# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Closed-loop AI formulation optimization for chemistry R&D — Bayesian-style optimization with an LLM (Claude) as the reasoning engine. Standalone product that ingests Revvity (Signals One) Notebook data via the REST API and runs a DOE inner loop (propose → sample → test → log → evaluate → iterate) under a portfolio-level outer loop (project-start reporting, project-end learnings capture).

Being co-designed with Jun Liu (Senior PMM, Revvity Signals Software). Jun is the domain expert; he is not engineering. Collaboration doubles as an audition for a Revvity role — calibrate output accordingly.

## Product shape (locked after Jun's 2026-04-24 answers)

Three layers:
- **Portfolio** — 5–10 concurrent projects per 20-person R&D team, each 6–18 months. Reporting bookend at project start, learnings bookend at project end. **In POC scope, not phase 2.**
- **Project (DOE inner loop 3→6)** — ingest base products + set targets → AI proposes K candidates → manual sampling → manual testing → log results → AI evaluator does one of three things: iterate, declare success, or **escalate a data-integrity flag when the actual-vs-proposed gap exceeds a noise threshold** (Jun's anomaly case).
- **Persistence** — across iterations and across projects; schema may change between projects.

Engineering split:
- **Phase 1 (POC):** LLM-only proposal generator (Claude Opus 4.7), no classical ML yet. Results logged as typed values (numerical with units default; categorical with pass/fail as subtype — *not* binary hit/miss). Portfolio surfaces visible from day one.
- **Phase 2:** swap in real Bayesian optimizer (GP/BO) under the LLM. AI-during-testing (SOPs, QC) is explicitly out of POC — Jun called that "worth billions by itself," likely a separate product track.

Keep the `optimizer/` module boundary clean so Phase 2 can slot in without refactoring the LLM path.

## Stack

- **Frontend:** React 19 + Vite 8 + TypeScript 6 + Tailwind 3.4 + Radix primitives (shadcn-style via `class-variance-authority` + `clsx` + `tailwind-merge`) + `react-router-dom` 7. Versions mirror `../eb/Unified-Document-Retrieval/frontend` — that's the layout reference.
- **Backend:** FastAPI + SQLAlchemy 2.x + Alembic + Postgres 17, managed with `uv`. Layout and patterns mirror `../SignalsStudioAI/api`.
- **Auth:** JWT + bcrypt + Postgres users, plumbed but with no product features yet.
- **Infra:** Docker + docker-compose (local); GH Actions build and push images to GHCR, then SSH to EC2 for `docker compose pull && alembic upgrade head && up -d`.

## Monorepo layout

```
.
├── frontend/                  Vite + React app
├── backend/                   FastAPI app (src layout under formulation_ai/)
│   ├── src/formulation_ai/    app.py, config.py, db.py, auth.py, models/, routers/, schemas/
│   └── alembic/               migrations
├── experiments/               Standalone prototypes (not features)
│   └── quad-model-proposal/   Audition artifact for Jun's #3 skepticism
├── docker-compose.yml         Postgres + backend + frontend
└── .github/workflows/         ci.yml + deploy.yml
```

## Commands

**Local dev loop:**
```bash
docker compose up -d postgres
(cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn formulation_ai.app:app --reload --port 8000)
(cd frontend && npm install && npm run dev)   # proxies /api → 127.0.0.1:8000
```

**Full stack via compose:**
```bash
docker compose up --build
# frontend → http://localhost:8080, backend → http://localhost:8000
```

**Backend:**
```bash
cd backend
uv run ruff check .
uv run pytest -q
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

**Frontend:**
```bash
cd frontend
npm run lint
npm run build
```

## Configuration

Backend config is `pydantic-settings` with prefix `FA_` — see `backend/src/formulation_ai/config.py`. Common env vars: `FA_DATABASE_URL`, `FA_JWT_SECRET`, `FA_CORS_ORIGINS`, `FA_ANTHROPIC_API_KEY` (falls back to SDK's `ANTHROPIC_API_KEY`).

Frontend dev server proxies `/api/*` to `http://127.0.0.1:8000`. In production, nginx in `frontend/Dockerfile` proxies `/api/` to `http://backend:8000`.

## External references — don't rebuild, reuse

- **`../SignalsStudioAI/scraper/`** — one-shot Playwright-driven scrape of `signalstrial.signalsresearch.revvitycloud.eu` on 2026-04-16. 42 entities across 4 notebooks, raw JSON in `raw/` and normalized fixtures in `fixtures/`. **These are our sample Signals data for designing the ingestion adapter** — don't re-scrape. The trial tenant blocks API key generation, so the fixtures are the offline source of truth.
- **`../SignalsStudioAI/recon/recon-notes.md`** — navigation map, click flows, template catalog. Template #1 "Industrial Chem Experiment Template" is the formulation-relevant one.
- **`../revvitysignals-mcp/`** — MCP server wrapping Signals REST v1.0 with 48 tools. Requires `x-api-key` auth — only useful against paid tenants. Once Formulation-AI hits a paying customer, vendor or wrap `src/client.ts`.
- **`../eb/Unified-Document-Retrieval/frontend`** — UI layout + component-library reference. Copy patterns from `AppShell.tsx`, `src/lib/utils.ts`, and the Radix/Tailwind config files verbatim.

## Domain context that isn't in the code

- **Heterogeneity is the hard problem.** Different R&D teams organize formulation data differently across Signals Notebook entities (experiments, notebook entries, embedded tables, attached xlsx). "Aggregated and tabularized" is not a schema — it's an adapter layer. The tabularized shape itself is simple: wide table, one row per tested formulation, N input columns + M output columns.
- **Output contract the optimizer must satisfy:** `(predicted value, 1-sigma uncertainty)` per output per candidate, plus a short rationale. This shape comes from Jun's "Sheet1 predictions" in `experiments/quad-model-proposal/Quad Model.xlsx`.
- **Results are mostly numerical.** Categorical (including pass/fail) is supported but not the default. Don't model results as booleans.
- **Jun is openly skeptical that LLMs can do DOE.** The `experiments/quad-model-proposal/` prototype is the concrete answer to that — a one-shot script that demonstrates Claude Opus 4.7 proposing new candidates with honest uncertainty on his synthetic dataset. When engaging Jun on the proposal engine, lead with runnable demos against his data, not architecture slides.

## Open questions / unknowns

- **Business framing.** "Standalone product via Revvity API" + David pursuing a Revvity hire creates a built-in tension — is this a Revvity-owned product, a partner product, or a net-new offering David is pitching? Answer affects branding, pricing, customer ownership. Still unresolved.
- **MVP slice.** Portfolio + DOE loop + ingestion adapter + LLM engine is too much for a first demo. The opinionated MVP is **the project-level DOE loop with one hardcoded Signals adapter + one read-only portfolio screen** — nail that before adding breadth.
- **Cost/latency at scale.** Opus 4.7 proposals work great on 9 points. At portfolio scale (5–10 projects × N iterations × K candidates each), cost and latency haven't been scoped.
- Three open clarifying questions to Jun (tracked in project memory): Signals entity types that house formulation data, anomaly-threshold approach for step 6, and the portfolio-reporting visual Jun wants.

## Current state

Initial scaffold committed. Auth plumbing is in but no product features yet — **do not start building features until Jun's next response closes the open questions and we've picked the MVP slice.** The Quad Model audition prototype runs end-to-end.
