import sys
import os
import signal
import time
from flask import Flask, session, redirect, url_for, request
from dotenv import load_dotenv
from database.db import init_db

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables — primary .env, fallback to _.env.example
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
_env_example = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_.env.example')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
elif os.path.exists(_env_example):
    load_dotenv(_env_example)

# ============================================================
#   CLI BANNER – SilentSnare Professional Startup Screen
# ============================================================

RESET  = "\033[0m"
BOLD   = "\033[1m"
GOLD   = "\033[38;2;255;215;0m"
DIM    = "\033[38;2;184;134;11m"
GREEN  = "\033[38;2;68;255;68m"
RED    = "\033[38;2;255;68;68m"
CYAN   = "\033[38;2;68;200;255m"
GRAY   = "\033[38;2;100;100;100m"
WHITE  = "\033[97m"

ASCII_LOGO = r"""
  ███████╗██╗██╗     ███████╗███╗   ██╗████████╗
  ██╔════╝██║██║     ██╔════╝████╗  ██║╚══██╔══╝
  ███████╗██║██║     █████╗  ██╔██╗ ██║   ██║
  ╚════██║██║██║     ██╔══╝  ██║╚██╗██║   ██║
  ███████║██║███████╗███████╗██║ ╚████║   ██║
  ╚══════╝╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝
  ███████╗███╗   ██╗ █████╗ ██████╗ ███████╗
  ██╔════╝████╗  ██║██╔══██╗██╔══██╗██╔════╝
  ███████╗██╔██╗ ██║███████║██████╔╝█████╗
  ╚════██║██║╚██╗██║██╔══██║██╔══██╗██╔══╝
  ███████║██║ ╚████║██║  ██║██║  ██║███████╗
  ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
"""

def print_banner(port: int = 5000):
    W = 62
    LINE = GRAY + "═" * W + RESET

    print()
    print(LINE)
    # شعار ASCII
    for row in ASCII_LOGO.strip("\n").split("\n"):
        print(GOLD + BOLD + row + RESET)
    print(LINE)
    print()
    print(BOLD + WHITE + "  ✦  SilentSnare  —  MITM Educational Platform  ✦" + RESET)
    print()
    print(GRAY + "  ┌" + "─" * (W - 4) + "┐" + RESET)

    rows = [
        ("🌐", "Web Interface",  f"{CYAN}http://localhost:{port}{RESET}"),
        ("🌐", "Direct Link",    f"{CYAN}http://127.0.0.1:{port}{RESET}"),
        ("🔐", "Login Page",     f"{CYAN}http://127.0.0.1:{port}/login{RESET}"),
        ("📡", "Port",           f"{GREEN}{port}{RESET}"),
        ("✅", "Status",         f"{GREEN}Server Running{RESET}"),
    ]
    for icon, label, value in rows:
        print(f"{GRAY}  │{RESET}  {icon}  {BOLD}{WHITE}{label:<16}{RESET}  {value}")

    print(GRAY + "  └" + "─" * (W - 4) + "┘" + RESET)
    print()
    print(GOLD + "  📌  افتح المتصفح وابدأ من صفحة تسجيل الدخول" + RESET)
    print()
    print(GRAY + "  [ Ctrl+C to stop ]" + RESET)
    print()
    print(LINE)
    print()


# ============================================================
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'silentsnare-secret-2025')

init_db()

from routes import main, capture, analysis, scenarios, auth, admin, scenario2, sniffer

app.register_blueprint(main.bp)
app.register_blueprint(capture.bp)
app.register_blueprint(analysis.bp)
app.register_blueprint(scenarios.bp, url_prefix='/scenarios')
app.register_blueprint(auth.bp)
app.register_blueprint(admin.bp, url_prefix='/admin')
app.register_blueprint(scenario2.bp)
app.register_blueprint(sniffer.bp)

# ========== حماية المسارات ==========
public_endpoints = ['auth.login', 'auth.logout', 'static']

@app.before_request
def require_login():
    if request.endpoint and request.endpoint.startswith('static'):
        return
    if request.endpoint in public_endpoints or session.get('user_id'):
        return
    return redirect(url_for('auth.login'))

# ========== تنظيف الموارد ==========
def cleanup_resources():
    print("\n🛑 جاري إيقاف التطبيق وتنظيف الموارد...")
    for mod_name, mod in [('scenarios', scenarios), ('scenario2', scenario2), ('sniffer', sniffer)]:
        try:
            if hasattr(mod, 'cleanup'):
                mod.cleanup()
        except Exception as e:
            print(f"⚠️  خطأ أثناء تنظيف {mod_name}: {e}")
    print("✅ تم التنظيف بنجاح")

def signal_handler(sig, frame):
    cleanup_resources()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 5000))
    print_banner(PORT)
    app.run(debug=False, host='0.0.0.0', port=PORT)
