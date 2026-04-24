# Formulation-AI backend

FastAPI + Postgres. Managed with `uv`.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn formulation_ai.app:app --reload --port 8000
```

Config is driven by pydantic-settings with env prefix `FA_` (see `src/formulation_ai/config.py`).
