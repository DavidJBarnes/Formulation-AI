from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FA_", env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://formulation_ai:formulation_ai@localhost:5433/formulation_ai"
    )

    jwt_secret: str = "change-me-in-prod-this-is-for-local-dev-only"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # Optimizer (Phase 2)
    optimizer_backend: str = "llm"  # "llm" | "gp_sklearn" | "gp_botorch"
    optimizer_min_observations: int = 3  # fall back to LLM-only below this
    optimizer_acquisition: str = "ei"   # "ei" | "ucb" | "pi"
    optimizer_ucb_kappa: float = 2.0
    optimizer_ei_xi: float = 0.01
    optimizer_n_candidates: int = 3
    optimizer_n_restarts: int = 5
    optimizer_random_seed: int | None = None


settings = Settings()
