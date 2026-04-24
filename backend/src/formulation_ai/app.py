"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from formulation_ai.config import settings
from formulation_ai.routers import auth as auth_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Formulation-AI API",
        description="Closed-loop AI formulation optimization.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
