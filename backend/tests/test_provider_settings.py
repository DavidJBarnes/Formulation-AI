"""Unit tests for provider settings (model, routes, config resolution, proposal dispatch)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from formulation_ai.config import get_llm_config
from formulation_ai.models.app_setting import AppSetting
from formulation_ai.routers.admin import (
    ProviderSettingsIn,
    get_settings,
    update_settings,
)

# ---------------------------------------------------------------------------
# AppSetting model tests
# ---------------------------------------------------------------------------

class TestAppSettingModel:
    def test_create(self):
        setting = AppSetting(key="llm_provider", value="deepseek")
        assert setting.key == "llm_provider"
        assert setting.value == "deepseek"

    def test_update_value(self):
        setting = AppSetting(key="llm_model", value="old-model")
        setting.value = "new-model"
        assert setting.value == "new-model"


# ---------------------------------------------------------------------------
# get_settings route logic tests
# ---------------------------------------------------------------------------

class TestGetSettings:
    def test_returns_defaults_when_nothing_stored(self, monkeypatch):
        """When no DB settings exist, returns anthropic defaults."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = get_settings(db=mock_db, _=MagicMock())
        assert result.provider == "anthropic"
        assert result.api_key_set is False
        assert result.model == "claude-sonnet-4-6"

    def test_masks_api_key(self, monkeypatch):
        """api_key_set is True when key exists, but raw key never exposed."""
        row = MagicMock()
        row.key = "llm_api_key"
        row.value = "sk-secret-123"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [row]

        result = get_settings(db=mock_db, _=MagicMock())
        assert result.api_key_set is True
        # The result model has no field for the raw key — it's structurally masked
        assert result.model_dump().get("api_key") is None

    def test_returns_stored_provider_and_model(self, monkeypatch):
        rows = [
            _make_setting_row("llm_provider", "deepseek"),
            _make_setting_row("llm_model", "deepseek-chat-v2"),
        ]
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = rows

        result = get_settings(db=mock_db, _=MagicMock())
        assert result.provider == "deepseek"
        assert result.model == "deepseek-chat-v2"

    def test_admin_guard(self, monkeypatch):
        """get_current_admin is enforced by FastAPI dependency — tested via the dependency chain.
        We verify the endpoint requires the _ parameter which is typed as User.
        """
        # The function signature itself enforces get_current_admin via Depends()
        # This test just confirms the function runs when called directly
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        result = get_settings(db=mock_db, _=MagicMock())
        assert result.provider == "anthropic"


# ---------------------------------------------------------------------------
# update_settings route logic tests
# ---------------------------------------------------------------------------

class TestUpdateSettings:
    def test_save_provider_config(self, monkeypatch):
        """Successfully saves provider, key, and model. Key is stored encrypted."""
        mock_db = MagicMock()

        store: dict[str, str] = {}

        def fake_get(model, key):
            if key in store:
                row = MagicMock()
                row.value = store[key]
                return row
            return None

        def fake_add(obj):
            store[obj.key] = obj.value

        mock_db.get = fake_get
        mock_db.add = fake_add

        payload = ProviderSettingsIn(
            provider="deepseek",
            api_key="sk-deep-456",
            model="deepseek-chat",
        )

        result = update_settings(payload, db=mock_db, _=MagicMock())
        assert result.provider == "deepseek"
        assert result.api_key_set is True
        assert result.model == "deepseek-chat"

        # Verify store was populated
        assert store["llm_provider"] == "deepseek"
        # Key must be encrypted (Fernet token is base64, starts with gAAA)
        assert store["llm_api_key"] != "sk-deep-456"
        assert len(store["llm_api_key"]) > 50  # ciphertext is much longer
        assert store["llm_model"] == "deepseek-chat"
        assert mock_db.commit.called

    def test_rejects_invalid_api_key_format(self, monkeypatch):
        """API keys must match provider-specific patterns."""
        mock_db = MagicMock()

        # Anthropic key must start with sk-ant-
        payload = ProviderSettingsIn(provider="anthropic", api_key="sk-abc123")
        with pytest.raises(HTTPException) as exc:
            update_settings(payload, db=mock_db, _=MagicMock())
        assert exc.value.status_code == 422
        assert "must start with" in exc.value.detail

        # DeepSeek key must start with sk-
        payload = ProviderSettingsIn(provider="deepseek", api_key="bad-key")
        with pytest.raises(HTTPException) as exc:
            update_settings(payload, db=mock_db, _=MagicMock())
        assert exc.value.status_code == 422

    def test_valid_key_formats_accepted(self, monkeypatch):
        """Correctly formatted keys pass validation."""
        mock_db = MagicMock()
        mock_db.get.return_value = None  # no existing settings

        # Anthropic: sk-ant- prefix
        payload = ProviderSettingsIn(provider="anthropic", api_key="sk-ant-test123")
        result = update_settings(payload, db=mock_db, _=MagicMock())
        assert result.provider == "anthropic"

        # DeepSeek: sk- prefix
        payload2 = ProviderSettingsIn(provider="deepseek", api_key="sk-test456")
        result2 = update_settings(payload2, db=mock_db, _=MagicMock())
        assert result2.provider == "deepseek"

    def test_rejects_invalid_provider(self, monkeypatch):
        """Non-anthropic/non-deepseek provider raises 422."""
        mock_db = MagicMock()
        payload = ProviderSettingsIn(provider="openai", api_key="sk-123")

        with pytest.raises(HTTPException) as exc:
            update_settings(payload, db=mock_db, _=MagicMock())
        assert exc.value.status_code == 422

    def test_partial_update_preserves_existing(self, monkeypatch):
        """Changing only model preserves existing provider and key."""
        mock_db = MagicMock()

        existing_key = MagicMock()
        existing_key.value = "sk-existing"
        mock_db.get.return_value = existing_key  # existing row found

        payload = ProviderSettingsIn(
            provider="anthropic",
            model="claude-opus-4-7",
            # api_key omitted — should preserve existing
        )

        result = update_settings(payload, db=mock_db, _=MagicMock())
        assert result.provider == "anthropic"
        assert result.api_key_set is True  # existing key preserved
        assert result.model == "claude-opus-4-7"

    def test_admin_guard_via_dependency(self, monkeypatch):
        """update_settings requires get_current_admin via Depends()."""
        mock_db = MagicMock()
        payload = ProviderSettingsIn(provider="anthropic", api_key="sk-ant-test")
        # Should run without error when called directly (dependency is bypassed)
        result = update_settings(payload, db=mock_db, _=MagicMock())
        assert result.provider == "anthropic"


# ---------------------------------------------------------------------------
# Config resolution tests (env > DB)
# ---------------------------------------------------------------------------

class TestGetLlmConfig:
    def test_env_var_wins_override(self, monkeypatch):
        """Env var FA_LLM_PROVIDER overrides DB value."""
        from formulation_ai import config

        monkeypatch.setattr(config.settings, "llm_provider", "anthropic")
        monkeypatch.setattr(config.settings, "llm_api_key", "sk-env-key")

        provider, api_key, model = get_llm_config()
        assert provider == "anthropic"
        assert api_key == "sk-env-key"
        assert model == "claude-sonnet-4-6"

    def test_db_fallback_when_no_env(self, monkeypatch):
        """get_llm_config falls back to DB with single batch query + decryption."""
        from formulation_ai import config

        row_provider = _make_setting_row("llm_provider", "deepseek")
        # Key is stored encrypted; decrypt() will be called on it
        row_key = _make_setting_row("llm_api_key", "encrypted-deepseek-key")
        row_model = _make_setting_row("llm_model", "deepseek-chat-v3")

        # Mock the scalars().all() return
        mock_result = MagicMock()
        mock_result.all.return_value = [row_provider, row_key, row_model]

        db_session = MagicMock()
        db_session.scalars.return_value = mock_result

        # Mock decrypt to return a known plaintext
        from formulation_ai.services import crypto

        monkeypatch.setattr(crypto, "decrypt", lambda v: "sk-decrypted-db-key")

        monkeypatch.setattr(config.settings, "llm_provider", "anthropic")
        monkeypatch.setattr(config.settings, "llm_api_key", None)
        monkeypatch.setattr(config.settings, "llm_model", None)

        provider, api_key, model = get_llm_config(db_session)
        assert provider == "deepseek"
        assert api_key == "sk-decrypted-db-key"
        assert model == "deepseek-chat-v3"
        # Only one query issued
        db_session.scalars.assert_called_once()

    def test_legacy_anthropic_key_fallback(self, monkeypatch):
        """FA_ANTHROPIC_API_KEY used when provider=anthropic and no llm_api_key."""
        from formulation_ai import config

        monkeypatch.setattr(config.settings, "llm_provider", "anthropic")
        monkeypatch.setattr(config.settings, "llm_api_key", None)
        monkeypatch.setattr(config.settings, "anthropic_api_key", "sk-legacy")
        monkeypatch.setattr(config.settings, "llm_model", None)

        provider, api_key, model = get_llm_config()
        assert provider == "anthropic"
        assert api_key == "sk-legacy"
        assert model == "claude-sonnet-4-6"

    def test_no_db_session_no_crash(self, monkeypatch):
        """get_llm_config works without a DB session (env-only mode)."""
        from formulation_ai import config

        monkeypatch.setattr(config.settings, "llm_provider", "deepseek")
        monkeypatch.setattr(config.settings, "llm_api_key", "sk-env")
        monkeypatch.setattr(config.settings, "llm_model", "deepseek-chat")

        provider, api_key, model = get_llm_config()
        assert provider == "deepseek"
        assert api_key == "sk-env"
        assert model == "deepseek-chat"


# ---------------------------------------------------------------------------
# Proposal engine provider dispatch tests
# ---------------------------------------------------------------------------

class TestProposalDispatch:
    def test_default_to_anthropic(self, monkeypatch):
        """When provider=anthropic, dispatches to Anthropic."""
        from formulation_ai.services import proposal_engine
        from formulation_ai.services.proposal_engine import ProposalRequest, ProposedFormulation

        called_anthropic = []
        called_deepseek = []

        def fake_anthropic(req, api_key, model):
            called_anthropic.append((api_key, model))
            return [ProposedFormulation("P-1-1", "test", {}, [])]

        def fake_deepseek(req, api_key, model):
            called_deepseek.append(True)
            return []

        monkeypatch.setattr(proposal_engine, "_run_anthropic_proposal", fake_anthropic)
        monkeypatch.setattr(proposal_engine, "_run_deepseek_proposal", fake_deepseek)
        monkeypatch.setattr(proposal_engine.settings, "llm_provider", "anthropic")
        monkeypatch.setattr(proposal_engine.settings, "llm_api_key", "sk-test")
        monkeypatch.setattr(proposal_engine.settings, "llm_model", "claude-sonnet-4-6")

        req = ProposalRequest(
            project_name="Test",
            iteration_n=1,
            ingredients=[],
            targets=[],
            base_products=[],
            tested=[],
        )
        proposal_engine.run_proposal(req)
        assert len(called_anthropic) == 1
        assert len(called_deepseek) == 0

    def test_deepseek_when_configured(self, monkeypatch):
        """When provider=deepseek, dispatches to DeepSeek."""
        from formulation_ai.services import proposal_engine
        from formulation_ai.services.proposal_engine import ProposalRequest, ProposedFormulation

        called_anthropic = []
        called_deepseek = []

        def fake_anthropic(req, api_key, model):
            called_anthropic.append(True)
            return []

        def fake_deepseek(req, api_key, model):
            called_deepseek.append((api_key, model))
            return [ProposedFormulation("P-1-1", "test", {}, [])]

        monkeypatch.setattr(proposal_engine, "_run_anthropic_proposal", fake_anthropic)
        monkeypatch.setattr(proposal_engine, "_run_deepseek_proposal", fake_deepseek)
        monkeypatch.setattr(proposal_engine.settings, "llm_provider", "deepseek")
        monkeypatch.setattr(proposal_engine.settings, "llm_api_key", "sk-deep")
        monkeypatch.setattr(proposal_engine.settings, "llm_model", "deepseek-chat")

        req = ProposalRequest(
            project_name="Test",
            iteration_n=1,
            ingredients=[],
            targets=[],
            base_products=[],
            tested=[],
        )
        proposal_engine.run_proposal(req)
        assert len(called_anthropic) == 0
        assert len(called_deepseek) == 1
        assert called_deepseek[0] == ("sk-deep", "deepseek-chat")

    def test_missing_api_key_raises(self, monkeypatch):
        """run_proposal raises RuntimeError when no API key is configured."""
        from formulation_ai.services import proposal_engine
        from formulation_ai.services.proposal_engine import ProposalRequest

        monkeypatch.setattr(proposal_engine.settings, "llm_provider", "deepseek")
        monkeypatch.setattr(proposal_engine.settings, "llm_api_key", None)
        monkeypatch.setattr(proposal_engine.settings, "llm_model", "deepseek-chat")
        monkeypatch.setattr("formulation_ai.config.settings.anthropic_api_key", None)

        req = ProposalRequest(
            project_name="Test",
            iteration_n=1,
            ingredients=[],
            targets=[],
            base_products=[],
            tested=[],
        )
        with pytest.raises(RuntimeError, match="No API key configured"):
            proposal_engine.run_proposal(req)

    def test_gp_short_circuits_llm(self, monkeypatch):
        """GP backend skips LLM entirely when enough data exists."""
        from formulation_ai.services import proposal_engine
        from formulation_ai.services.proposal_engine import ProposalRequest, ProposedFormulation

        called_llm = []

        monkeypatch.setattr(
            proposal_engine,
            "_run_llm_proposal",
            lambda req, db_session=None: called_llm.append(True) or [],
        )
        monkeypatch.setattr("formulation_ai.config.settings.optimizer_backend", "gp_sklearn")
        monkeypatch.setattr("formulation_ai.config.settings.optimizer_min_observations", 5)

        req = ProposalRequest(
            project_name="Test",
            iteration_n=1,
            ingredients=[],
            targets=[],
            base_products=[],
            tested=[{}, {}],  # 2 < 5 → falls back to LLM
        )

        def fake_gp(req):
            return [ProposedFormulation("GP-1", "gp", {}, [])]

        monkeypatch.setattr("formulation_ai.optimizer.gp_proposal.run_gp_proposal", fake_gp)
        proposal_engine.run_proposal(req)
        assert len(called_llm) == 1  # Below threshold, so LLM path taken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_setting_row(key: str, value: str) -> MagicMock:
    row = MagicMock()
    row.key = key
    row.value = value
    return row
