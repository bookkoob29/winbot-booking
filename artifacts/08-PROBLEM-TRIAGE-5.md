# Problem Triage — WINBOT Condo Search v6

## Issue: Local DB (110 entries) misses condos like Skyrise Avenue 64

## Solution: Hybrid search
1. **Local DB** (instant, 110 entries) — primary results
2. **Nominatim (OpenStreetMap)** — real-time backup search, no API key needed, free
3. Backend proxy to respect rate limits + combine results
