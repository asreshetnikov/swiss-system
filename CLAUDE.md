# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run dev server (SQLite, no Docker needed)
DATABASE_URL="" python3 manage.py migrate
DATABASE_URL="" python3 manage.py runserver

# Lint
ruff check .

# Run all tests
pytest pairing/tests/ -v

# Run a single test
pytest pairing/tests/test_engine.py::TestClassName::test_name -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev     # dev server on :3000
npm run build   # production build
npm run lint    # ESLint
```

### Docker (full stack)
```bash
cp backend/.env.example backend/.env   # first time only
docker-compose up --build              # starts db:5432, backend:8000, frontend:3000
```

## Architecture

### Backend (Django 5 + DRF)

**Apps and responsibilities:**
- `accounts` — Custom User (email as `USERNAME_FIELD`), JWT auth endpoints, `CookieJWTAuthentication` reads `access_token` from httpOnly cookie
- `tournaments` — Tournament model with nanoid slug, status machine (DRAFT→OPEN→RUNNING→FINISHED→ARCHIVED)
- `participants` — Participant model; seeds assigned on DRAFT→RUNNING by rating DESC then insertion order
- `rounds` — Round + Pairing models; result entry and round lifecycle (DRAFT→PUBLISHED→CLOSED)
- `standings` — `StandingSnapshot` stores JSON snapshots on round close; current standings recalculated live
- `pairing` — Pure pairing logic in `engine.py`, **no ORM**, fully unit-tested
- `audit` — Append-only `AuditLog`

**Pairing engine** (`pairing/engine.py`): Takes `list[PlayerState]` → returns `list[Pair]`. Round 1: top-half vs bottom-half by seed, colors alternate per board, first board color is random. Round 2+: group by score (desc), within group sort by `(-|CD|, seed)`, two-pass pairing (complementary color + no repeat → any non-repeat), color-aware floater selection for odd groups. Bye goes to the lowest-ranked player by standings (points ASC, seed DESC) without a prior bye. FIDE Dutch System (C.04).

**Standings calculator** (`standings/calculator.py`): Recalculates from raw pairing results. Tiebreak order is configurable via `tournament.tiebreak_order` (JSON list of strings: `"points"`, `"buchholz"`, `"wins"`, `"head_to_head"`, `"seed"`).

**Config:** `backend/config/` holds `settings.py` and root `urls.py`. Environment loaded from `.env` (copy from `backend/.env.example`). `DATABASE_URL=""` falls back to SQLite for local dev without Docker.

### Frontend (Next.js 14 App Router)

**Route structure:**
- `/` — landing
- `/login`, `/register` — auth
- `/dashboard` — owner's tournament list (auth-gated)
- `/tournaments/[slug]` — public view (Info / Rounds / Standings / Crosstable tabs)
- `/tournaments/[slug]/admin` — owner panel (Overview / Participants / Pairings / Standings tabs)

**Key files:**
- `lib/api.ts` — typed API client; all backend calls go through here
- `lib/types.ts` — shared TypeScript interfaces (Tournament, Participant, Round, Pairing, StandingRow, …)
- `lib/auth-context.tsx` — `AuthProvider` wrapping the app; exposes `user`, `login()`, `logout()`

### API URL patterns
```
/api/auth/{register|login|logout|refresh|me}/
/api/tournaments/                                  # list/create
/api/tournaments/{slug}/                           # detail
/api/tournaments/{slug}/status/                    # POST transition
/api/tournaments/{slug}/participants/
/api/tournaments/{slug}/participants/{id}/withdraw/
/api/tournaments/{slug}/rounds/
/api/tournaments/{slug}/rounds/generate/
/api/tournaments/{slug}/rounds/{n}/publish|close/
/api/tournaments/{slug}/rounds/{n}/pairings/
/api/tournaments/{slug}/rounds/{n}/pairings/{id}/
/api/tournaments/{slug}/standings/
/api/tournaments/{slug}/standings/{round}/
```

### Key design decisions
- Pairing and standings logic are pure functions — keep them ORM-free so they stay unit-testable
- Standings snapshots are written on round close; the `/standings/` endpoint recalculates live from closed rounds
- JWT lives in httpOnly cookies (SameSite=Lax); `CookieJWTAuthentication` handles extraction
- Public GET endpoints require no auth; write operations require owner auth
