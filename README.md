# SSIP GovTech Platform

A citizen-facing multilingual OCR and RAG assistant for Indian government form applications. Citizens upload notices, certificates, or draft applications in the language they are most comfortable with; the platform runs OCR to extract text across Indian scripts, then uses retrieval-augmented generation over a vector index of official forms and procedures to explain what a form is asking for, which fields apply to the citizen, and how to complete and submit the application correctly.

## Tech Stack

- **Frontend:** Next.js (App Router), TypeScript (strict), Tailwind CSS, shadcn/ui
- **Backend:** FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2.0 async
- **Database & Auth:** Supabase (PostgreSQL)
- **Vector search:** pgvector, for retrieval over form and procedure content
- **Migrations:** Alembic

## Folder Structure

```
.
├── backend/     FastAPI service: async routes, Pydantic schemas, services, settings
├── frontend/    Next.js App Router app: UI, typed API client, Supabase client
└── .pre-commit-config.yaml   Secret scanning and repo hygiene hooks
```

- `frontend/` — the Next.js App Router application. Server Components by default, with `"use client"` only where interactivity is required. UI primitives live in `frontend/components/ui/` (shadcn/ui); `frontend/lib/` holds the typed API client and `supabaseClient.ts`.
- `backend/` — the FastAPI application. Route handlers and services are async. `backend/app/main.py` wires up the app and its middleware; `backend/app/config.py` loads settings from the environment. Database schema changes are applied through Alembic migrations.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then fill in real values
uvicorn app.main:app --reload --port 8000
```

The service exposes `GET /health`. CORS is configured for `http://localhost:3000`.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # then fill in real values
npm run dev
```

The app is served at `http://localhost:3000` and talks to the backend at the URL configured in `.env.local`.

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

Once installed, `gitleaks`, private-key detection, and the large-file check run automatically before each commit.

## Environment variables

Secrets are never committed. Copy the example files and supply values locally:

- Backend: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`
- Frontend: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL`

See `backend/.env.example` and `frontend/.env.local.example` for the full list of placeholders.
