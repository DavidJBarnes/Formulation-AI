# Formulation-AI

Closed-loop AI formulation optimization for chemistry R&D — Bayesian optimization with an LLM reasoning layer. Standalone product that pulls Revvity (Signals One) data via API.

## Stack

- **Frontend:** React 19 + Vite + TypeScript + Tailwind + Radix (shadcn-style)
- **Backend:** FastAPI + SQLAlchemy + Postgres, managed with `uv`
- **Migrations:** Alembic
- **Auth:** JWT + Postgres users (passlib/bcrypt)
- **Infra:** Docker + docker-compose; EC2 deploy via GitHub Actions

## Layout

```
.
├── frontend/   # Vite + React app
├── backend/    # FastAPI app
└── docker-compose.yml
```

## Local development

```bash
docker compose up -d postgres
(cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn formulation_ai.app:app --reload)
(cd frontend && npm install && npm run dev)
```
