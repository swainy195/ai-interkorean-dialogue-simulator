# Deployment

## Architecture

- Frontend: Vercel, `apps/web`
- Backend: Render, `apps/api`
- Database: existing Supabase project and PostgreSQL/pgvector schema

## Frontend environment

Set `VITE_API_BASE_URL` to the public Render API URL. No Supabase, OpenRouter, public-data API key, service-role key, or database password is exposed to the frontend bundle.

## Backend environment

Set the variables in `.env.example` in Render. `WEB_BASE_URL` must contain the Vercel origin, optionally comma-separated with a local development origin. FastAPI CORS does not use `*`.

## Commands

Render uses `pip install -r requirements.txt` and `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Vercel uses `npm run build` and publishes `dist`.

## Smoke checklist

After URLs are supplied by the deployment providers, verify `/health`, `/health/db`, `/health/openrouter`, frontend load, both simulation modes, Evidence display, and a terminal result. Provider credentials are entered only in the provider dashboards.

## Phase 9.1 status

Deployment manifests are ready and local production build/API smoke tests pass. Actual Vercel/Render deployment was not executed in this workspace because no Vercel/Render CLI authentication, Git remote, or public provider URL is available. No deployment URL is recorded or fabricated. Once provider access is connected, enter the variables above, deploy Render first, set `VITE_API_BASE_URL` in Vercel, update Render `WEB_BASE_URL` with the Vercel origin, and run the smoke checklist.
