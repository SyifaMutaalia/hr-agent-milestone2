"""Security helpers. Complete every TODO before persisting telemetry."""
from __future__ import annotations

import hashlib
import re

def token_hash(token: str) -> str:
    """Hash token menggunakan SHA-256 agar raw token tidak disimpan."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
    raise NotImplementedError


def stable_safety_id(employee_id: str) -> str:
    """Membuat identifier stabil tanpa mengirim employee_id asli ke provider."""
    return hashlib.sha256(
        f"hr-assistant:{employee_id}".encode("utf-8")
    ).hexdigest()
    raise NotImplementedError


def redact(value: str) -> str:
    """Menyamarkan informasi sensitif sebelum disimpan ke telemetry."""
    if not value:
        return value

    result = value

    # Email
    result = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        result,
    )

    # Nomor telepon Indonesia: 08..., +62..., 62...
    result = re.sub(
        r"(?<!\d)(?:\+62|62|0)8\d{7,12}(?!\d)",
        "[REDACTED_PHONE]",
        result,
    )

    # Token / API-key-like values.
    result = re.sub(
        r"(?i)\b(?:token|bearer|api[_-]?key|secret)[-_:\s]+[A-Za-z0-9._-]{6,}\b",
        "[REDACTED_TOKEN]",
        result,
    )

    # Medical details supplied using common labels.
    result = re.sub(
        r"(?i)\b(?:diagnosis|diagnosa|penyakit|kondisi medis)\s*:\s*"
        r"[^.;,\n]+",
        "[REDACTED_MEDICAL]",
        result,
    )

    return result