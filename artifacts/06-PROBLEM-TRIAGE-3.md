# Problem Triage — WINBOT Booking v3 Improvements

## Issue Analysis

| # | Issue | Type | Impact | Effort | Priority |
|---|-------|------|--------|--------|----------|
| 1 | **Condo location picker via Google Maps** — customer specifies condo name + Google Maps link, stored in DB, visible only in admin | Feature | High — core business need to know delivery location | High (~1-2h) | **P0** |
| 2 | **Admin slip image bug** — slip images not showing/accessible | Bug | Critical — admin can't verify payments | Medium (~15-30min) | **P0** |
| 3 | **Remove admin phone from website footer** | Content | Low — minor cleanup | Trivial (~2min) | P2 |
| 4 | **Terms & conditions on confirmation page** | Content/UX | Medium — legal protection | Low (~15min) | P1 |

## Build Order
1. **P0 — Slip image bug** (#2): Investigate why images aren't showing, fix ASAP
2. **P0 — Condo location** (#1): DB schema → models → API → frontend → admin display
3. **P1 — T&C section** (#4): Add collapsible terms on confirmation page
4. **P2 — Remove phone** (#3): Footer cleanup
