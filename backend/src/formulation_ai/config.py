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

    # LLM provider settings (env vars win, DB falls back)
    anthropic_api_key: str | None = None  # legacy — prefer FA_LLM_API_KEY
    anthropic_model: str = "claude-sonnet-4-6"  # legacy — prefer FA_LLM_MODEL
    llm_provider: str = "anthropic"  # "anthropic" | "deepseek"
    llm_api_key: str | None = None
    llm_model: str | None = None

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

# Default models per provider
_PROVIDER_DEFAULTS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "deepseek": "deepseek-chat",
}


def get_llm_config(db_session=None) -> tuple[str, str | None, str]:
    """Resolve (provider, api_key, model) with env-over-DB precedence.

    Returns a 3-tuple of (provider, api_key, model).
    api_key may be None if not configured (the caller should raise a clear error).
    """
    provider = settings.llm_provider
    api_key: str | None = settings.llm_api_key
    model: str | None = settings.llm_model

    # Fall back to DB if any value is at its default and a session is provided
    if db_session is not None and (provider == "anthropic" or api_key is None or model is None):
        from sqlalchemy import select

        from formulation_ai.models.app_setting import AppSetting
        from formulation_ai.services.crypto import decrypt

        # Single query for all three settings — avoids race condition
        rows = db_session.scalars(
            select(AppSetting).where(
                AppSetting.key.in_(["llm_provider", "llm_api_key", "llm_model"])
            )
        ).all()
        stored = {row.key: row.value for row in rows}

        if "llm_provider" in stored:
            provider = stored["llm_provider"]

        if api_key is None and "llm_api_key" in stored:
            try:
                api_key = decrypt(stored["llm_api_key"])
            except Exception:
                # Corrupted or legacy plaintext — treat as None
                api_key = None

        if model is None and "llm_model" in stored:
            model = stored["llm_model"]

    # Legacy fallback: FA_ANTHROPIC_API_KEY when provider is anthropic
    if provider == "anthropic" and api_key is None and settings.anthropic_api_key:
        api_key = settings.anthropic_api_key

    # If model is still None, use provider default
    if model is None:
        model = _PROVIDER_DEFAULTS.get(provider, "claude-sonnet-4-6")

    return provider, api_key, model
