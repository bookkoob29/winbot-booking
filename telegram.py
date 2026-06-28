"""
Telegram notification service for WINBOT Booking Application.
Sends messages to the configured Telegram bot via HTTP API.
"""
import asyncio
import os

import httpx

# --- Config ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8969930460")

if not TELEGRAM_BOT_TOKEN:
    token_file = os.path.expanduser("~/.telegram_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            TELEGRAM_BOT_TOKEN = f.read().strip()

TELEGRAM_API = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN

from database import mark_telegram_sent

# --- Emoji constants (avoid f-string issues) ---
ICON_NEW = "\U0001F4CC"      # 📌
ICON_SLIP = "\U0001F4B3"     # 💳
ICON_CONFIRMED = "\u2705"     # ✅
ICON_CHANGED = "\U0001F504"  # 🔄
ICON_ERROR = "\u26A0\uFE0F"  # ⚠️
ICON_CANCELLED = "\u274C"    # ❌

# --- Message builders (plain strings, no f-string gotchas) ---

def msg_new_booking(booking, booking_code):
    name = booking.get("customer_name") or "-"
    phone = booking.get("phone") or "-"
    line_id = booking.get("line_id") or "-"
    note = booking.get("note") or "-"
    return ("%s ใบจองใหม่\n\n" % ICON_NEW +
            "Booking ID: %s\n" % booking_code +
            "Status: ยังไม่ชำระเงิน\n" +
            "Date: %s\n" % booking["booking_date"] +
            "Time: %s–%s\n\n" % (booking["slot_start"], booking["slot_end"]) +
            "Name: %s\n" % name +
            "Phone: %s\n" % phone +
            "Line ID: %s\n\n" % line_id +
            "Note: %s" % note +
            "\n\nAction: รอลูกค้าชำระเงิน / แนบ Slip")

def msg_slip_uploaded(booking, filename):
    return ("%s แนบสลิปแล้ว\n\n" % ICON_SLIP +
            "Booking ID: %s\n" % booking["booking_code"] +
            "Status: รอ Confirm\n" +
            "Date: %s\n" % booking["booking_date"] +
            "Time: %s–%s\n\n" % (booking["slot_start"], booking["slot_end"]) +
            "Name: %s\n" % booking["customer_name"] +
            "Phone: %s\n" % booking["phone"] +
            "File: %s\n\n" % filename +
            "Action: กรุณาตรวจสอบ Slip และ Confirm")

def msg_admin_confirmed(booking):
    return ("%s ยืนยันการจองแล้ว\n\n" % ICON_CONFIRMED +
            "Booking ID: %s\n" % booking["booking_code"] +
            "Status: จองแล้ว\n" +
            "Date: %s\n" % booking["booking_date"] +
            "Time: %s–%s\n\n" % (booking["slot_start"], booking["slot_end"]) +
            "Name: %s\n" % booking["customer_name"] +
            "Phone: %s\n" % booking["phone"] +
            "\nConfirmed by: Admin")

def msg_status_changed(booking, old_status, new_status, actor, log_message):
    return ("%s เปลี่ยนสถานะการจอง\n\n" % ICON_CHANGED +
            "Booking ID: %s\n" % booking["booking_code"] +
            "From: %s\n" % old_status +
            "To: %s\n\n" % new_status +
            "Changed by: %s\n" % actor +
            "Detail: %s" % log_message)

def msg_cancelled(booking):
    return ("%s ยกเลิกการจอง\n\n" % ICON_CANCELLED +
            "Booking ID: %s\n" % booking["booking_code"] +
            "Date: %s\n" % booking["booking_date"] +
            "Time: %s–%s\n\n" % (booking["slot_start"], booking["slot_end"]) +
            "Name: %s\n" % booking["customer_name"] +
            "Phone: %s" % booking["phone"])

def msg_error(message):
    return "%s System Error\n\n%s" % (ICON_ERROR, message)

# --- Async sender ---

async def send_telegram_async(message, log_id=None):
    """Send Telegram message asynchronously. Returns (success, error)."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "No Telegram bot token configured"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                TELEGRAM_API + "/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
            )
        if resp.status_code == 200:
            if log_id:
                try:
                    mark_telegram_sent(log_id)
                except Exception:
                    pass
            return True, None
        else:
            err = resp.json()
            return False, "Telegram error: " + str(err.get("description", "Unknown"))
    except Exception as e:
        return False, "Telegram send failed: " + str(e)


async def send_telegram_photo_async(photo_path, caption="", log_id=None):
    """Send a photo to Telegram via sendPhoto API. Returns (success, error)."""
    if not TELEGRAM_BOT_TOKEN or not os.path.exists(photo_path):
        return False, "No token or file not found"

    try:
        # Read the file content
        with open(photo_path, "rb") as f:
            file_bytes = f.read()

        api_url = TELEGRAM_API + "/sendPhoto"

        # Build multipart manually (httpx can also do this via files=)
        from httpx import AsyncClient
        async with AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                api_url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": (os.path.basename(photo_path), file_bytes, "image/jpeg")},
            )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                if log_id:
                    try:
                        mark_telegram_sent(log_id)
                    except Exception:
                        pass
                return True, None
            else:
                return False, "Telegram photo error: " + str(data.get("description", "Unknown"))
        else:
            try:
                err = resp.json()
                return False, "Telegram photo error: " + str(err.get("description", str(resp.status_code)))
            except Exception:
                return False, "Telegram photo: HTTP " + str(resp.status_code)
    except Exception as e:
        return False, "Telegram photo send failed: " + str(e)

# --- Sync wrapper ---

def send_telegram(message, log_id=None):
    """Synchronous wrapper for send_telegram_async."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            import threading
            result = [None]
            def run():
                result[0] = asyncio.run(send_telegram_async(message, log_id))
            t = threading.Thread(target=run)
            t.start()
            t.join()
            return result[0]
        else:
            return loop.run_until_complete(send_telegram_async(message, log_id))
    except RuntimeError:
        return asyncio.run(send_telegram_async(message, log_id))


def send_telegram_photo(photo_path, caption="", log_id=None):
    """Synchronous wrapper for send_telegram_photo_async."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            import threading
            result = [None]
            def run():
                result[0] = asyncio.run(send_telegram_photo_async(photo_path, caption, log_id))
            t = threading.Thread(target=run)
            t.start()
            t.join()
            return result[0]
        else:
            return loop.run_until_complete(send_telegram_photo_async(photo_path, caption, log_id))
    except RuntimeError:
        return asyncio.run(send_telegram_photo_async(photo_path, caption, log_id))

# --- Notification triggers ---

def notify_new_booking(booking, log_id):
    return send_telegram(msg_new_booking(booking, booking["booking_code"]), log_id)

def notify_slip_uploaded(booking, filename, filepath, log_id):
    """Send notification + photo of the slip."""
    result = send_telegram(msg_slip_uploaded(booking, filename), log_id)
    # Also send the photo itself
    caption = "สลิปการชำระเงิน — %s — %s" % (booking.get("booking_code", ""), booking.get("customer_name", ""))
    send_telegram_photo(filepath, caption)
    return result

def notify_admin_confirmed(booking, log_id):
    return send_telegram(msg_admin_confirmed(booking), log_id)

def notify_status_changed(booking, old_status, new_status, actor, log_message, log_id):
    return send_telegram(msg_status_changed(booking, old_status, new_status, actor, log_message), log_id)

def notify_cancelled(booking, log_id):
    return send_telegram(msg_cancelled(booking), log_id)

def notify_error(message):
    return send_telegram(msg_error(message))
