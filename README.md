<br>
<div align="center">

```
  ██████╗ ██╗██╗     ███████╗███╗   ██╗████████╗
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
```

**SilentSnare** — MITM Educational Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-gold?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.2-gold?style=flat-square&logo=flask&logoColor=white)
![Scapy](https://img.shields.io/badge/Scapy-2.5%2B-gold?style=flat-square)
![Kali Linux](https://img.shields.io/badge/Kali%20Linux-Compatible-gold?style=flat-square&logo=kali-linux&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-gold?style=flat-square)
![Educational](https://img.shields.io/badge/Use-Educational%20Only-red?style=flat-square)

*منصة تعليمية تفاعلية لمحاكاة هجمات Man-in-the-Middle في بيئات مخبرية معزولة*

</div>

---

## Overview

**SilentSnare** is an interactive web-based educational platform built for isolated lab environments.
It visualizes and simulates Man-in-the-Middle (MITM) attacks to help security students understand:

- **ARP Spoofing** — how attackers position themselves between two hosts
- **Packet Inspection** — real-time analysis of HTTP / HTTPS / SMTP / SMTPS traffic
- **Traffic Interception** — modifying packets in-flight using iptables + scapy
- **Protocol Security** — the difference between encrypted and plaintext protocols
- **Email Interception** — fake SMTP server capturing cleartext credentials

---

## Requirements

| Component      | Version  | Purpose                        |
|----------------|----------|--------------------------------|
| Python         | 3.10+    | Runtime                        |
| Flask          | 3.1.2    | Web framework                  |
| Scapy          | 2.5+     | Packet crafting & ARP spoofing |
| netifaces      | 0.11+    | Network interface enumeration  |
| Flask-SocketIO | 5.5+     | Real-time WebSocket events     |
| python-dotenv  | 1.0+     | Environment configuration      |

> **OS Requirement:** Linux only (Kali Linux recommended). Raw socket access requires root privileges.

---

## Quick Start — Kali Linux

### Automated Installation (Recommended)

```bash
# Clone / download the project
git clone https://github.com/youruser/silentsnare.git
cd silentsnare

# Run installer as root
chmod +x install.sh
sudo ./install.sh
```

The installer will:
1. Verify Python 3.10+ is present
2. Install all pip dependencies (`--break-system-packages` for Kali)
3. Initialize the SQLite database and create default admin account
4. Copy `.env.example` → `.env` if no config file exists
5. Launch the Flask server automatically

---

### Manual Installation

```bash
# 1. Install Python dependencies
sudo pip install --break-system-packages -r requirements.txt

# 2. Configure environment
cp .env.example .env
nano .env          # Set SECRET_KEY and PORT

# 3. Initialize database
python3 -c "from database.db import init_db; init_db()"

# 4. Launch (root required for network features)
sudo python3 app.py
```

---

### Standard Python / venv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 app.py
```

---

## Access the Interface

After startup open your browser:

```
http://localhost:5000
http://127.0.0.1:5000
```

---

## Default Credentials

| Field    | Value            |
|----------|------------------|
| Username | `ala alaadani`   |
| Password | `778559174`      |

> **Security Note:** Change the password from the Admin panel immediately after first login.

---

## Available Pages

| Route         | Description                          |
|---------------|--------------------------------------|
| `/login`      | Authentication                       |
| `/`           | Main dashboard                       |
| `/inspector`  | Live payload inspector               |
| `/sniffer`    | Network packet sniffer               |
| `/scenarios`  | Scenario 1 — ARP + HTTP MITM        |
| `/scenario2`  | Scenario 2 — SMTP email interception |
| `/admin`      | Administration panel                 |

---

## Project Structure

```
silentsnare/
├── app.py                  # Entry point — startup banner, Flask app, blueprints
├── requirements.txt        # Python dependencies
├── install.sh              # Auto-install & launch script (Kali-ready)
├── .env.example            # Environment variable template
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Master layout (navbar, toasts, Font Awesome)
│   ├── login.html          # Login page (gold animated theme)
│   ├── index.html          # Dashboard
│   ├── inspector.html      # Packet inspector
│   ├── sniffer.html        # Sniffer UI
│   └── scenarios.html      # Scenarios UI
│
├── static/
│   ├── css/style.css       # Dark gold theme
│   └── js/main.js          # Toast notifications, API helpers
│
├── routes/                 # Flask Blueprint modules
│   ├── auth.py             # Login / logout
│   ├── main.py             # Dashboard & inspector
│   ├── capture.py          # Packet capture API
│   ├── analysis.py         # Traffic analysis
│   ├── scenarios.py        # MITM Scenario 1 (ARP spoofing)
│   ├── scenario2.py        # MITM Scenario 2 (SMTP intercept)
│   ├── sniffer.py          # Live packet sniffer
│   ├── admin.py            # Admin panel
│   └── api.py              # JSON REST endpoints
│
└── database/
    └── db.py               # SQLite helpers & schema init
```

---

## Protocol Color Reference

| Protocol | Color                   | Security        |
|----------|-------------------------|-----------------|
| `HTTP`   | 🔴 Red `#FF4444`        | Cleartext — Dangerous |
| `HTTPS`  | 🟢 Green `#44BB44`      | Encrypted — Safe |
| `SMTP`   | 🟠 Orange `#FFAA00`     | Cleartext email  |
| `SMTPS`  | 🟡 Amber `#FF8800`      | Encrypted email  |
| `MITM`   | 🟣 Purple `#AA44FF`     | Intercepted      |

---

## Network Features (Requires Root)

| Feature               | Requirement           |
|-----------------------|-----------------------|
| ARP Spoofing          | `sudo` + Scapy        |
| Packet Sniffing       | `sudo` + Scapy        |
| iptables Forwarding   | `sudo` + iptables     |
| Interface Enumeration | netifaces             |

Enable IP forwarding for full MITM operation:
```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```

---

## Configuration

Copy and edit the environment file before running:
```bash
cp .env.example .env
```

Key variables:

| Variable       | Default                  | Description                          |
|----------------|--------------------------|--------------------------------------|
| `SECRET_KEY`   | *(change this!)*         | Flask session encryption key         |
| `PORT`         | `5000`                   | HTTP server port                     |
| `DEBUG`        | `False`                  | Never enable on real networks        |

---

## Troubleshooting

**`Permission denied` on sniff / ARP:**
```bash
sudo python3 app.py
```

**`pip` fails on Kali Linux:**
```bash
sudo pip install --break-system-packages -r requirements.txt
```

**Port 5000 already in use:**
```bash
# Edit .env and set PORT=5001 (or any free port)
# Or kill the process using port 5000:
sudo fuser -k 5000/tcp
```

**netifaces build fails:**
```bash
sudo apt install python3-dev build-essential -y
pip install --break-system-packages netifaces
```

---

## Disclaimer

> This tool is **strictly for educational purposes** in isolated lab environments.  
> Using it on any live network without explicit authorization is **illegal**.  
> The authors assume no liability for misuse.  
> Always comply with applicable laws and ethical guidelines.

---

## License

```
MIT License — Educational Use Only
Copyright (c) 2025 SilentSnare Project
```
 ## 👨‍💻 Development Team

<div align="center">

## 🏆 Core Development Team

<table>
<tr>

<td align="center" width="25%">

### 👨‍💻 Ala Al-Baadani

**Lead Developer & Project Manager**

📧 [laa3490@gmail.com](mailto:laa3490@gmail.com)

📱 +967 778 559 174

<br>

<a href="https://github.com/Ala7393">
<img src="https://img.shields.io/badge/GitHub-Ala7393-gold?logo=github&logoColor=white">
</a>

<a href="https://linkedin.com/in/Ala7393">
<img src="https://img.shields.io/badge/LinkedIn-Ala7393-gold?logo=linkedin&logoColor=white">
</a>

<a href="https://t.me/Ala7393">
<img src="https://img.shields.io/badge/Telegram-@Ala7393-gold?logo=telegram&logoColor=white">
</a>

<a href="https://wa.me/967778559174">
<img src="https://img.shields.io/badge/WhatsApp-+967778559174-gold?logo=whatsapp&logoColor=white">
</a>

</td>

<td align="center" width="25%">

### 👨‍💻 Mohammed Salah

**Backend Developer & Database Engineer**

📧 [moom1719877@gmail.com](mailto:moom1719877@gmail.com)

📱 +967 771 719 877

<br>

<img src="https://img.shields.io/badge/Backend-Developer-blue">
<img src="https://img.shields.io/badge/Database-Engineer-green">

</td>

</tr>

<tr>

<td align="center">

### 👨‍💻 Wajdi Al-Maamari

**Cybersecurity Analyst & Quality Assurance Engineer**
📧 [wajdialmamary2@gmail.com](mailto:wajdialmamary2@gmail.com)

📱 +967 775 968 143

<br>
<img src="https://img.shields.io/badge/Cybersecurity-Analyst-red">
<img src="https://img.shields.io/badge/QA-
Engineer-yellow">
</td>

<td align="center">

### 👨‍💻 Ahmed Sharah
**Frontend Developer & UI/UX Designer**

📧 [ahmdalshybh81@gmail.com](mailto:ahmdalshybh81@gmail.com)

📱 +967 775 655 129

<br>
<img src="https://img.shields.io/badge/Frontend-Developer-orange">
<img src="https://img.shields.io/badge/UI%2FUX-Designer-purple">


</td>

</tr>
</table>

</div>

---

## 📌 Team Responsibilities

| Member               | Responsibility                                       |
| -------------------- | ---------------------------------------------------- |
| **Ala Al-Baadani**    | Project Leadership, System Architecture, Integration |
| **Mohammed Salah**   | Backend Development, APIs, Database Management       |
| **Wajdi Al-Maamari** | Cybersecurity Analysis, Testing & Quality Assurance  |
| **Ahmed Shrah**     |Frontend Development, UI/UX Design  |

---

## 📞 Contact Information

| Developer        | Email                                                       | Phone            |
| ---------------- | ----------------------------------------------------------- | ---------------- |
| Ala Al-Baadani    | [laa3490@gmail.com](mailto:laa3490@gmail.com)               | +967 778 559 174 |
| Mohammed Salah   | [moom1719877@gmail.com](mailto:moom1719877@gmail.com)       | +967 771 719 877 |
| Wajdi Al-Maamari | [wajdialmamary2@gmail.com](mailto:wajdialmamary2@gmail.com) | +967 775 968 143 |
| Ahmed Shrah     | [ahmdalshybh81@gmail.com](mailto:ahmdalshybh81@gmail.com)   | +967 775 655 129 |

---

> © 2026 Development Team. All Rights Reserved.
>
> This project was developed collaboratively by the team members listed above for academic, research, and professional purposes.
