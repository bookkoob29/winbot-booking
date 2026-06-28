# Architecture Decision Record — WINBOT Booking Website

## Stack Decision

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend Framework | FastAPI | Already installed (0.128.0), async, auto-docs |
| ASGI Server | Uvicorn | Already installed (0.40.0) |
| Database | SQLite (raw sqlite3) | Zero setup, single file, perfect for single-unit MVP |
| Templates | Jinja2 | Already installed (3.1.6), FastAPI-native |
| Frontend CSS | Tailwind CSS (CDN) | No build step, mobile-first, fast iteration |
| Frontend JS | Vanilla JS + HTMX (optional) | Minimal dependencies, easy to maintain |
| File Storage | Local `uploads/slips/` | Simpler than cloud storage for MVP |
| Telegram | HTTP API via httpx | Already installed (0.28.1), async |
| Auth | Session cookie + admin passcode | Simple, no OAuth dependency |

## File Structure

```
winbot-booking-app/
├── app.py                  # FastAPI application entry point
├── database.py             # SQLite schema + CRUD operations
├── telegram.py             # Telegram notification service
├── config.py               # Configuration from env vars
├── models.py               # Pydantic models
├── requirements.txt        # Dependencies
├── run.sh                  # Launch script
├── bookings.db             # SQLite database (auto-created)
├── uploads/
│   └── slips/              # Uploaded slip images
├── templates/
│   ├── base.html           # Base layout template
│   ├── index.html          # Landing page
│   ├── availability.html   # Calendar view
│   ├── booking_form.html   # Booking form (modal)
│   ├── confirmation.html   # Booking confirmation page
│   ├── admin/
│   │   ├── login.html      # Admin login page
│   │   ├── dashboard.html  # Admin dashboard
│   │   └── booking_detail.html # Booking detail + slip preview
│   └── error.html          # Error page
├── static/
│   └── style.css           # Custom CSS overrides
└── artifacts/
    ├── 01-PROBLEM-TRIAGE.md
    ├── 02-SUCCESS-CRITERIA.md
    └── 03-VERIFICATION-POLICY.md
```

## API Route Map

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/` | Public | Landing page |
| GET | `/availability` | Public | Calendar view page |
| GET | `/api/availability` | Public | JSON availability data |
| POST | `/api/bookings` | Public | Create booking |
| GET | `/booking/{id}` | Public | Booking confirmation page |
| POST | `/api/bookings/{id}/slip` | Public | Upload slip |
| GET | `/admin/login` | - | Admin login page |
| POST | `/admin/login` | - | Admin login action |
| GET | `/admin/dashboard` | Admin | Admin dashboard |
| GET | `/admin/bookings` | Admin | Admin booking list (API) |
| GET | `/admin/bookings/{id}` | Admin | Booking detail |
| PATCH | `/admin/bookings/{id}/status` | Admin | Change booking status |
| PATCH | `/admin/bookings/{id}` | Admin | Edit booking data |
| GET | `/admin/export/csv` | Admin | Export as CSV |
| GET | `/admin/activity-logs` | Admin | View activity logs |
| POST | `/admin/telegram/resend/{log_id}` | Admin | Resend notification |

## Status Flow

```
S4: AVAILABLE
  └─ [Customer books] → S3: RESERVED_UNPAID
       ├─ [30 min expiry] → S4: AVAILABLE
       ├─ [Customer uploads slip] → S2: PAID_PENDING_CONFIRM
       └─ [Admin cancels] → S4: AVAILABLE
S2: PAID_PENDING_CONFIRM
       ├─ [Admin confirms] → S1: CONFIRMED_PAID
       ├─ [Admin rejects] → S3: RESERVED_UNPAID
       └─ [Admin cancels] → S4: AVAILABLE
S1: CONFIRMED_PAID
       └─ [Admin cancels] → S4: AVAILABLE
```

## Data Flow

```
Customer → Browser → FastAPI → SQLite → Telegram Bot → @BookKoob29
                ↓                   ↓
           Slip Upload        Activity Log
           (local FS)          (SQLite)
```
