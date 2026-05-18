import subprocess
from flask import Blueprint, request, jsonify
import os
from decorators import login_required

bp = Blueprint('analysis', __name__)

@bp.route('/analyze', methods=['POST'])
@login_required
def analyze():
    data = request.get_json()
    pcap_file = data.get('file') if data else None
    if not pcap_file:
        return jsonify({'error': 'no file provided'}), 400

    if not os.path.exists(pcap_file):
        return jsonify({'error': 'file not found'}), 404

    try:
        result = subprocess.run(['tshark', '-r', pcap_file, '-q', '-z', 'io,stat,1'],
                                capture_output=True, text=True, timeout=30)
        return jsonify({'summary': result.stdout})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'analysis timeout'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
