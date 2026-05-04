"""Field-level encryption for sensitive settings (API keys).

Uses Fernet symmetric encryption with a key derived from the JWT secret.
Keys stored in app_settings are ciphertext; decrypted on read.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from formulation_ai.config import settings


def _derive_fernet_key() -> bytes:
    """Derive a Fernet-compatible key from the JWT secret."""
    raw = hashlib.sha256(settings.jwt_secret.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def _get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt(value: str) -> str:
    """Encrypt a setting value for DB storage."""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a setting value read from DB."""
    return _get_fernet().decrypt(value.encode()).decode()
