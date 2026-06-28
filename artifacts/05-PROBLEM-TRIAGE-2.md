# Problem Triage — WINBOT Booking Improvements

## Issue Analysis

| # | Issue | Type | Impact | Effort | Priority |
|---|-------|------|--------|--------|----------|
| 1 | LINE OpenChat link is placeholder | Content | Low - cosmetic | Trivial (~1 min) | P2 |
| 2 | Telegram notification missing slip image | Feature | High - admin can't verify slips from phone | Medium (~30 min) | **P1** |
| 3 | Payment channel info is placeholder | Content | High - customers can't pay | Low (~5 min) | **P1** |
| 4 | **Slot flexibility** — any 3h window 09:00-18:00 | Business logic | Critical - core booking model change | High (~1h) | **P0** |
| 5 | Download/save booking calendar to device | Feature | Medium - nice UX improvement | Medium (~30 min) | P2 |

## Priority Order (Build Sequence)

1. **P0 — Slot flexibility** (#4): Rewrites the core slot model from 3 fixed slots to any 3h window 09:00-18:00
2. **P1 — Payment info** (#3): Update confirmation page with real bank details
3. **P1 — Telegram slip image** (#2): Send photo alongside text notification
4. **P1 — LINE link** (#1): Replace placeholder URL
5. **P2 — Download calendar** (#5): Add .ics download on confirmation page
