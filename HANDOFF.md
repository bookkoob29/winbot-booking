# WINBOT Mini 2 Booking System — Handoff Document

**Version:** Stable (`a0b9ad4`)
**Date:** June 28, 2026
**Author:** Sorlakom (Book)
**GitHub:** https://github.com/bookkoob29/winbot-booking
**Production:** https://winbot-booking.onrender.com

---

## 1. System Overview

Public booking website for WINBOT Mini 2 window-cleaning robot rental. Customers view available time slots, book 3-hour rental windows, upload payment slips, and receive Telegram notifications. Admin dashboard manages bookings, confirms payments, and tracks activity logs.

**Stack:** FastAPI (Python 3.11/3.14) + Jinja2 + Tailwind CSS CDN + SQLite (dev) / PostgreSQL (prod)
**Hosting:** Render Cloud (24/7), Local DEV via ngrok, Local PROD via cloudflared

---

## 2. Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Browser    │────▶│  FastAPI app  │────▶│  Database   │
│  (Tailwind) │     │  (uvicorn)    │     │  (SQLite/PG)│
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Telegram    │
                    │  Bot API     │
                    └──────────────┘
```

### 2.1 Environments

| Env | Port | URL | DB | Tunnel |
|-----|------|-----|----|--------|
| **DEV** | 8080 | `http://localhost:8080` | SQLite (bookings.db) | ngrok |
| **PROD (local)** | 8081 | `http://localhost:8081` | SQLite | cloudflared |
| **PROD (Render)** | — | `https://winbot-booking.onrender.com` | PostgreSQL | Render |

### 2.2 Key Directories

```
~/winbot-booking-app/
├── app.py              # Main FastAPI application
├── config.py           # Configuration constants
├── database.py         # Database CRUD + schema
├── models.py           # Pydantic request validators
├── telegram.py         # Telegram notification helpers
├── start.sh            # Render startup script
├── Procfile            # Render process definition
├── render.yaml         # Render Blueprint config
├── requirements.txt    # Python dependencies
├── DEPLOYMENT.md       # Deployment guide
├── static/
│   └── condos-bangkok.json  # 110 condo entries
├── templates/
│   ├── base.html            # Base layout + i18n + toast
│   ├── index.html           # Landing page
│   ├── availability.html    # Calendar + booking modal
│   ├── confirmation.html    # Booking confirmation + T&C
│   ├── error.html           # Error page
│   └── admin/
│       ├── login.html       # Admin login
│       ├── dashboard.html   # Admin dashboard
│       ├── booking_detail.html  # Booking detail + actions
│       └── activity_logs.html   # Activity log viewer
├── scripts/
│   ├── dev.sh           # Start DEV + ngrok
│   ├── setup-prod.sh    # Install cloudflared + launchd
│   ├── start-prod.sh    # Start PROD via launchd
│   └── urls.sh          # Show tunnel URLs
└── artifacts/           # Problem triage docs
```

---

## 3. API Routes

### 3.1 Public Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Landing page |
| GET | `/availability` | Calendar + booking page |
| GET | `/api/availability?start_date=&end_date=` | JSON slot availability |
| GET | `/booking/{id}` | Booking confirmation page |
| GET | `/booking/{id}/ics` | Download ICS calendar file |
| POST | `/api/bookings` | Create booking |
| POST | `/api/bookings/{id}/slip` | Upload payment slip |
| GET | `/api/search-condo?q=` | Search condos (local DB + Nominatim) |
| GET | `/api/health` | Health check |

### 3.2 Admin Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/login` | Login form |
| POST | `/admin/login` | Login (passcode) |
| GET | `/admin/logout` | Logout |
| GET | `/admin/dashboard` | Booking list |
| GET | `/admin/bookings/{id}` | Booking detail |
| PATCH | `/admin/api/bookings/{id}/status` | Change status |
| PATCH | `/admin/api/bookings/{id}` | Edit customer info |
| GET | `/admin/api/bookings` | JSON booking list |
| GET | `/admin/activity-logs` | Activity log viewer |
| GET | `/admin/export/csv` | Export bookings CSV |
| POST | `/admin/api/telegram/resend/{log_id}` | Resend notification |
| POST | `/admin/api/reset-database` | Clear all data |

### 3.3 Maintenance Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/maintenance/expire` | Expire unpaid bookings |

---

## 4. Database Schema

### 4.1 `bookings`

| Column | Type (PG) | Type (SQLite) | Description |
|--------|-----------|---------------|-------------|
| id | TEXT PK | TEXT PK | UUID |
| booking_code | TEXT UNIQUE | TEXT UNIQUE | Auto-generated (BK-YYYYMMDD-NNN) |
| booking_date | DATE | TEXT | YYYY-MM-DD |
| slot_start | TIME | TEXT | HH:MM |
| slot_end | TIME | TEXT | HH:MM |
| customer_name | TEXT | TEXT | |
| phone | TEXT | TEXT | Thai mobile |
| line_id | TEXT | TEXT | Optional |
| condo_name | TEXT | TEXT | Condo/project name |
| condo_map_link | TEXT | TEXT | Google Maps URL |
| note | TEXT | TEXT | Customer note |
| internal_note | TEXT | TEXT | Admin note |
| status | TEXT | TEXT | See Status Flow |
| confirmed_by | TEXT | TEXT | Admin name |
| confirmed_at | TIMESTAMPTZ | TEXT | ISO datetime |
| created_at | TIMESTAMPTZ | TEXT | Auto |
| updated_at | TIMESTAMPTZ | TEXT | Auto |
| cancelled_at | TIMESTAMPTZ | TEXT | Auto |

**Unique constraint:** `(booking_date, slot_start, slot_end)` — prevents overlapping bookings.

### 4.2 `activity_logs`

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| booking_id | TEXT FK | References bookings |
| booking_code | TEXT | Denormalized for display |
| activity_type | TEXT | e.g. BOOKING_CREATED, SLIP_UPLOADED, STATUS_CHANGED |
| old_status | TEXT | Previous status |
| new_status | TEXT | New status |
| actor_type | TEXT | Customer / Admin / System |
| actor_name | TEXT | Who performed action |
| message | TEXT | Description |
| telegram_sent | BOOLEAN/INT | FALSE/0 or TRUE/1 |
| telegram_sent_at | TIMESTAMPTZ/TEXT | When sent |
| created_at | TIMESTAMPTZ/TEXT | Auto |

### 4.3 `slip_files`

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| booking_id | TEXT FK | References bookings |
| filename | TEXT | Server filename |
| original_name | TEXT | Original filename |
| filepath | TEXT | Full path on disk |
| filesize | INTEGER | File size in bytes |
| created_at | TIMESTAMPTZ/TEXT | Auto |

---

## 5. Booking Status Flow

```
AVAILABLE
    │
    ▼ (Customer books)
RESERVED_UNPAID ──────────────────▶ AVAILABLE (Admin cancels / auto-expire 48h)
    │
    ▼ (Customer uploads slip)
PAID_PENDING_CONFIRM
    │
    ▼ (Admin confirms payment)
CONFIRMED_PAID ──────────────────▶ AVAILABLE (Admin cancels)
```

### 5.1 Allowed Transitions

| From | To |
|------|----|
| RESERVED_UNPAID | PAID_PENDING_CONFIRM, AVAILABLE |
| PAID_PENDING_CONFIRM | CONFIRMED_PAID, RESERVED_UNPAID, AVAILABLE |
| CONFIRMED_PAID | AVAILABLE |

### 5.2 Status Colors

| Status | Background | Text |
|--------|-----------|------|
| AVAILABLE | `#DBEAFE` (light blue) | `#1E40AF` |
| RESERVED_UNPAID | `#64748B` (slate gray) | `#FFFFFF` |
| PAID_PENDING_CONFIRM | `#F59E0B` (amber) | `#FFFFFF` |
| CONFIRMED_PAID | `#16A34A` (green) | `#FFFFFF` |

---

## 6. Booking Rules

### 6.1 Operating Hours

- 09:00 – 18:00 daily
- 3-hour slots: 09:00–12:00, 10:00–13:00, ..., 15:00–18:00 (7 slots)

### 6.2 24-Hour Advance Booking

All bookings must be made at least 24 hours in advance of the slot start time. If 24 hours from now falls after 18:00, the next day earliest slot becomes available.

### 6.3 Unpaid Expiry

Bookings expire after 48 hours (configurable via `UNPAID_EXPIRY_MINUTES` env var) if no slip is uploaded.

### 6.4 Overlap Prevention

Database-level UNIQUE constraint on `(booking_date, slot_start, slot_end)` prevents double-booking. The API validates slot availability before creation.

---

## 7. Condo Search

Two data sources:

### 7.1 Local DB (110 condos)

File: `static/condos-bangkok.json`

Entries have verified names (TH + EN), district, developer, coordinates, and Google Maps search URLs.

### 7.2 Nominatim (OSM) Fallback

When a query doesn't match local DB, falls back to OpenStreetMap's Nominatim API (free, no key needed). Results use Google Maps search-by-name URLs (not OSM coordinates).

---

## 8. Telegram Notifications

Bot token stored in `~/.telegram_token` or `TELEGRAM_BOT_TOKEN` env var. Chat ID: `8969930460`.

Triggered on:
- New booking created
- Slip uploaded (with photo of slip)
- Admin confirms booking
- Status changed
- Booking cancelled
- System errors

---

## 9. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | (from file) | Telegram bot token |
| `TELEGRAM_CHAT_ID` | `8969930460` | Admin Telegram chat ID |
| `ADMIN_PASSCODE` | `BooK2905@1990` | Admin login passcode |
| `SESSION_SECRET` | `winbot-booking-secret-key-...` | Session encryption key |
| `DATABASE_URL` | (none) | PostgreSQL URL (prod only) |
| `UNPAID_EXPIRY_MINUTES` | `2880` | Auto-cancel after (48h) |
| `PORT` | `8080` | Server port |
| `HOST` | `0.0.0.0` | Server host |

---

## 10. Deployment

### 10.1 DEV (local + ngrok)

```bash
cd ~/winbot-booking-app
bash scripts/dev.sh
# → http://localhost:8080 + https://{ngrok}.ngrok-free.dev
```

### 10.2 PROD (local + cloudflared)

```bash
bash scripts/setup-prod.sh     # One-time setup
# → http://localhost:8081 + https://{tunnel}.trycloudflare.com
```

### 10.3 PROD (Render Cloud)

1. Push to `https://github.com/bookkoob29/winbot-booking`
2. Go to `https://dashboard.render.com`
3. Manual Deploy → Deploy latest commit
4. Set env vars: `TELEGRAM_BOT_TOKEN`, `ADMIN_PASSCODE`, `SESSION_SECRET`
5. Render auto-adds PostgreSQL DATABASE_URL

### 10.4 Key Deployment Files

| File | Purpose |
|------|---------|
| `start.sh` | Uvicorn startup (used by Render) |
| `Procfile` | Web process definition |
| `render.yaml` | Blueprint auto-config |
| `scripts/dev.sh` | DEV + ngrok |
| `scripts/setup-prod.sh` | cloudflared + launchd |
| `scripts/start-prod.sh` | PROD uvicorn |

---

## 11. Admin Guide

**URL:** `/admin/login`
**Passcode:** `BooK2905@1990`

### Features

| Feature | How |
|---------|-----|
| View bookings | Dashboard shows all, filterable by date/status |
| View slip | Click booking → see uploaded slip images |
| Confirm payment | Status change → CONFIRMED_PAID |
| Cancel booking | Status change → AVAILABLE |
| Edit customer | Name, phone, internal note |
| Activity logs | Full audit trail with Telegram status |
| Resend Telegram | Failed notifications can be retried |
| Export CSV | Download bookings as spreadsheet |
| Reset database | Admin API: POST `/admin/api/reset-database` |

---

## 12. Slip Upload Rules

- Formats: `.jpg`, `.jpeg`, `.png` only
- Max size: 2 MB
- Max files per booking: 3
- Stored in: `~/winbot-booking-app/uploads/slips/`
- Status changes to `PAID_PENDING_CONFIRM` on successful upload

---

## 13. Google Maps Integration

All condo locations use Google Maps search-by-name URLs:
```
https://www.google.com/maps/search/{condo_name}+Bangkok/
```

This applies to:
- All 110 local DB entries
- All Nominatim search results
- Frontend fallback when user types manual name

---

## 14. Mobile Responsiveness

- Tailwind responsive classes (`max-w-lg`, `grid-cols-3`, etc.)
- Nav buttons use `whitespace-nowrap` to prevent text wrapping
- Gap spacing for touch targets
- Modal content limited to `max-height: 90vh` with overflow scroll
- Toast notifications bottom-right on mobile

---

## 15. Known Behaviors & Edge Cases

| Scenario | Behavior |
|----------|----------|
| Past dates are never bookable | `bookable: false`, label "ปิด" |
| Today is bookable (if ≥24h from now) | Uses 24-hour rule |
| 30-day lookback limit | API won't return data older than 30 days |
| Database auto-creates | `init_db()` on first import |
| SQLite ↔ PostgreSQL | Auto-detected by `DATABASE_URL` env var |
| Slip file cleanup | Files remain on disk, only DB records deleted on reset |
| Main nav has no mobile hamburger | Responsive by stacking vertically |
| Error 500 on templates | Returns fallback plain-text error |

---

## 16. Troubleshooting

### Calendar shows "โหลดข้อมูลไม่สำเร็จ"
- Check API health: `GET /api/health`
- Check CORS/network
- Verify `zoneinfo` is available (Python 3.9+)

### Slip upload fails
- Check file type/size
- Check `uploads/slips/` directory permissions
- Verify booking status allows upload

### Admin login not working
- Clear session cookies
- Verify `ADMIN_PASSCODE` env var
- Check session secret

### Booking shows 409 Conflict
- Slot is already booked (unique constraint)
- Refresh calendar to see updated availability

### PostgreSQL errors
- Verify `DATABASE_URL` is set correctly
- PostgreSQL uses BOOLEAN type for `telegram_sent` (not INTEGER like SQLite)

---

## 17. Quick Reference

**Admin Passcode:** `BooK2905@1990`
**Telegram Chat ID:** `8969930460`
**Price:** 500 THB / 3 hours
**Deposit:** 2,000 THB (pay on pickup, refund on return)
**Auto-cancel:** 48 hours unpaid
**Advance booking:** Minimum 24 hours

### Key URLs

| URL | Purpose |
|-----|---------|
| `https://winbot-booking.onrender.com` | Production |
| `https://winbot-booking.onrender.com/admin/login` | Admin |
| `https://github.com/bookkoob29/winbot-booking` | GitHub |
| `https://dashboard.render.com` | Render dashboard |
