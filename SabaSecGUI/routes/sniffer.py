# routes/sniffer.py
import subprocess
import os
import time
import threading
import re
from functools import wraps
from flask import Blueprint, jsonify, render_template, request
from database.db import get_db

from scapy.all import ARP, Ether, srp, sniff, IP, TCP, Raw
import netifaces
import ipaddress

bp = Blueprint('sniffer', __name__, url_prefix='/sniffer')

def json_response(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return decorated_function

# ========== متغيرات عامة ==========
sniff_active = False
sniff_thread = None
sniff_packets = []
sniff_target = None

# ========== دالة معالجة الحزم (مع طباعة للتشخيص) ==========
def packet_handler(pkt):
    global sniff_packets, sniff_target

    # طباعة أي حزمة تصل للتأكد من عمل Scapy
    print(f"[SNIFFER] Packet received: {pkt.summary()}")

    if not sniff_target:
        return

    if not (pkt.haslayer(IP) and pkt.haslayer(TCP)):
        return

    src = pkt[IP].src
    if src != sniff_target:
        return

    dst = pkt[IP].dst
    src_port = pkt[TCP].sport
    dst_port = pkt[TCP].dport

    if not pkt.haslayer(Raw):
        return

    payload_data = pkt[Raw].load

    if len(payload_data) < 50:
        return

    protocol = None
    is_secure = 0
    method = None

    if dst_port == 443:
        protocol = 'HTTPS'
        is_secure = 1
        if len(payload_data) < 500:
            return
        method = '🔒'
    elif dst_port == 80:
        try:
            payload_str = payload_data.decode('utf-8', errors='ignore')
            method_match = re.match(r'^(GET|POST|PUT|DELETE|HEAD|OPTIONS|CONNECT|TRACE|PATCH)\s', payload_str, re.IGNORECASE | re.MULTILINE)
            if method_match:
                protocol = 'HTTP'
                method = method_match.group(1).upper()
            else:
                method = 'HTTP'
        except:
            method = 'HTTP'
    else:
        return

    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO packets 
                (src_ip, dst_ip, protocol, length, payload, is_secure, src_port, dst_port)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                src, dst,
                protocol,
                len(pkt),
                payload_data[:2000].decode('utf-8', errors='ignore') if payload_data else '',
                is_secure,
                src_port,
                dst_port
            ))
    except Exception as db_err:
        print(f"⚠️ Database error: {db_err}")

    sniff_packets.append({
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'src_ip': src,
        'dst_ip': dst,
        'src_port': src_port,
        'dst_port': dst_port,
        'protocol': protocol,
        'data': payload_data.decode('utf-8', errors='ignore'),  # الحمولة كاملة
        'is_secure': is_secure,
        'method': method,
        'source': 'sniff'
    })

    print(f"[SNIFFER] Packet stored: {src} -> {dst}, total packets: {len(sniff_packets)}")

def start_spawn(target, *args, **kwargs):
    thread = threading.Thread(target=target, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

# ========== نقاط النهاية ==========
@bp.route('/')
def index():
    return render_template('sniffer.html')

@bp.route('/scan_network', methods=['POST'])
@json_response
def scan_network():
    data = request.get_json()
    interface = data.get('interface', 'eth0')
    try:
        addrs = netifaces.ifaddresses(interface)
        ip_info = addrs[netifaces.AF_INET][0]
        network = ipaddress.IPv4Network(f"{ip_info['addr']}/{ip_info['netmask']}", strict=False)
        arp_request = ARP(pdst=str(network))
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        answered = srp(broadcast/arp_request, timeout=5, iface=interface, verbose=0)[0]
        devices = [{'ip': rcv.psrc, 'mac': rcv.hwsrc} for _, rcv in answered]
        return jsonify({'status': 'success', 'devices': devices})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/start_sniff', methods=['POST'])
@json_response
def start_sniff():
    global sniff_active, sniff_thread, sniff_packets, sniff_target
    if sniff_active:
        return jsonify({'status': 'error', 'message': 'Sniffing already active'}), 400
    data = request.get_json()
    interface = data.get('interface', 'eth0')
    target_ip = data.get('target_ip')
    if not target_ip:
        return jsonify({'status': 'error', 'message': 'Please specify target IP'}), 400
    sniff_active = True
    sniff_packets = []
    sniff_target = target_ip
    def sniff_stop_filter(pkt):
        return not sniff_active
    sniff_thread = start_spawn(
        lambda: sniff(
            iface=interface,
            prn=packet_handler,
            store=False,
            stop_filter=sniff_stop_filter,
            filter="tcp dst port 80 or tcp dst port 443"
        )
    )
    return jsonify({'status': 'success', 'message': f'Started sniffing on {target_ip}'})

@bp.route('/stop_sniff', methods=['POST'])
@json_response
def stop_sniff():
    global sniff_active, sniff_target
    sniff_active = False
    sniff_target = None
    return jsonify({'status': 'success', 'message': 'Sniffing stopped'})

@bp.route('/sniff_status', methods=['GET'])
@json_response
def sniff_status():
    global sniff_active, sniff_packets
    return jsonify({'active': sniff_active, 'count': len(sniff_packets)})

@bp.route('/get_packets', methods=['GET'])
@json_response
def get_packets():
    global sniff_packets
    return jsonify({'packets': sniff_packets})

@bp.route('/clear_packets', methods=['POST'])
@json_response
def clear_packets():
    global sniff_packets
    sniff_packets = []
    return jsonify({'status': 'success', 'message': 'All packets cleared'})

# ========== دالة التنظيف ==========
def cleanup():
    global sniff_active, sniff_target, sniff_packets
    if sniff_active:
        sniff_active = False
        sniff_target = None
        sniff_packets = []
    print("✅ Sniffer cleanup done")
