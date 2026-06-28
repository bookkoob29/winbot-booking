# WINBOT Booking — Deployment Guide

## Architecture

```text
DEV (Testing)
├── Localhost:8080
├── SQLite (bookings.db)
├── Local file storage
├── ngrok tunnel (public URL)
└── Telegram dev bot

PROD (Production 24/7)
├── Render Web Service
├── PostgreSQL (Render free tier)
├── Render Persistent Disk or S3
├── Custom domain (booking.bookkoob.com)
└── Telegram real bot
```

## Quick Start

### Dev — ทดสอบ
```bash
bash scripts/dev.sh
# → http://localhost:8080
# → https://xxxx.ngrok-free.dev (public URL)
```

### Prod — Deploy ขึ้น Render

**Step 1: Push to GitHub**
```bash
cd ~/winbot-booking-app
git init
git add .
git commit -m "Initial commit"
gh repo create winbot-booking --public --push
# หรือสร้าง repo ที่ github.com แล้ว push
```

**Step 2: Deploy on Render**
1. ไปที่ https://dashboard.render.com
2. New → Web Service → เลือก GitHub repo
3. ตั้งค่า:
   - **Name:** `winbot-booking`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app`
   - **Health Check Path:** `/api/health`
4. Add Environment Variables:
   - `ADMIN_PASSCODE` → `BooK2905@1990`
   - `TELEGRAM_BOT_TOKEN` → (your token)
   - `TELEGRAM_CHAT_ID` → `8969930460`
   - `SESSION_SECRET` → (random string)
5. Add a PostgreSQL database:
   - Render Dashboard → New → PostgreSQL
   - Render auto-injects `DATABASE_URL` into the web service
6. Deploy!

**Step 3: Custom Domain (Optional)**
- Render Dashboard → Settings → Custom Domain
- Add `booking.bookkoob.com`
- Configure DNS at your domain provider

## Environment Variables

| Variable | Dev | Prod | Required |
|----------|-----|------|----------|
| `DATABASE_URL` | (not set, uses SQLite) | Render auto-injects | For PG only |
| `TELEGRAM_BOT_TOKEN` | from ~/.telegram_token | Set in Render dashboard | ✅ |
| `TELEGRAM_CHAT_ID` | 8969930460 | 8969930460 | ✅ |
| `ADMIN_PASSCODE` | BooK2905@1990 | BooK2905@1990 | ✅ |
| `SESSION_SECRET` | hardcoded default | Set in Render dashboard | ✅ |

## Database

Dev uses **SQLite** (`bookings.db`). Prod uses **PostgreSQL** (auto-detected via `DATABASE_URL`).

All SQL is backend-agnostic — the `database.py` adapter handles placeholder conversion (`?` → `%s`).

## URLs

### Dev
- Landing: `http://localhost:8080`
- Public: `https://xxxx.ngrok-free.dev`
- Admin: `/admin/login`

### Production
- Landing: `https://winbot-booking.onrender.com`
- Custom: `https://booking.bookkoob.com` (หลังตั้ง domain)
- Admin: `/admin/login`
