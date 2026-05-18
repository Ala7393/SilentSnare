from flask import Blueprint, jsonify, request
from models.models import get_recent_packets, get_alerts
import os

bp = Blueprint('api', __name__)

@bp.route('/recent_packets', methods=['GET'])
def recent_packets():
    limit = request.args.get('limit', default=50, type=int)
    packets = get_recent_packets(limit)
    # تحويل الصفوف إلى قواميس
    packets_list = [dict(pkt) for pkt in packets]
    return jsonify(packets_list)

@bp.route('/alerts', methods=['GET'])
def alerts():
    limit = request.args.get('limit', default=20, type=int)
    alerts = get_alerts(limit)
    alerts_list = [dict(alert) for alert in alerts]
    return jsonify(alerts_list)

@bp.route('/pcaps', methods=['GET'])
def list_pcaps():
    pcap_dir = 'pcaps'
    if not os.path.exists(pcap_dir):
        return jsonify([])
    files = []
    for f in os.listdir(pcap_dir):
        if f.endswith('.pcap'):
            files.append({
                'name': f,
                'path': os.path.join(pcap_dir, f)
            })
    return jsonify(files)
