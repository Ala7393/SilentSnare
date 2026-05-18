from database.db import get_db

def insert_packet(src_ip, dst_ip, protocol, length, payload, is_secure):
    with get_db() as db:
        db.execute(
            "INSERT INTO packets (src_ip, dst_ip, protocol, length, payload, is_secure) VALUES (?,?,?,?,?,?)",
            (src_ip, dst_ip, protocol, length, payload, is_secure)
        )

def get_recent_packets(limit=50):
    with get_db() as db:
        return db.execute("SELECT * FROM packets ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

def insert_alert(type, message):
    with get_db() as db:
        db.execute("INSERT INTO alerts (type, message) VALUES (?,?)", (type, message))

def get_alerts(limit=20):
    with get_db() as db:
        return db.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
