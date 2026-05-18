from flask import Blueprint, render_template, jsonify, send_from_directory, request
from database.db import get_db
import os
import netifaces

bp = Blueprint('main', __name__)

def get_recent_packets(limit=20):
    with get_db() as db:
        return db.execute("SELECT * FROM packets ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

def get_alerts(limit=20):
    with get_db() as db:
        return db.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

@bp.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('main.educational'))

@bp.route('/educational')
def educational():
    return render_template('educational.html')

@bp.route('/visual-traffic')
def visual_traffic():
    return render_template('visual_traffic.html')

@bp.route('/logs')
def logs():
    return render_template('logs.html')

@bp.route('/inspector')
def inspector():
    return render_template('inspector.html')

@bp.route('/pcaps')
def pcaps():
    return render_template('p.html')

@bp.route('/api/recent_packets')
def api_recent_packets():
    limit = request.args.get('limit', 20, type=int)
    packets = get_recent_packets(limit)
    return jsonify([dict(p) for p in packets])

@bp.route('/api/alerts')
def api_alerts():
    limit = request.args.get('limit', 20, type=int)
    alerts = get_alerts(limit)
    return jsonify([dict(a) for a in alerts])

@bp.route('/api/pcaps')
def api_pcaps():
    pcap_dir = os.path.join(os.path.dirname(__file__), '..', 'pcaps')
    files = []
    if os.path.exists(pcap_dir):
        for f in os.listdir(pcap_dir):
            if f.endswith('.pcap') or f.endswith('.pcapng'):
                files.append({'name': f, 'path': os.path.join(pcap_dir, f)})
    return jsonify(files)

@bp.route('/download/<filename>')
def download_file(filename):
    pcap_dir = os.path.join(os.path.dirname(__file__), '..', 'pcaps')
    return send_from_directory(pcap_dir, filename, as_attachment=True)

@bp.route('/api/protocol_stats')
def protocol_stats():
    with get_db() as db:
        row = db.execute("""
            SELECT
              SUM(CASE WHEN dst_port = 80  OR src_port = 80  THEN 1 ELSE 0 END)  as http,
              SUM(CASE WHEN dst_port = 443 OR src_port = 443 THEN 1 ELSE 0 END)  as https,
              SUM(CASE WHEN dst_port NOT IN (80,443) AND src_port NOT IN (80,443) THEN 1 ELSE 0 END) as other
            FROM packets
        """).fetchone()
    return jsonify({
        'http':  row['http']  or 0,
        'https': row['https'] or 0,
        'other': row['other'] or 0
    })

@bp.route('/api/clear_packets', methods=['POST'])
def clear_packets():
    try:
        with get_db() as db:
            db.execute("DELETE FROM packets")
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/interfaces')
def get_interfaces():
    try:
        interfaces = netifaces.interfaces()
        return jsonify(interfaces)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/view_pcap/<filename>')
def view_pcap(filename):
    pcap_dir = os.path.join(os.path.dirname(__file__), '..', 'pcaps')
    filepath = os.path.join(pcap_dir, filename)
    if not os.path.exists(filepath):
        return "الملف غير موجود", 404
    try:
        import subprocess
        result = subprocess.run(
            ['tshark', '-r', filepath, '-V'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if not result.stdout.strip():
            return "لا توجد بيانات قابلة للعرض في هذا الملف."
        return f"<pre>{result.stdout}</pre>"
    except subprocess.TimeoutExpired:
        return "انتهت مهلة المعالجة", 500
    except Exception as e:
        return f"خطأ: {str(e)}", 500
