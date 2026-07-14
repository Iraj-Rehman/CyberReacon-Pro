"""
core/database.py
Real SQLite database for scan history — replaces the earlier history.json
flat-file approach. Uses Python's built-in sqlite3 (no extra dependency),
kept intentionally simple (no ORM) so it's easy to read and explain in an
interview: "I designed a two-table relational schema — scans and ports,
linked by scan_id, one-to-many."

Schema:
  scans(id, target, resolved_ip, scan_type, date, duration_sec,
        total_ports, open_ports, closed_ports, risk_score)
  ports(id, scan_id, port, protocol, state, service, version, banner,
        risk, description, latency_ms)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cyberrecon.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS scans (
        id TEXT PRIMARY KEY,
        target TEXT NOT NULL,
        resolved_ip TEXT,
        scan_type TEXT,
        date TEXT NOT NULL,
        duration_sec REAL,
        total_ports INTEGER,
        open_ports INTEGER,
        closed_ports INTEGER,
        risk_score INTEGER
    );

    CREATE TABLE IF NOT EXISTS ports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id TEXT NOT NULL,
        port INTEGER,
        protocol TEXT,
        state TEXT,
        service TEXT,
        version TEXT,
        banner TEXT,
        risk TEXT,
        description TEXT,
        latency_ms REAL,
        FOREIGN KEY (scan_id) REFERENCES scans (id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_ports_scan_id ON ports (scan_id);
    CREATE INDEX IF NOT EXISTS idx_scans_date ON scans (date);
    """)
    conn.commit()
    conn.close()


def save_scan(record: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO scans (id, target, resolved_ip, scan_type, date, duration_sec,
                               total_ports, open_ports, closed_ports, risk_score)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (record["id"], record["target"], record["resolved_ip"], record["scan_type"],
         record["date"], record["duration_sec"], record["total_ports"],
         record["open_ports"], record["closed_ports"], record["risk_score"]),
    )
    for r in record["results"]:
        conn.execute(
            """INSERT INTO ports (scan_id, port, protocol, state, service, version,
                                   banner, risk, description, latency_ms)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (record["id"], r["port"], r["protocol"], r["state"], r["service"],
             r["version"], r["banner"], r["risk"], r["description"], r["latency_ms"]),
        )
    conn.commit()
    conn.close()


def get_history(limit: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM scans ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_scan_with_results(scan_id: str):
    conn = get_connection()
    scan = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not scan:
        conn.close()
        return None
    ports = conn.execute("SELECT * FROM ports WHERE scan_id = ?", (scan_id,)).fetchall()
    conn.close()
    scan_dict = dict(scan)
    scan_dict["results"] = [dict(p) for p in ports]
    return scan_dict


def delete_scan(scan_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM ports WHERE scan_id = ?", (scan_id,))
    conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()


def get_scan(scan_id: str):
    """Alias used by report export — same as get_scan_with_results."""
    return get_scan_with_results(scan_id)


def search_history(query: str, limit: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM scans WHERE target LIKE ? ORDER BY date DESC LIMIT ?",
        (f"%{query}%", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]