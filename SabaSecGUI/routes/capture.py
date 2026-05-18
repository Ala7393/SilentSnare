import subprocess
import os
from flask import Blueprint, jsonify
from datetime import datetime
from decorators import login_required

bp = Blueprint('capture', __name__)

capture_process = None

@bp.route('/start_capture', methods=['POST'])
@login_required
def start_capture():
    global capture_process
    iface = os.getenv('IFACE', 'eth0')
    os.makedirs('pcaps', exist_ok=True)
    pcap_file = f"pcaps/capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pcap"
    cmd = ['tshark', '-i', iface, '-w', pcap_file]
    try:
        capture_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({'status': 'started', 'file': pcap_file})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/stop_capture', methods=['POST'])
@login_required
def stop_capture():
    global capture_process
    if capture_process:
        capture_process.terminate()
        capture_process = None
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'not running'})
