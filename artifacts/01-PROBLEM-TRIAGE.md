# Problem Triage — WINBOT Mini 2 Booking Website

## Risk × Impact Matrix

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | **Double booking race condition** — Two customers book the same slot simultaneously | Low | Critical | Database-level UNIQUE constraint on (booking_date, slot_start); atomic transaction for booking creation |
| R2 | **Slip upload fails** — File too large, wrong format, network issue | Medium | Medium | Client-side validation (size + type check before upload); server re-validation; Telegram alert on failure |
| R3 | **Telegram notification fails** — Bot token invalid, network error, chat_id wrong | Medium | High | Notification is async + fire-and-forget; `telegram_sent` flag on activity log; admin dashboard shows failed notifications; manual resend button |
| R4 | **Unpaid booking expiry not implemented** — Customer books and never pays, blocking the slot | High | High | Implement auto-expiry (30 min default) via periodic sweep or lazy check on availability query |
| R5 | **Admin session hijack** — Weak admin auth exposes customer data (phone, Line ID, slip images) | Low | Critical | Simple passcode or basic auth; HTTPS mandatory; session timeout after 30 min inactivity |
| R6 | **Customer guessing booking tokens** — Sequential booking IDs let customers modify others' bookings | Medium | High | Use UUID-based booking IDs; confirmation page uses booking UUID in URL, not sequential |
| R7 | **Spam bookings** — Bot submits fake bookings blocking real customers | Medium | Medium | Rate limit per IP (5 bookings/hour); rate limit per phone number (3/day); captcha optional |
| R8 | **Time zone confusion** — Server timezone vs customer expectation for slot times | Low | Medium | Asia/Bangkok timezone hardcoded; all times stored in UTC+7 explicitly |
| R9 | **Admin dashboard not mobile-friendly** — Admin needs to confirm slips on phone | Medium | Low | Admin dashboard responsive; slip preview works on mobile |
| R10 | **File storage fills up** — Slip images accumulate without cleanup | Low | Medium | Auto-delete slips after 90 days; or move to cold storage |

## Key Assumptions Requiring Validation

| # | Assumption | How to Validate | If Wrong |
|---|-----------|-----------------|----------|
| A1 | Customers will upload slips from their phone | Test with real users in soft launch | Send slip via LINE as fallback; admin uploads on behalf |
| A2 | 30 min expiry is enough for customers to pay | Monitor abandoned bookings in first week | Adjust to 60 min or disable expiry |
| A3 | Customers return to the confirmation page to upload slip later | Track revisit rate on confirmation URLs | Embed slip upload link in Telegram notification to customer (future) |
| A4 | Single machine (WINBOT mini 2) is enough for initial demand | Track booking collisions (same date, different slots) | Add multi-machine inventory in v2 |
| A5 | LINE OpenChat is the primary customer acquisition channel | Track source of traffic in analytics | Add Facebook/Google ads landing page |

## Gaps vs. Original System

| Feature | PRD Status | Why | Alternative |
|---------|-----------|-----|-------------|
| Online Payment Gateway | Out of scope | MVP uses manual slip verification | Slip upload + admin confirm |
| Customer Login | Out of scope | No auth complexity in MVP | Confirmation link with UUID token |
| Auto OCR on Slip | Out of scope | Too complex for MVP | Manual admin review |
| Multi-device inventory | Out of scope | Single machine initially | Extend schema later |
| SMS notifications | Out of scope | Telegram only | LINE messaging fallback |

## Dependency Chain

```
Database (SQLite) ← no deps, first
  └─ Availability API ← depends on DB
  └─ Booking API ← depends on DB
  └─ Slip Upload ← depends on Booking API
  └─ Telegram Notification ← depends on Booking API
  └─ Admin Dashboard ← depends on Booking API
     └─ Admin Auth ← no deps
```

**Build order:** DB Schema → Booking API → Slip Upload → Telegram → Admin Dashboard → Frontend
