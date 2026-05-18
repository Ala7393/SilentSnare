#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║          SilentSnare — Auto Install & Launch Script              ║
# ║          MITM Educational Platform v2.0                          ║
# ║          Tested on: Kali Linux 2024.x, Debian 12, Ubuntu 22+    ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ─── Color Palette ────────────────────────────────────────────────────
RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
GOLD="\033[38;2;255;215;0m"
GOLD2="\033[38;2;212;175;55m"
GREEN="\033[38;2;68;187;68m"
RED="\033[38;2;255;68;68m"
CYAN="\033[38;2;68;200;255m"
GRAY="\033[38;2;90;90;100m"
WHITE="\033[97m"
YELLOW="\033[38;2;255;200;0m"

LINE="${GRAY}$(printf '═%.0s' {1..66})${RESET}"
THIN="${GRAY}$(printf '─%.0s' {1..66})${RESET}"

# ─── Banner ───────────────────────────────────────────────────────────
clear
echo ""
echo -e "$LINE"
echo -e "${GOLD}${BOLD}"
echo "   ██████╗ ██╗██╗     ███████╗███╗   ██╗████████╗ "
echo "   ██╔════╝██║██║     ██╔════╝████╗  ██║╚══██╔══╝ "
echo "   ███████╗██║██║     █████╗  ██╔██╗ ██║   ██║    "
echo "   ╚════██║██║██║     ██╔══╝  ██║╚██╗██║   ██║    "
echo "   ███████║██║███████╗███████╗██║ ╚████║   ██║    "
echo "   ╚══════╝╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   "
echo "   ███████╗███╗   ██╗ █████╗ ██████╗ ███████╗     "
echo "   ██╔════╝████╗  ██║██╔══██╗██╔══██╗██╔════╝     "
echo "   ███████╗██╔██╗ ██║███████║██████╔╝█████╗       "
echo "   ╚════██║██║╚██╗██║██╔══██║██╔══██╗██╔══╝       "
echo "   ███████║██║ ╚████║██║  ██║██║  ██║███████╗     "
echo "   ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝    "
echo -e "${RESET}"
echo -e "   ${BOLD}${WHITE}✦  MITM Educational Platform  —  v2.0  ✦${RESET}"
echo -e "$LINE"
echo ""

# ─── Helper Functions ─────────────────────────────────────────────────
step()    { echo -e "${CYAN}${BOLD}[${1}/${TOTAL}]${RESET}  ${BOLD}${WHITE}${2}${RESET}"; }
ok()      { echo -e "      ${GREEN}✔  ${1}${RESET}"; }
warn()    { echo -e "      ${YELLOW}⚠  ${1}${RESET}"; }
fail()    { echo -e "      ${RED}✘  ${1}${RESET}"; }
info()    { echo -e "      ${GRAY}→  ${1}${RESET}"; }
sep()     { echo -e "   $THIN"; echo ""; }

TOTAL=5

# ─── Step 1: Check root ───────────────────────────────────────────────
step 1 "Checking privileges..."
echo ""
if [ "$EUID" -ne 0 ]; then
    warn "Not running as root."
    warn "Network features (ARP Spoofing, Sniffing, iptables) require root."
    warn "Re-run with:  sudo ./install.sh"
    echo ""
else
    ok "Running as root — full network access available."
fi
sep

# ─── Step 2: Check Python ─────────────────────────────────────────────
step 2 "Checking Python version..."
echo ""

if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    fail "Python not found. Install with:"
    info "sudo apt update && sudo apt install python3 python3-pip -y"
    exit 1
fi

PY_VER=$($PY_CMD --version 2>&1 | awk '{print $2}')
PY_MAJOR=$($PY_CMD -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PY_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    fail "Python $PY_VER detected. SilentSnare requires Python 3.10+."
    info "Update Python: https://www.python.org/downloads/"
    exit 1
fi

ok "Python $PY_VER detected."
sep

# ─── Step 3: Install pip dependencies ────────────────────────────────
step 3 "Installing Python dependencies..."
echo ""

# Detect pip command
if command -v pip3 &>/dev/null; then
    PIP_CMD="pip3"
elif command -v pip &>/dev/null; then
    PIP_CMD="pip"
else
    fail "pip not found. Install with:"
    info "sudo apt install python3-pip -y"
    exit 1
fi

info "Using: $PIP_CMD"
info "Source: requirements.txt"
echo ""

# Try Kali/Debian --break-system-packages first, fall back to normal
if $PIP_CMD install --break-system-packages -r requirements.txt -q 2>/dev/null; then
    ok "All dependencies installed (--break-system-packages)."
elif $PIP_CMD install -r requirements.txt -q 2>/dev/null; then
    ok "All dependencies installed."
else
    fail "Dependency installation failed."
    info "Try manually:"
    info "  pip install --break-system-packages -r requirements.txt"
    info "  or: pip install -r requirements.txt"
    exit 1
fi
sep

# ─── Step 4: Setup environment ────────────────────────────────────────
step 4 "Setting up configuration..."
echo ""

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        ok "Created .env from .env.example"
        warn "Edit .env and set a strong SECRET_KEY before production use."
    else
        warn ".env.example not found — skipping environment setup."
        warn "Create a .env file manually if needed."
    fi
else
    ok ".env file already exists — skipping."
fi
sep

# ─── Step 5: Initialize database ─────────────────────────────────────
step 5 "Initializing database..."
echo ""

if $PY_CMD -c "from database.db import init_db; init_db(); print('OK')" 2>/dev/null | grep -q "OK"; then
    ok "Database initialized successfully."
else
    warn "Database init returned a non-critical warning. Continuing..."
fi
sep

# ─── Launch ───────────────────────────────────────────────────────────
echo -e "$LINE"
echo ""
echo -e "  ${GOLD}${BOLD}✦  SilentSnare is ready. Starting server...${RESET}"
echo ""

# Detect configured port
PORT_VAL=5000
if [ -f ".env" ]; then
    PORT_VAL=$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo 5000)
    PORT_VAL=${PORT_VAL:-5000}
fi

echo -e "  ${CYAN}🌐  Interface:  ${WHITE}http://localhost:${PORT_VAL}/login${RESET}"
echo -e "  ${CYAN}🌐  LAN:        ${WHITE}http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '0.0.0.0'):${PORT_VAL}/login${RESET}"
echo ""
echo -e "  ${GOLD2}👤  Default login:  ${WHITE}ala alaadani${RESET}  ${GOLD2}/  ${WHITE}778559174${RESET}"
echo -e "  ${YELLOW}⚠   Change default credentials via /admin after first login${RESET}"
echo ""
echo -e "$LINE"
echo ""

exec $PY_CMD app.py
