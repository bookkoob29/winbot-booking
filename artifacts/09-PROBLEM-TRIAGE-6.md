# Problem Triage — Production Deployment

## Issue
Both environments depend on the local machine. When computer is off → websites are dead.

## Solution: Deploy to Render Cloud
- FastAPI app → Render Web Service (24/7)
- Database → Render PostgreSQL (free tier)
- No local machine needed
- Custom domain support

## Acceptance Criteria
1. Production website accessible from any device at any time
2. Admin dashboard works remotely
3. Booking + slip upload work remotely
4. Telegram notifications work remotely
5. Zero dependency on local Mac
