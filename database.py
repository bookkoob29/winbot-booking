"""
Database adapter — supports both SQLite (dev) and PostgreSQL (production).

Auto-detects by DATABASE_URL environment variable:
- If DATABASE_URL is set → PostgreSQL (production on Render/Supabase)
- If not set → SQLite (local dev, file: bookings.db)
"""
import os
import uuid
import datetime
from config import DB_PATH, STATUS_AVAILABLE, SLOTS

# Detect backend
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

# --- Schema (SQLite version) ---

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    booking_code TEXT UNIQUE NOT NULL,
    booking_date TEXT NOT NULL,
    slot_start TEXT NOT NULL,
    slot_end TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    line_id TEXT DEFAULT NULL,
    condo_name TEXT DEFAULT NULL,
    condo_map_link TEXT DEFAULT NULL,
    note TEXT DEFAULT NULL,
    internal_note TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'RESERVED_UNPAID',
    confirmed_by TEXT DEFAULT NULL,
    confirmed_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
    cancelled_at TEXT DEFAULT NULL,
    UNIQUE(booking_date, slot_start, slot_end)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL,
    booking_code TEXT DEFAULT NULL,
    activity_type TEXT NOT NULL,
    old_status TEXT DEFAULT NULL,
    new_status TEXT DEFAULT NULL,
    actor_type TEXT NOT NULL DEFAULT 'System',
    actor_name TEXT DEFAULT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
    telegram_sent INTEGER NOT NULL DEFAULT 0,
    telegram_sent_at TEXT DEFAULT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS slip_files (
    id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    filepath TEXT NOT NULL,
    filesize INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', '+7 hours')),
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(booking_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_activity_booking ON activity_logs(booking_id);
CREATE INDEX IF NOT EXISTS idx_slip_booking ON slip_files(booking_id);
"""

# --- Schema (PostgreSQL version) ---

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    booking_code TEXT UNIQUE NOT NULL,
    booking_date DATE NOT NULL,
    slot_start TIME NOT NULL,
    slot_end TIME NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    line_id TEXT DEFAULT NULL,
    condo_name TEXT DEFAULT NULL,
    condo_map_link TEXT DEFAULT NULL,
    note TEXT DEFAULT NULL,
    internal_note TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'RESERVED_UNPAID',
    confirmed_by TEXT DEFAULT NULL,
    confirmed_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_at TIMESTAMPTZ DEFAULT NULL,
    UNIQUE(booking_date, slot_start, slot_end)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL REFERENCES bookings(id),
    booking_code TEXT DEFAULT NULL,
    activity_type TEXT NOT NULL,
    old_status TEXT DEFAULT NULL,
    new_status TEXT DEFAULT NULL,
    actor_type TEXT NOT NULL DEFAULT 'System',
    actor_name TEXT DEFAULT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    telegram_sent BOOLEAN NOT NULL DEFAULT FALSE,
    telegram_sent_at TIMESTAMPTZ DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS slip_files (
    id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL REFERENCES bookings(id),
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    filepath TEXT NOT NULL,
    filesize INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(booking_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_activity_booking ON activity_logs(booking_id);
CREATE INDEX IF NOT EXISTS idx_slip_booking ON slip_files(booking_id);
"""


# ── Connection helpers ──

def get_conn():
    """Get a database connection. Auto-detects SQLite vs PostgreSQL."""
    if USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def _execute(conn, sql, params=None):
    """Execute with proper placeholder style for the backend. Returns cursor."""
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
        cursor = conn.cursor()
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return cursor
    else:
        if params is None:
            return conn.execute(sql)
        return conn.execute(sql, params)


def _fetchone(cursor):
    """Fetch one row as dict."""
    if USE_POSTGRES:
        if cursor.rowcount == 0 or cursor.rowcount == -1:
            return None
        row = cursor.fetchone()
        if row is None:
            return None
        # Convert to dict-like
        desc = [d[0] for d in cursor.description]
        return dict(zip(desc, row))
    row = cursor.fetchone()
    return dict(row) if row else None


def _fetchall(cursor):
    """Fetch all rows as list of dicts."""
    if USE_POSTGRES:
        desc = [d[0] for d in cursor.description]
        return [dict(zip(desc, row)) for row in cursor.fetchall()]
    return [dict(row) for row in cursor.fetchall()]


def _now_str():
    """Get current timestamp string (UTC+7)."""
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def _date_str_to_pg(d):
    """Convert date string for PG if needed."""
    return d  # Same format YYYY-MM-DD works for both


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    try:
        if USE_POSTGRES:
            _execute(conn, PG_SCHEMA)
        else:
            conn.executescript(SQLITE_SCHEMA)
        conn.commit()
        _migrate_schema(conn)
    finally:
        conn.close()


def _migrate_schema(conn):
    """Add new columns to existing tables if missing."""
    if USE_POSTGRES:
        # PostgreSQL handles schema differently; skip migration
        return
    import sqlite3 as _sqlite3
    try:
        cursor = _execute(conn, "PRAGMA table_info(bookings)")
        cols = [row[1] for row in cursor.fetchall()]
        for col in ["condo_name", "condo_map_link"]:
            if col not in cols:
                _execute(conn, f"ALTER TABLE bookings ADD COLUMN {col} TEXT DEFAULT NULL")
        conn.commit()
    except Exception:
        conn.rollback()


def generate_id():
    return str(uuid.uuid4())


def generate_booking_code(booking_date, conn=None):
    date_part = booking_date.replace("-", "")
    close_conn = False
    if conn is None:
        conn = get_conn()
        close_conn = True
    try:
        cursor = _execute(conn,
            "SELECT COUNT(*) FROM bookings WHERE booking_date = ?",
            (booking_date,)
        )
        count = cursor.fetchone()[0]
        return f"BK-{date_part}-{count + 1:03d}"
    finally:
        if close_conn:
            conn.close()


# ── Booking CRUD ──

def create_booking(booking_date, slot_start, slot_end, customer_name, phone,
                   line_id=None, note=None, condo_name=None, condo_map_link=None):
    conn = get_conn()
    try:
        # Overlap check
        cursor = _execute(conn,
            """SELECT id, status FROM bookings
               WHERE booking_date = ? AND slot_start < ? AND ? < slot_end
               AND status != ?""",
            (booking_date, slot_end, slot_start, STATUS_AVAILABLE)
        )
        existing = _fetchone(cursor)
        if existing and existing["status"] != STATUS_AVAILABLE:
            return None, None, "ช่วงเวลานี้ถูกจองแล้ว"

        booking_id = generate_id()
        booking_code = generate_booking_code(booking_date, conn)

        now = _now_str()
        _execute(conn,
            """INSERT INTO bookings (id, booking_code, booking_date, slot_start, slot_end,
               customer_name, phone, line_id, condo_name, condo_map_link, note, status,
               created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (booking_id, booking_code, booking_date, slot_start, slot_end,
             customer_name, phone, line_id, condo_name, condo_map_link, note,
             "RESERVED_UNPAID", now, now)
        )

        log_id = generate_id()
        _execute(conn,
            """INSERT INTO activity_logs (id, booking_id, booking_code, activity_type,
               new_status, actor_type, actor_name, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, booking_id, booking_code, "BOOKING_CREATED",
             "RESERVED_UNPAID", "Customer", customer_name,
             f"สร้างการจองใหม่: {booking_code}", now)
        )

        conn.commit()
        return booking_id, booking_code, None
    except Exception as e:
        conn.rollback()
        return None, None, str(e)
    finally:
        conn.close()


def get_booking(booking_id):
    conn = get_conn()
    try:
        cursor = _execute(conn, "SELECT * FROM bookings WHERE id = ?", (booking_id,))
        return _fetchone(cursor)
    finally:
        conn.close()


def get_booking_by_code(booking_code):
    conn = get_conn()
    try:
        cursor = _execute(conn, "SELECT * FROM bookings WHERE booking_code = ?", (booking_code,))
        return _fetchone(cursor)
    finally:
        conn.close()


def get_bookings(booking_date=None, status=None, phone=None, booking_code=None,
                 date_from=None, date_to=None, limit=100, offset=0):
    conn = get_conn()
    try:
        query = "SELECT * FROM bookings WHERE 1=1"
        params = []
        if booking_date:
            query += " AND booking_date = ?"
            params.append(booking_date)
        if status:
            query += " AND status = ?"
            params.append(status)
        if phone:
            query += " AND phone LIKE ?"
            params.append(f"%{phone}%")
        if booking_code:
            query += " AND booking_code LIKE ?"
            params.append(f"%{booking_code}%")
        if date_from:
            query += " AND booking_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND booking_date <= ?"
            params.append(date_to)
        query += " ORDER BY booking_date DESC, slot_start ASC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = _execute(conn, query, params)
        return _fetchall(cursor)
    finally:
        conn.close()


def update_booking_status(booking_id, new_status, actor_type="Admin",
                          actor_name="Admin", internal_note=None):
    conn = get_conn()
    try:
        booking = get_booking(booking_id)
        if not booking:
            return False, "ไม่พบรายการจองนี้"

        old_status = booking["status"]
        now = _now_str()

        if new_status == "AVAILABLE":
            _execute(conn,
                "UPDATE bookings SET status=?, updated_at=?, cancelled_at=? WHERE id=?",
                (new_status, now, now, booking_id))
        elif new_status == "CONFIRMED_PAID":
            _execute(conn,
                "UPDATE bookings SET status=?, confirmed_by=?, confirmed_at=?, updated_at=? WHERE id=?",
                (new_status, actor_name, now, now, booking_id))
        else:
            _execute(conn,
                "UPDATE bookings SET status=?, updated_at=? WHERE id=?",
                (new_status, now, booking_id))

        if internal_note:
            _execute(conn,
                "UPDATE bookings SET internal_note=?, updated_at=? WHERE id=?",
                (internal_note, now, booking_id))

        log_id = generate_id()
        activity_type = "STATUS_CHANGED"
        if new_status == "AVAILABLE":
            activity_type = "BOOKING_CANCELLED"
        elif new_status == "CONFIRMED_PAID":
            activity_type = "PAYMENT_CONFIRMED"

        message = f"เปลี่ยนสถานะจาก {old_status} เป็น {new_status}"
        if internal_note:
            message += f" | หมายเหตุ: {internal_note}"

        _execute(conn,
            """INSERT INTO activity_logs (id, booking_id, booking_code, activity_type,
               old_status, new_status, actor_type, actor_name, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, booking_id, booking["booking_code"], activity_type,
             old_status, new_status, actor_type, actor_name, message, now)
        )

        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_booking_details(booking_id, customer_name=None, phone=None,
                           line_id=None, internal_note=None, actor_name="Admin"):
    conn = get_conn()
    try:
        booking = get_booking(booking_id)
        if not booking:
            return False, "ไม่พบรายการจองนี้"

        updates = []
        params = []
        if customer_name is not None:
            updates.append("customer_name = ?")
            params.append(customer_name)
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        if line_id is not None:
            updates.append("line_id = ?")
            params.append(line_id)
        if internal_note is not None:
            updates.append("internal_note = ?")
            params.append(internal_note)

        if not updates:
            return True, None

        now = _now_str()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(booking_id)

        _execute(conn,
            f"UPDATE bookings SET {', '.join(updates)} WHERE id = ?",
            params)

        log_id = generate_id()
        changed_fields = []
        if customer_name is not None: changed_fields.append(f"ชื่อ: {customer_name}")
        if phone is not None: changed_fields.append(f"เบอร์โทร: {phone}")
        if line_id is not None: changed_fields.append(f"Line ID: {line_id}")

        _execute(conn,
            """INSERT INTO activity_logs (id, booking_id, booking_code, activity_type,
               actor_type, actor_name, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, booking_id, booking["booking_code"], "BOOKING_EDITED",
             "Admin", actor_name,
             f"แก้ไขข้อมูล: {', '.join(changed_fields)}", now)
        )

        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# ── Slip management ──

def add_slip(booking_id, filename, original_name, filepath, filesize):
    conn = get_conn()
    try:
        booking = get_booking(booking_id)
        if not booking:
            return False, "ไม่พบรายการจองนี้"

        if booking["status"] not in ("RESERVED_UNPAID", "PAID_PENDING_CONFIRM"):
            return False, "สถานะปัจจุบันไม่สามารถแนบสลิปได้"

        slip_id = generate_id()
        now = _now_str()
        _execute(conn,
            """INSERT INTO slip_files (id, booking_id, filename, original_name, filepath, filesize, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (slip_id, booking_id, filename, original_name, filepath, filesize, now)
        )

        old_status = booking["status"]
        if old_status == "RESERVED_UNPAID":
            _execute(conn,
                "UPDATE bookings SET status=?, updated_at=? WHERE id=?",
                ("PAID_PENDING_CONFIRM", now, booking_id))

            log_id = generate_id()
            _execute(conn,
                """INSERT INTO activity_logs (id, booking_id, booking_code, activity_type,
                   old_status, new_status, actor_type, actor_name, message, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, booking_id, booking["booking_code"], "SLIP_UPLOADED",
                 old_status, "PAID_PENDING_CONFIRM", "Customer", booking["customer_name"],
                 f"แนบสลิป: {original_name}", now)
            )

        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_slips(booking_id):
    conn = get_conn()
    try:
        cursor = _execute(conn,
            "SELECT * FROM slip_files WHERE booking_id = ? ORDER BY created_at ASC",
            (booking_id,))
        return _fetchall(cursor)
    finally:
        conn.close()


# ── Activity logs ──

def get_activity_logs(booking_id=None, limit=100, offset=0):
    conn = get_conn()
    try:
        query = "SELECT * FROM activity_logs"
        params = []
        if booking_id:
            query += " WHERE booking_id = ?"
            params.append(booking_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = _execute(conn, query, params)
        return _fetchall(cursor)
    finally:
        conn.close()


def mark_telegram_sent(log_id):
    conn = get_conn()
    try:
        now = _now_str()
        _execute(conn,
            "UPDATE activity_logs SET telegram_sent=1, telegram_sent_at=? WHERE id=?",
            (now, log_id))
        conn.commit()
    finally:
        conn.close()


def get_failed_notifications(limit=50):
    conn = get_conn()
    try:
        cursor = _execute(conn,
            """SELECT * FROM activity_logs
               WHERE telegram_sent = 0 AND activity_type != 'SYSTEM'
               ORDER BY created_at DESC LIMIT ?""", (limit,))
        return _fetchall(cursor)
    finally:
        conn.close()


# ── Availability ──

def get_availability(date_from, date_to):
    conn = get_conn()
    try:
        results = []
        from datetime import datetime, timedelta
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        current = start

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            day_slots = []
            for slot in SLOTS:
                cursor = _execute(conn,
                    """SELECT id, status, booking_code FROM bookings
                       WHERE booking_date = ? AND slot_start < ? AND ? < slot_end
                       AND status != ?""",
                    (date_str, slot["end"], slot["start"], STATUS_AVAILABLE)
                )
                booking = _fetchone(cursor)

                if booking:
                    day_slots.append({
                        "start": slot["start"],
                        "end": slot["end"],
                        "label": slot["label"],
                        "status": booking["status"],
                        "booking_code": booking["booking_code"],
                        "booking_id": booking["id"],
                        "bookable": False,
                        "color": None
                    })
                else:
                    day_slots.append({
                        "start": slot["start"],
                        "end": slot["end"],
                        "label": slot["label"],
                        "status": STATUS_AVAILABLE,
                        "booking_code": None,
                        "booking_id": None,
                        "bookable": True,
                        "color": None
                    })
            results.append({"date": date_str, "slots": day_slots})
            current += timedelta(days=1)

        return results
    finally:
        conn.close()


# ── Expired bookings ──

def expire_unpaid_bookings():
    from config import UNPAID_EXPIRY_MINUTES
    conn = get_conn()
    try:
        import datetime as dt
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=UNPAID_EXPIRY_MINUTES)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

        cursor = _execute(conn,
            """SELECT id, booking_code, customer_name FROM bookings
               WHERE status = 'RESERVED_UNPAID'
               AND created_at < ?""",
            (cutoff_str,))
        expired = _fetchall(cursor)

        for booking in expired:
            now = _now_str()
            _execute(conn,
                "UPDATE bookings SET status=?, updated_at=?, cancelled_at=? WHERE id=?",
                (STATUS_AVAILABLE, now, now, booking["id"]))
            log_id = generate_id()
            _execute(conn,
                """INSERT INTO activity_logs (id, booking_id, booking_code, activity_type,
                   old_status, new_status, actor_type, actor_name, message, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, booking["id"], booking["booking_code"], "BOOKING_EXPIRED",
                 "RESERVED_UNPAID", STATUS_AVAILABLE, "System", "System",
                 f"การจอง {booking['booking_code']} หมดอายุโดยอัตโนมัติ", now))

        conn.commit()
        return expired
    finally:
        conn.close()


def reset_all_data():
    """Clear all data from database tables. Admin-only."""
    conn = get_conn()
    try:
        _execute(conn, "DELETE FROM activity_logs")
        _execute(conn, "DELETE FROM slip_files")
        _execute(conn, "DELETE FROM bookings")
        conn.commit()
    finally:
        conn.close()


# ── Export ──

def export_bookings_csv(date_from=None, date_to=None):
    rows = get_bookings(date_from=date_from, date_to=date_to)
    from config import STATUS_LABELS
    import csv, io
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Booking Code", "Date", "Time", "Customer", "Phone", "Line ID",
                     "Note", "Status", "Created At", "Confirmed By", "Confirmed At"])
    for row in rows:
        writer.writerow([
            row["booking_code"], row["booking_date"],
            f"{row['slot_start']}-{row['slot_end']}",
            row["customer_name"], row["phone"],
            row["line_id"] if row["line_id"] else "",
            row["note"] if row["note"] else "",
            STATUS_LABELS.get(row["status"], row["status"]),
            row["created_at"],
            row["confirmed_by"] if row["confirmed_by"] else "",
            row["confirmed_at"] if row["confirmed_at"] else "",
        ])
    return buffer.getvalue()


# Initialize on import
init_db()
