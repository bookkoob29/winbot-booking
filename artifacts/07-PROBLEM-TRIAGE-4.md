# Problem Triage — WINBOT Booking v5

## Priority Matrix

| # | Task | Type | Impact | Effort | Priority |
|---|------|------|--------|--------|----------|
| 1 | **Upgrade condo DB** — adopt research report schema (thai_name, english_name, district, developer, year, alt names) + add 10+ new condos from report | Data/Feature | High — better search, matches real Bangkok condo data | High (~1h) | **P0** |
| 2 | **Change admin password** → `BooK2905@1990` | Config | High — security | Trivial (~1 min) | **P0** |
| 3 | **Production deployment** — external internet access | Infra | Critical — go live | Medium (~30m) | **P1** |

## Build Order
1. P0 — Admin password change
2. P0 — Condo DB schema upgrade + data expansion
3. P1 — Production deployment (ngrok tunnel or cloud deploy)
