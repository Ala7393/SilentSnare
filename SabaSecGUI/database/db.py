import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'silentsnare.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                src_ip TEXT,
                dst_ip TEXT,
                protocol TEXT,
                length INTEGER,
                payload TEXT,
                is_secure BOOLEAN DEFAULT 0,
                src_port INTEGER,
                dst_port INTEGER
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type TEXT,
                message TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_packets_ports ON packets(dst_port, src_port)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_packets_ts ON packets(timestamp)')
        user = db.execute("SELECT * FROM users WHERE username = ?", ('ala alaadani',)).fetchone()
        if not user:
            hashed = generate_password_hash('778559174')
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                       ('ala alaadani', hashed))
        print("✅ قاعدة البيانات جاهزة (مع جدول المستخدمين)")

if __name__ == '__main__':
    init_db()
