"""
WINBOT Mini 2 Booking Website — Main Application
FastAPI backend serving Jinja2 templates + REST API
"""
import os
import secrets
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import config
import database as db
from models import BookingCreate, BookingStatusUpdate, BookingEdit
from telegram import (
    notify_new_booking, notify_slip_uploaded, notify_admin_confirmed,
    notify_status_changed, notify_cancelled, notify_error
)

# --- App setup ---

app = FastAPI(
    title="WINBOT Mini 2 Booking",
    description="ระบบจองเช่าเครื่องเช็ดกระจก WINBOT mini 2",
    version="1.0.0",
)

app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, max_age=1800)

# --- Static files ---
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Uploaded files (slips)
app.mount("/uploads", StaticFiles(directory=str(config.UPLOAD_DIR)), name="uploads")

# --- Templates ---
templates_dir = Path(__file__).parent / "templates"
templates_dir = Path(__file__).parent / "templates"
(templates_dir / "admin").mkdir(exist_ok=True)

# Create Jinja2 environment directly (bypass Starlette's Jinja2Templates wrapper)
from jinja2 import Environment, FileSystemLoader, select_autoescape
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,  # Disable template cache (avoids weakref/hashing issues)
)

# Inject config into templates
jinja_env.globals.update(
    config=config,
    STATUS_LABELS=config.STATUS_LABELS,
    STATUS_COLORS=config.STATUS_COLORS,
    STATUS_TEXT_COLORS=config.STATUS_TEXT_COLORS,
    SLOTS=config.SLOTS,
    BOOKING_PRICE=config.BOOKING_PRICE,
)

# Custom TemplateResponse that uses our jinja_env
from starlette.templating import _TemplateResponse

def render_template(request, name, context=None):
    """Render a Jinja2 template and return a Starlette response."""
    if context is None:
        context = {}
    context.setdefault("request", request)
    template = jinja_env.get_template(name)
    return _TemplateResponse(template, context)

# --- Helpers ---

def get_today_str():
    return date.today().strftime("%Y-%m-%d")

def get_week_range():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def get_status_color(status):
    return config.STATUS_COLORS.get(status, "#DBEAFE")

def get_status_label(status):
    return config.STATUS_LABELS.get(status, status)

def verify_slot_times(slot_start, slot_end):
    """Verify slot start/end are valid."""
    return config.is_valid_slot(slot_start, slot_end)

# === ADMIN AUTH DEPENDENCY ===
# Must be defined before any route that uses it.

def get_admin_session(request: Request):
    """Check admin is logged in via session cookie.
    SessionMiddleware is installed, so request.session is available
    inside route handlers (not in @app.middleware which runs before it)."""
    if request.session.get("admin_logged_in"):
        return request.session.get("admin_name", "Admin")
    raise HTTPException(status_code=303, detail="Login required")

# === PUBLIC ROUTES ===

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page with hero, pricing, benefits."""
    try:
        return render_template(request, "index.html", {"today": get_today_str()})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"LANDING ERROR: {e}\n{error_detail}")
        from starlette.responses import PlainTextResponse
        return PlainTextResponse(f"เกิดข้อผิดพลาด: {e}\n\n{error_detail}", status_code=500)

@app.get("/availability", response_class=HTMLResponse)
async def availability_page(request: Request):
    """Calendar availability page."""
    week_start, week_end = get_week_range()
    return render_template(request, "availability.html", {"week_start": week_start, "week_end": week_end})

@app.get("/api/availability")
async def api_availability(start_date: str = None, end_date: str = None):
    """JSON availability data."""
    from datetime import datetime as _dt, timedelta as _td
    
    today = _dt.now().strftime("%Y-%m-%d")
    thirty_days_ago = (_dt.now() - _td(days=30)).strftime("%Y-%m-%d")
    
    if not start_date:
        start_date = thirty_days_ago
    if not end_date:
        _, end_date = get_week_range()

    results = db.get_availability(start_date, end_date)

    # Add colors and labels; enforce booking rules
    for day in results:
        is_past = day["date"] < today  # Only past (yesterday-), today is bookable
        for slot in day["slots"]:
            slot["color"] = config.STATUS_COLORS.get(slot["status"], "#DBEAFE")
            slot["label"] = config.STATUS_LABELS.get(slot["status"], slot["status"])
            
            # Past dates → read-only (not bookable)
            if is_past:
                slot["bookable"] = False
            
            # Don't expose booking details to public
            if not slot["bookable"]:
                for key in ["booking_code", "booking_id"]:
                    if key in slot:
                        del slot[key]

    return {"dates": results}

@app.get("/booking/{booking_id}/ics")
async def download_ics(booking_id: str):
    """Download booking as .ics calendar file."""
    booking = db.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจองนี้")

    # Build ICS content
    from datetime import datetime, timedelta
    import pytz
    try:
        tz = pytz.timezone("Asia/Bangkok")
    except:
        tz = None

    date_str = booking["booking_date"]
    start_hm = booking["slot_start"]
    end_hm = booking["slot_end"]

    if tz:
        dt_start = tz.localize(datetime.strptime(f"{date_str} {start_hm}", "%Y-%m-%d %H:%M"))
        dt_end = tz.localize(datetime.strptime(f"{date_str} {end_hm}", "%Y-%m-%d %H:%M"))
    else:
        dt_start = datetime.strptime(f"{date_str} {start_hm}", "%Y-%m-%d %H:%M")
        dt_end = datetime.strptime(f"{date_str} {end_hm}", "%Y-%m-%d %H:%M")

    uid = booking["id"]
    code = booking["booking_code"]

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//WINBOT Booking//TH
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{uid}
DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}
DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:เช่า WINBOT Mini 2 ({code})
DESCRIPTION:เช่าเครื่องเช็ดกระจก WINBOT Mini 2\\nรหัส: {code}\\nชื่อ: {booking['customer_name']}\\nเบอร์: {booking['phone']}
LOCATION:คอนโด
END:VEVENT
END:VCALENDAR"""

    return Response(
        content=ics,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="winbot-booking-{code}.ics"',
            "Content-Type": "text/calendar; charset=utf-8"
        }
    )

@app.get("/booking/{booking_id}", response_class=HTMLResponse)
async def booking_confirmation(request: Request, booking_id: str):
    """Booking confirmation page."""
    booking = db.get_booking(booking_id)
    if not booking:
        return render_template(request, "error.html")

    slips = db.get_slips(booking_id)
    return render_template(request, "confirmation.html", {"booking": dict(booking),
        "slips": [dict(s) for s in slips],
    })

@app.post("/api/bookings", status_code=201)
async def create_booking(data: BookingCreate, request: Request):
    """Create a new booking."""
    # Verify slot times
    if not verify_slot_times(data.slot_start, data.slot_end):
        raise HTTPException(status_code=400, detail="เวลา Slot ไม่ถูกต้อง")

    # Create booking
    booking_id, booking_code, error = db.create_booking(
        booking_date=data.booking_date,
        slot_start=data.slot_start,
        slot_end=data.slot_end,
        customer_name=data.customer_name,
        phone=data.phone,
        line_id=data.line_id,
        condo_name=data.condo_name,
        condo_map_link=data.condo_map_link,
        note=data.note,
    )

    if error:
        raise HTTPException(status_code=409, detail=error)

    # Get the booking back to construct notification
    booking = db.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=500, detail="สร้างรายการจองแล้ว แต่ไม่พบข้อมูล")

    # Get the activity log ID for tracking Telegram
    logs = db.get_activity_logs(booking_id, limit=1)
    log_id = logs[0]["id"] if logs else None

    # Send Telegram notification (async, non-blocking)
    success, err = notify_new_booking(dict(booking), log_id)
    if not success and err:
        pass  # Notification failure is logged, but booking succeeds

    return {
        "id": booking_id,
        "booking_code": booking_code,
        "status": "RESERVED_UNPAID",
        "message": "จองสำเร็จ กรุณาชำระเงินและแนบสลิป"
    }

@app.post("/api/bookings/{booking_id}/slip")
async def upload_slip(booking_id: str, file: UploadFile = File(...)):
    """Upload slip image for a booking."""
    booking = db.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจองนี้")

    # Validate file
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ JPG, PNG, PDF เท่านั้น")

    # Read & check size
    content = await file.read()
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="ไฟล์ต้องมีขนาดไม่เกิน 2 MB")

    # Save file
    safe_name = f"{booking_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(config.UPLOAD_DIR, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    # Add to database
    success, error = db.add_slip(
        booking_id=booking_id,
        filename=safe_name,
        original_name=file.filename or safe_name,
        filepath=filepath,
        filesize=len(content),
    )

    if not success:
        # Clean up saved file on failure
        try:
            os.remove(filepath)
        except OSError:
            pass
        raise HTTPException(status_code=400, detail=error)

    # Send notification
    logs = db.get_activity_logs(booking_id, limit=1)
    log_id = logs[0]["id"] if logs else None

    refreshed = db.get_booking(booking_id)
    if refreshed and refreshed["status"] == "PAID_PENDING_CONFIRM":
        success, err = notify_slip_uploaded(dict(refreshed), file.filename or safe_name, filepath, log_id)

    return {
        "message": "อัปโหลดสลิปสำเร็จ",
        "filename": safe_name,
        "status": "PAID_PENDING_CONFIRM"
    }

# === ADMIN ROUTES ===

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    if request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return render_template(request, "admin/login.html")

@app.post("/admin/login")
async def admin_login(request: Request, passcode: str = Form(...)):
    """Admin login action."""
    if passcode == config.ADMIN_PASSCODE:
        request.session["admin_logged_in"] = True
        request.session["admin_name"] = "Admin"
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return render_template(request, "admin/login.html")

@app.get("/admin/logout")
async def admin_logout(request: Request):
    """Admin logout."""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, _admin=Depends(get_admin_session)):
    """Admin dashboard main page."""

    today = get_today_str()
    today_bookings = db.get_bookings(booking_date=today)
    pending = db.get_bookings(status="PAID_PENDING_CONFIRM")
    unpaid = db.get_bookings(status="RESERVED_UNPAID")
    all_bookings = db.get_bookings(limit=50)

    return render_template(request, "admin/dashboard.html", {
        "today_bookings": [dict(b) for b in today_bookings],
        "pending_bookings": [dict(b) for b in pending],
        "unpaid_bookings": [dict(b) for b in unpaid],
        "all_bookings": [dict(b) for b in all_bookings],
        "today": today,
    })

@app.get("/admin/api/bookings")
async def admin_get_bookings(
    request: Request,
    date_from: str = None,
    date_to: str = None,
    status: str = None,
    phone: str = None,
    booking_code: str = None,
    _admin=Depends(get_admin_session),
):
    """Admin API: get bookings with filters."""
    bookings = db.get_bookings(
        date_from=date_from, date_to=date_to,
        status=status, phone=phone, booking_code=booking_code
    )
    return {
        "bookings": [dict(b) for b in bookings],
        "count": len(bookings),
    }

@app.get("/admin/bookings/{booking_id}", response_class=HTMLResponse)
async def admin_booking_detail(request: Request, booking_id: str, _admin=Depends(get_admin_session)):
    """Admin booking detail page with slip preview."""
    booking = db.get_booking(booking_id)
    if not booking:
        return render_template(request, "error.html")

    slips = db.get_slips(booking_id)
    logs = db.get_activity_logs(booking_id, limit=50)

    return render_template(request, "admin/booking_detail.html", {
        "booking": dict(booking),
        "slips": [dict(s) for s in slips],
        "logs": [dict(l) for l in logs],
        "allowed_transitions": config.ALLOWED_TRANSITIONS.get(booking["status"], []),
    })

@app.patch("/admin/api/bookings/{booking_id}/status")
async def admin_update_status(booking_id: str, data: BookingStatusUpdate, request: Request, _admin=Depends(get_admin_session)):
    """Admin API: change booking status."""

    booking = db.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจองนี้")

    # Validate transition
    allowed = config.ALLOWED_TRANSITIONS.get(booking["status"], [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="ไม่สามารถเปลี่ยนสถานะจาก %s เป็น %s ได้" % (config.STATUS_LABELS.get(booking["status"], booking["status"]), config.STATUS_LABELS.get(data.status, data.status))
        )

    old_status = booking["status"]
    success, error = db.update_booking_status(
        booking_id, data.status,
        actor_type="Admin",
        actor_name=request.session.get("admin_name", "Admin"),
        internal_note=data.internal_note
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # Get updated booking
    updated = db.get_booking(booking_id)

    # Get the activity log
    logs = db.get_activity_logs(booking_id, limit=1)
    log_id = logs[0]["id"] if logs else None

    # Send Telegram notification
    if updated:
        booking_dict = dict(updated)
        if data.status == "AVAILABLE":
            notify_cancelled(booking_dict, log_id)
        elif data.status == "CONFIRMED_PAID":
            notify_admin_confirmed(booking_dict, log_id)
        else:
            notify_status_changed(booking_dict, old_status, data.status,
                                  request.session.get("admin_name", "Admin"),
                                  logs[0]["message"] if logs else "Status changed", log_id)

    return {
        "message": "อัปเดตสถานะสำเร็จ",
        "status": data.status,
        "booking_code": booking["booking_code"],
    }

@app.patch("/admin/api/bookings/{booking_id}")
async def admin_edit_booking(booking_id: str, data: BookingEdit, request: Request, _admin=Depends(get_admin_session)):
    """Admin API: edit booking details."""

    success, error = db.update_booking_details(
        booking_id,
        customer_name=data.customer_name,
        phone=data.phone,
        line_id=data.line_id,
        internal_note=data.internal_note,
        actor_name=request.session.get("admin_name", "Admin"),
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # Send notification
    logs = db.get_activity_logs(booking_id, limit=1)
    log_id = logs[0]["id"] if logs else None
    booking = db.get_booking(booking_id)
    if booking:
        notify_status_changed(dict(booking), "N/A", "N/A",
                              request.session.get("admin_name", "Admin"),
                              logs[0]["message"] if logs else "Booking edited", log_id)

    return {"message": "แก้ไขข้อมูลสำเร็จ"}

@app.get("/admin/export/csv")
async def admin_export_csv(request: Request, date_from: str = None, date_to: str = None, _admin=Depends(get_admin_session)):
    """Export bookings as CSV."""
    csv_data = db.export_bookings_csv(date_from=date_from, date_to=date_to)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bookings_export.csv"}
    )

@app.get("/admin/activity-logs", response_class=HTMLResponse)
async def admin_activity_logs(request: Request, _admin=Depends(get_admin_session)):
    """View all activity logs with failed notifications."""
    logs = db.get_activity_logs(limit=200)
    failed = db.get_failed_notifications()
    return render_template(request, "admin/activity_logs.html", {
        "logs": [dict(l) for l in logs],
        "failed_logs": [dict(l) for l in failed],
    })

@app.post("/admin/api/telegram/resend/{log_id}")
async def admin_resend_telegram(request: Request, log_id: str, _admin=Depends(get_admin_session)):
    """Resend a failed Telegram notification."""
    logs = db.get_activity_logs(limit=1)
    # Find the specific log entry
    conn = db.get_conn()
    try:
        cursor = conn.execute("SELECT * FROM activity_logs WHERE id = ?", (log_id,))
        log_entry = cursor.fetchone()
    finally:
        conn.close()

    if not log_entry:
        raise HTTPException(status_code=404, detail="ไม่พบ Activity Log นี้")

    booking = db.get_booking(log_entry["booking_id"])
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจองนี้")

    # Resend notification
    success, err = notify_status_changed(
        dict(booking),
        log_entry["old_status"] or "-",
        log_entry["new_status"] or "-",
        log_entry["actor_name"] or "System",
        log_entry["message"],
        log_id,
    )

    if success:
        return {"message": "ส่ง Telegram สำเร็จ"}
    else:
        return JSONResponse(status_code=500, content={"detail": "ส่ง Telegram ล้มเหลว: " + str(err)})


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }

# === MAINTENANCE TASKS ===

@app.post("/api/maintenance/expire")
async def run_expiry():
    """Manually trigger unpaid booking expiry."""
    expired = db.expire_unpaid_bookings()
    return {
        "expired_count": len(expired),
        "expired_bookings": [e["booking_code"] for e in expired],
    }


@app.get("/api/search-condo")
async def search_condo(q: str = ""):
    """Search condos from local DB + Nominatim (OpenStreetMap) backup."""
    import json as _json
    import httpx
    import os

    results = []

    # 1. Search local DB
    local_path = os.path.join(config.BASE_DIR, "static", "condos-bangkok.json")
    if os.path.exists(local_path) and len(q) >= 1:
        with open(local_path, encoding="utf-8") as f:
            local_condos = _json.load(f)

        ql = q.lower()
        seen_names = set()
        for c in local_condos:
            match = (
                ql in c["name"].lower()
                or (c.get("name_en") and ql in c["name_en"].lower())
                or any(ql in a.lower() for a in c.get("alternate_names", []))
                or any(ql in t for t in c.get("search_tokens", []))
            )
            if match and c["name"] not in seen_names:
                seen_names.add(c["name"])
                results.append({
                    "source": "local",
                    "name": c["name"],
                    "name_en": c.get("name_en", ""),
                    "area": c.get("area", ""),
                    "district": c.get("district_th", ""),
                    "developer": c.get("developer", ""),
                    "maps_url": c.get("maps_url", ""),
                    "lat": c.get("lat"),
                    "lng": c.get("lng"),
                })

    # 2. Search Nominatim (OpenStreetMap) — free, no API key
    if len(q) >= 3:
        try:
            search_q = q + " Bangkok"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": search_q,
                        "format": "json",
                        "limit": 5,
                        "countrycodes": "th",
                        "addressdetails": 1,
                    },
                    headers={"User-Agent": "WINBOT-Booking-App/1.0 (condo-search)"},
                )
            if resp.status_code == 200:
                osm_results = resp.json()
                for r in osm_results:
                    r_name = r.get("display_name", "").split(",")[0].strip()
                    # Dedupe: skip if local already has a very similar name
                    if any(
                        r_name.lower() in res["name"].lower()
                        or res["name"].lower() in r_name.lower()
                        for res in results
                    ):
                        continue
                    addr = r.get("address", {})
                    district = addr.get(
                        "district",
                        addr.get("city_district", addr.get("suburb", "")),
                    )
                    lat_str = r.get("lat", "0")
                    lon_str = r.get("lon", "0")
                    maps_url = f"https://maps.google.com/?q={lat_str},{lon_str}"
                    results.append({
                        "source": "nominatim",
                        "name": r_name,
                        "name_en": "",
                        "area": district,
                        "district": district,
                        "developer": "",
                        "maps_url": maps_url,
                        "lat": float(lat_str) if lat_str else None,
                        "lng": float(lon_str) if lon_str else None,
                    })
        except Exception:
            pass  # Nominatim failure is non-blocking

    return {"results": results[:10], "total": len(results)}


# === ERROR HANDLERS ===

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return _TemplateResponse(jinja_env.get_template("error.html"), {"request": request, "message": "ไม่พบหน้าที่คุณต้องการ"}, status_code=404)

@app.exception_handler(500)
async def server_error(request: Request, exc):
    return _TemplateResponse(jinja_env.get_template("error.html"), {"request": request, "message": "เกิดข้อผิดพลาดภายในระบบ"}, status_code=500)

@app.exception_handler(Exception)
async def generic_error(request: Request, exc):
    from starlette.responses import PlainTextResponse
    return PlainTextResponse(f"เกิดข้อผิดพลาด: {str(exc)}", status_code=500)

# === STARTUP ===

@app.on_event("startup")
async def startup():
    """Run on application startup."""
    db.init_db()
    # Create upload directory
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
