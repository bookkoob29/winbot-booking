"""
Configuration for WINBOT Mini 2 Booking Application.
Loads from environment variables or .env file.
"""
import os
import json

# --- Project paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "slips")
DB_PATH = os.path.join(BASE_DIR, "bookings.db")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8969930460")

# Fallback: read token from file
if not TELEGRAM_BOT_TOKEN:
    token_file = os.path.expanduser("~/.telegram_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            TELEGRAM_BOT_TOKEN = f.read().strip()

# --- Admin ---
ADMIN_PASSCODE = os.environ.get("ADMIN_PASSCODE", "BooK2905@1990")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "winbot-booking-secret-key-change-in-production")

# --- Booking rules ---
BOOKING_PRICE = 500  # THB
SLOT_DURATION_HOURS = 3
SLOT_START_HOUR = 9   # 09:00
SLOT_END_HOUR = 18    # 18:00
SLOTS = []
for h in range(SLOT_START_HOUR, SLOT_END_HOUR - SLOT_DURATION_HOURS + 1):
    start = f"{h:02d}:00"
    end_h = h + SLOT_DURATION_HOURS
    end = f"{end_h:02d}:00"
    SLOTS.append({"start": start, "end": end, "label": f"{start}–{end}"})

def is_valid_slot(slot_start, slot_end):
    """Check if slot_start and slot_end form a valid 3-hour booking window."""
    for s in SLOTS:
        if s["start"] == slot_start and s["end"] == slot_end:
            return True
    return False
UNPAID_EXPIRY_MINUTES = int(os.environ.get("UNPAID_EXPIRY_MINUTES", "30"))

# --- Timezone ---
TIMEZONE = "Asia/Bangkok"

# --- Status constants ---
STATUS_AVAILABLE = "AVAILABLE"
STATUS_RESERVED_UNPAID = "RESERVED_UNPAID"
STATUS_PAID_PENDING_CONFIRM = "PAID_PENDING_CONFIRM"
STATUS_CONFIRMED_PAID = "CONFIRMED_PAID"

STATUS_CHOICES = [
    STATUS_AVAILABLE,
    STATUS_RESERVED_UNPAID,
    STATUS_PAID_PENDING_CONFIRM,
    STATUS_CONFIRMED_PAID,
]

STATUS_LABELS = {
    STATUS_AVAILABLE: "ว่าง",
    STATUS_RESERVED_UNPAID: "ยังไม่ชำระเงิน",
    STATUS_PAID_PENDING_CONFIRM: "รอ Confirm",
    STATUS_CONFIRMED_PAID: "จองแล้ว",
}

STATUS_COLORS = {
    STATUS_AVAILABLE: "#DBEAFE",       # Light blue
    STATUS_RESERVED_UNPAID: "#64748B", # Slate gray
    STATUS_PAID_PENDING_CONFIRM: "#F59E0B",  # Amber
    STATUS_CONFIRMED_PAID: "#16A34A",  # Green
}

STATUS_TEXT_COLORS = {
    STATUS_AVAILABLE: "#1E40AF",
    STATUS_RESERVED_UNPAID: "#FFFFFF",
    STATUS_PAID_PENDING_CONFIRM: "#FFFFFF",
    STATUS_CONFIRMED_PAID: "#FFFFFF",
}

# --- Allowed transitions ---
ALLOWED_TRANSITIONS = {
    STATUS_RESERVED_UNPAID: [STATUS_PAID_PENDING_CONFIRM, STATUS_AVAILABLE],
    STATUS_PAID_PENDING_CONFIRM: [STATUS_CONFIRMED_PAID, STATUS_RESERVED_UNPAID, STATUS_AVAILABLE],
    STATUS_CONFIRMED_PAID: [STATUS_AVAILABLE],
}

# --- File upload ---
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_FILES_PER_BOOKING = 3

# --- Server ---
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
