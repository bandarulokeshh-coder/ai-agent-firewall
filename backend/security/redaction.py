"""Redaction engine: sanitize sensitive data before it reaches the AI provider."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple


# Replacement tokens shown to both the model and the user.
REPLACEMENT_TOKENS: Dict[str, str] = {
    "email": "[EMAIL_REDACTED]",
    "phone_intl": "[PHONE_REDACTED]",
    "credit_card": "[CARD_REDACTED]",
    "ip_address": "[IP_REDACTED]",
    "ssn_like": "[SSN_REDACTED]",
    "date_of_birth": "[DOB_REDACTED]",
    "openai_api_key": "[API_KEY_REDACTED]",
    "github_token": "[TOKEN_REDACTED]",
    "aws_access_key": "[AWS_KEY_REDACTED]",
    "jwt": "[JWT_REDACTED]",
    "api_key_generic": "[API_KEY_REDACTED]",
    "password_field": "[PASSWORD_REDACTED]",
    "db_connection_string": "[DB_CREDENTIALS_REDACTED]",
    "private_key_block": "[PRIVATE_KEY_REDACTED]",
    "bearer_token": "[TOKEN_REDACTED]",
    "slack_token": "[SLACK_TOKEN_REDACTED]",
    "env_secret": "[SECRET_REDACTED]",
}


def redact_text(text: str, kinds: List[str] | None = None) -> Tuple[str, List[dict]]:
    """Replace sensitive spans with redaction tokens.

    Args:
        text: original content.
        kinds: which finding kinds to redact — subset of
               ["PII", "SECRET"]. None means redact everything detectable.

    Returns:
        (sanitized_text, list_of {"label", "count"} redactions applied)
    """
    from .detectors import PII_PATTERNS, SECRET_PATTERNS  # local import avoids cycle

    want = set(kinds) if kinds else {"PII", "SECRET"}
    sanitized = text
    applied: List[dict] = []

    # Secrets FIRST — otherwise PII patterns (e.g. phone digits) can mangle
    # an API key string and leave a partially-recognizable secret behind.
    if "SECRET" in want:
        for label, (pattern, _score) in SECRET_PATTERNS.items():
            matches = pattern.findall(sanitized)
            if not matches:
                continue
            sanitized = pattern.sub(REPLACEMENT_TOKENS[label], sanitized)
            applied.append({"label": label, "count": len(matches)})

    if "PII" in want:
        # Most-specific patterns first so credit cards don't get
        # swallowed by the looser international-phone rule.
        ordered = sorted(
            PII_PATTERNS.items(),
            key=lambda kv: {"credit_card": 0, "ssn_like": 1, "date_of_birth": 2,
                            "email": 3, "ip_address": 4, "phone_intl": 9}.get(kv[0], 5),
        )
        for label, (pattern, _score) in ordered:
            matches = pattern.findall(sanitized)
            if not matches:
                continue
            sanitized = pattern.sub(REPLACEMENT_TOKENS[label], sanitized)
            applied.append({"label": label, "count": len(matches)})

    return sanitized, applied


def redact_file_content(text: str) -> Tuple[str, List[dict]]:
    """Redact everything detectable in extracted file content."""
    return redact_text(text, kinds=["PII", "SECRET"])


def verify_no_secrets(sanitized: str) -> dict:
    """Post-redaction check: confirms the sanitized text has no original secrets.

    Returns {"clean": bool, "residual": [labels]}. Used by the output firewall
    and by tests to guarantee secrets never reach the provider.
    """
    from .detectors import SECRET_PATTERNS
    residual = []
    for label, (pattern, _score) in SECRET_PATTERNS.items():
        if pattern.search(sanitized):
            residual.append(label)
    return {"clean": not residual, "residual": residual}