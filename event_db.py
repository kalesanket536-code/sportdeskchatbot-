import sqlite3
import os
import shutil
from typing import List, Dict, Optional, Any

BASE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sports_event.db")

def get_db_path() -> str:
    """Return database path. On serverless environments (e.g. Vercel), copy seed DB to /tmp to allow write operations."""
    if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.abspath(BASE_DB_PATH)), os.W_OK):
        tmp_db = os.path.join("/tmp", "sports_event.db")
        if not os.path.exists(tmp_db) and os.path.exists(BASE_DB_PATH):
            try:
                shutil.copyfile(BASE_DB_PATH, tmp_db)
            except Exception:
                pass
        if os.path.exists(tmp_db):
            return tmp_db
    return BASE_DB_PATH

DB_PATH = BASE_DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_file = get_db_path()
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # Fixtures table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fixtures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sport TEXT NOT NULL,
        event_name TEXT NOT NULL,
        stage TEXT NOT NULL,
        court TEXT NOT NULL,
        start_time TEXT NOT NULL,
        status TEXT NOT NULL, -- 'Upcoming', 'Live', 'Delayed', 'Completed'
        notes TEXT
    )
    """)

    # Alerts & Weather Delays table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        delay_minutes INTEGER DEFAULT 0,
        message TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    # Facilities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        gate_proximity TEXT,
        details TEXT
    )
    """)

    # Seed initial fixtures if empty
    cursor.execute("SELECT COUNT(*) FROM fixtures")
    if cursor.fetchone()[0] == 0:
        sample_fixtures = [
            ("Track & Field", "100m Sprint Final", "Final", "Main Track A", "04:15 PM", "Upcoming", "Spectator gates open at 03:30 PM"),
            ("Track & Field", "400m Hurdles", "Semi-Final", "Main Track A", "02:30 PM", "Live", "Heat 2 of 3 underway"),
            ("Basketball", "Varsity Men's Semi-Final", "Semi-Final", "Court 3 (North Hall)", "03:00 PM", "Upcoming", "Warmups start at 02:40 PM"),
            ("Volleyball", "Invitational Final", "Final", "Court 1 (East Wing)", "05:00 PM", "Upcoming", "Coin toss at 04:45 PM"),
            ("Swimming", "50m Freestyle", "Heats", "Aquatics Center Lane 1-8", "01:30 PM", "Completed", "Results posted at Gate 4 board")
        ]
        cursor.executemany("""
            INSERT INTO fixtures (sport, event_name, stage, court, start_time, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_fixtures)

    # Seed initial alerts if empty
    cursor.execute("SELECT COUNT(*) FROM alerts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO alerts (category, location, delay_minutes, message, is_active)
            VALUES ('Weather', 'All Outdoor Tracks', 0, 'All tracks are dry and clear. No weather delays currently active.', 0)
        """)

    # Seed initial facilities if empty
    cursor.execute("SELECT COUNT(*) FROM facilities")
    if cursor.fetchone()[0] == 0:
        sample_facilities = [
            ("Medical Tent 1", "Concourse A, near Gate 1", "Gate 1", "First aid and rapid paramedic support"),
            ("Medical Tent 2", "Behind Concourse C, 50m south of Gate 3", "Gate 3", "Ambulance bay, triage, and doctor on site"),
            ("Hydration Station", "Gates 1, 2, 3, and 4", "All Gates", "Free chilled electrolyte and filtered water refills"),
            ("Box Office", "Gate 1 North Concourse", "Gate 1", "Ticket scans, will call, and badge reprints"),
            ("Lost & Found", "Gate 2 Customer Service Booth", "Gate 2", "Operating 08:00 AM - 08:00 PM")
        ]
        cursor.executemany("""
            INSERT INTO facilities (name, location, gate_proximity, details)
            VALUES (?, ?, ?, ?)
        """, sample_facilities)

    conn.commit()
    conn.close()

def get_fixtures(sport: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if sport:
        cursor.execute("SELECT * FROM fixtures WHERE sport LIKE ? OR event_name LIKE ? ORDER BY id ASC", (f"%{sport}%", f"%{sport}%"))
    else:
        cursor.execute("SELECT * FROM fixtures ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_active_delays() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE is_active = 1")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def set_delay(location: str, delay_minutes: int, message: str, is_active: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (category, location, delay_minutes, message, is_active)
        VALUES ('Delay Alert', ?, ?, ?, ?)
    """, (location, delay_minutes, message, 1 if is_active else 0))
    conn.commit()
    conn.close()

def get_facilities(query: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if query:
        cursor.execute("SELECT * FROM facilities WHERE name LIKE ? OR location LIKE ? OR gate_proximity LIKE ?", 
                       (f"%{query}%", f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT * FROM facilities")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def format_live_fixtures(sport: Optional[str] = None) -> str:
    fixtures = get_fixtures(sport)
    if not fixtures:
        return "No current fixtures found matching your request. Please check the central timetable board."
    
    lines = ["Here is the current live schedule:"]
    for f in fixtures:
        status_tag = f"[{f['status']}]"
        lines.append(f"• {f['event_name']} ({f['sport']}): {f['start_time']} at {f['court']} {status_tag}")
    return "\n".join(lines)

def format_live_delays() -> str:
    delays = get_active_delays()
    if not delays:
        return "Great news! All outdoor courts and tracks are dry and operational. There are zero active weather or schedule delays."
    
    lines = ["⚠️ Active Delays & Alerts:"]
    for d in delays:
        lines.append(f"• {d['location']}: {d['message']} ({d['delay_minutes']} min delay)")
    return "\n".join(lines)

def format_live_facilities(keyword: str = "") -> str:
    facs = get_facilities(keyword if keyword else None)
    if not facs:
        return "Facilities information: Medical tents and hydration points are operational near all stadium gates."
    lines = ["Event Facilities & Support:"]
    for f in facs:
        lines.append(f"• {f['name']}: {f['location']} ({f['details']})")
    return "\n".join(lines)
