# Success Criteria — WINBOT Mini 2 Booking Website

## Per-Component Pass Conditions

Each criterion below must be verifiable by a single command or action.

### SC1: Database Schema
- [ ] `sqlite3 bookings.db ".schema"` shows `bookings` table with all fields from §11.1
- [ ] `sqlite3 bookings.db ".schema"` shows `activity_logs` table with all fields from §11.2
- [ ] UNIQUE constraint exists on `(booking_date, slot_start, slot_end)`
- [ ] Booking status is stored as TEXT with values: `CONFIRMED_PAID`, `PAID_PENDING_CONFIRM`, `RESERVED_UNPAID`, `AVAILABLE`

### SC2: Slot Generation Logic
- [ ] Querying availability for any date returns 3 slots: 09:00-12:00, 12:00-15:00, 15:00-18:00
- [ ] Slots with no booking return status `AVAILABLE`
- [ ] Slots with active booking return status of the booking (not `AVAILABLE`)

### SC3: Booking Creation
- [ ] `POST /api/bookings` with valid data returns 201 + booking ID
- [ ] `POST /api/bookings` for already-booked slot returns 409 Conflict
- [ ] `POST /api/bookings` with missing required fields returns 422
- [ ] Booking code is generated in format `BK-YYYYMMDD-NNN`
- [ ] Activity log entry created for new booking

### SC4: Slip Upload
- [ ] `POST /api/bookings/{id}/slip` with valid image returns 200
- [ ] Status changes from `RESERVED_UNPAID` to `PAID_PENDING_CONFIRM` on slip upload
- [ ] File > 5MB returns 413
- [ ] Non-image file (.exe, .txt) returns 400
- [ ] Activity log entry created for slip upload

### SC5: Admin Confirm/Reject
- [ ] Admin confirms slip → status changes to `CONFIRMED_PAID`
- [ ] Admin rejects slip → status returns to `RESERVED_UNPAID`
- [ ] Admin cancels booking → slot returns to available
- [ ] Activity log entry created for each action
- [ ] Telegram notification sent for each action (telegram_sent=true)

### SC6: Availability API
- [ ] `GET /api/availability?start_date=X&end_date=Y` returns valid JSON
- [ ] Each slot has: `start`, `end`, `status`, `color`, `bookable` fields
- [ ] `bookable` is `false` for non-`AVAILABLE` slots
- [ ] Colors match the PRD color scheme

### SC7: Telegram Notifications
- [ ] New booking → Telegram message delivered
- [ ] Slip uploaded → Telegram message delivered
- [ ] Admin confirmed → Telegram message delivered
- [ ] Admin rejected → Telegram message delivered
- [ ] Admin cancelled → Telegram message delivered
- [ ] Failed notification → `telegram_sent=false` in DB (system still works)

### SC8: Public Frontend
- [ ] Landing page loads with hero, price, benefits, CTA buttons
- [ ] Calendar shows 3 slot rows per day with correct colors
- [ ] Clicking 'จอง' on available slot shows booking form
- [ ] Booking form validates required fields
- [ ] Confirmation page shows booking code, date, slot, status
- [ ] Slip upload works from confirmation page
- [ ] No customer PII (name, phone, Line ID) visible to other users

### SC9: Admin Dashboard
- [ ] Admin login page at `/admin/login` requires auth
- [ ] Dashboard shows today's bookings
- [ ] Booking list is filterable by date, status, phone
- [ ] Admin can confirm slip with one click
- [ ] Admin can reject/cancel bookings
- [ ] Admin can edit customer name, phone, Line ID
- [ ] Admin can export bookings as CSV
- [ ] Session expires after 30 min inactivity

### SC10: Unpaid Booking Expiry
- [ ] Booking with status `RESERVED_UNPAID` older than 30 min auto-expires
- [ ] Auto-expired booking sets slot back to `AVAILABLE`
- [ ] Activity log entry created for auto-expire

## Acceptance Checklist (From PRD §18)

- [ ] **AC1**: Customer can view available slots with colors
- [ ] **AC2**: Customer can book available slot → status = Reserved Unpaid
- [ ] **AC3**: Customer can upload slip → status = Paid Pending Confirm
- [ ] **AC4**: Admin can confirm slip → status = Confirmed Paid
- [ ] **AC5**: Telegram notified on every activity
- [ ] **AC6**: Double booking prevented
- [ ] **AC7**: Public user cannot see others' PII
