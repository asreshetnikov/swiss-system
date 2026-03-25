# SwissChess

Swiss-system chess tournament management platform.

## Stack

- **Backend**: Django 5 + DRF + PostgreSQL
- **Frontend**: Next.js (App Router) + Tailwind CSS
- **Auth**: JWT in httpOnly cookies (djangorestframework-simplejwt)

## Quick Start

```bash
cp backend/.env.example backend/.env
docker-compose up --build
```

- Backend API: http://localhost:8000/api/
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Tests

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
swisschess/
├── backend/
│   ├── config/          # Django settings, urls, wsgi
│   ├── accounts/        # User model, JWT auth endpoints
│   ├── tournaments/     # Tournament model, CRUD API
│   ├── participants/    # Participant model, CRUD API
│   ├── rounds/          # Round + Pairing/Match models, API
│   ├── standings/       # StandingSnapshot model, calculation
│   ├── pairing/         # Pairing engine (pure logic, testable)
│   └── audit/           # AuditLog model, append-only
└── frontend/
    ├── app/
    │   ├── (auth)/      # login, register pages
    │   ├── dashboard/   # my tournaments list
    │   └── tournaments/ # public + admin pages
    ├── components/
    └── lib/             # API client, types
```
