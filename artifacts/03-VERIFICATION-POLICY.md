# Verification Policy — WINBOT Mini 2 Booking Website

## Pre-Commit Gates

Before any code change is considered "done", the following gates must pass:

| Gate | Command / Check | Runner |
|------|----------------|--------|
| Python syntax | `python3 -m py_compile app.py` (or main file) | Dev |
| DB schema | `sqlite3 bookings.db ".schema"` matches model | Dev |
| API smoke test | `curl localhost:8080/api/availability` returns 200 | Dev |
| Telegram config | `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set in env | Dev |
| Static files | All HTML templates load without 500 errors | Dev |

## Daily Health Checks

| Check | Frequency | Action on Failure |
|-------|-----------|-------------------|
| App running | Daily | `systemctl restart winbot-app` or `python3 app.py &` |
| DB file exists | Daily | Check `bookings.db` in project root |
| Disk space for slip uploads | Daily | Clean old slips > 90 days |
| Telegram bot responds | Daily | `curl -s https://api.telegram.org/bot$TOKEN/getMe` |

## Failure Taxonomy

| Severity | Definition | Response Time | Example |
|----------|-----------|---------------|---------|
| **Critical** | System down, no bookings possible | Immediate | Database corruption, app crash on startup |
| **High** | Core feature broken but system runs | 1 hour | Double booking allowed, Telegram silent, slip upload fails |
| **Medium** | Admin feature broken | 4 hours | CSV export fails, internal note not saving |
| **Low** | Cosmetic or non-blocking | 24 hours | Wrong color on calendar, layout break on small screen |

## Test Set Specification

### Unit Tests (Python pytest)
| Test | Description | Pass Condition |
|------|-------------|----------------|
| `test_slot_generation` | Generate slots for a given date | Returns 3 slots with correct times |
| `test_booking_code_format` | Generate booking code | Matches `BK-\d{8}-\d{3}` pattern |
| `test_status_transitions` | Valid status transitions | S3→S2→S1, S3→S4, S2→S3 |
| `test_invalid_transitions` | Invalid status transitions | Rejected with error |
| `test_double_booking` | Book same slot twice | Second returns error |
| `test_expired_booking` | Booking older than 30 min | Auto-cleared |

### API Tests (curl commands)
| Test | curl Command | Expected |
|------|-------------|----------|
| Get availability | `curl localhost:8080/api/availability?start_date=2026-07-01&end_date=2026-07-07` | JSON with 7 dates × 3 slots |
| Create booking | `curl -X POST -H "Content-Type: application/json" -d '{"booking_date":"2026-07-01","slot_start":"09:00","slot_end":"12:00","customer_name":"Test","phone":"0812345678"}' localhost:8080/api/bookings` | 201 + booking object |
| Double booking | Same curl again | 409 Conflict |
| Invalid phone | `... "phone":"abc" ...` | 422 Validation error |

### End-to-End Test (Manual)
1. Open public URL → Landing page loads
2. Click "ดูเวลาว่าง" → Calendar shows available slots
3. Click "จอง Slot นี้" on an available slot → Booking form appears
4. Fill name, phone → Submit → Confirmation page with booking code
5. Upload slip image → Status changes to yellow
6. Open admin dashboard → Login → See pending booking
7. Click Confirm → Status changes to green
8. Check Telegram → 3 messages received (new booking, slip upload, confirmed)

## Acceptance Test Matrices

### Status Transition Matrix

| From ↓ \ To → | AVAILABLE | RESERVED_UNPAID | PAID_PENDING_CONFIRM | CONFIRMED_PAID |
|--------------|-----------|-----------------|---------------------|----------------|
| AVAILABLE | - | Create booking ✓ | - | - |
| RESERVED_UNPAID | Admin cancel ✓ / Auto-expire ✓ | - | Slip upload ✓ | - |
| PAID_PENDING_CONFIRM | Admin cancel ✓ | Admin reject ✓ | - | Admin confirm ✓ |
| CONFIRMED_PAID | Admin cancel ✓ | - | - | - |

### Notification Trigger Matrix

| Activity | Telegram Sent | Activity Log Created |
|----------|--------------|---------------------|
| Booking created | ✓ | ✓ |
| Slip uploaded | ✓ | ✓ |
| Admin confirmed | ✓ | ✓ |
| Admin rejected | ✓ | ✓ |
| Admin cancelled | ✓ | ✓ |
| Booking expired | ✓ | ✓ |
| Customer edited | ✓ | ✓ |
| Upload failed | ✓ | ✓ |

## Verification Script

A single `python3 -m pytest` must pass all unit tests before deployment.
A single `curl` against the API must return health check 200.
