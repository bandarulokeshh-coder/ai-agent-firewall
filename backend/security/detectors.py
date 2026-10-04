"""Security detection engines: PII, secrets, prompt injection, classification."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Finding:
    """One detected security finding."""
    kind: str          # "PII", "SECRET", "INJECTION", "CLASSIFICATION"
    label: str         # e.g. "email", "api_key", "instruction_override"
    count: int = 1
    score: int = 0     # contribution to the risk score
    samples: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "label": self.label, "count": self.count,
            "score": self.score, "samples": self.samples, "locations": self.locations,
        }


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

PII_PATTERNS: Dict[str, tuple] = {
    "email": (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), 4),
    "phone_intl": (re.compile(r"\+?\d[\d\s().-]{8,}\d"), 3),
    "credit_card": (re.compile(r"\b(?:\d[ -]?){13,16}\b"), 25),
    "ip_address": (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 3),
    "ssn_like": (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 20),
    "date_of_birth": (re.compile(r"\b(0?[1-9]|[12]\d|3[01])[/-](0?[1-9]|1[0-2])[/-](19|20)\d{2}\b"), 5),
}


def detect_pii(text: str) -> List[Finding]:
    """Detect PII in text. Returns structured findings with redacted samples."""
    findings: List[Finding] = []
    for label, (pattern, score) in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if not matches:
            continue
        samples = []
        for m in matches[:3]:
            s = str(m)
            samples.append(s[:3] + "***" + s[-2:] if len(s) > 6 else "***")
        findings.append(Finding(
            kind="PII", label=label, count=len(matches), score=score * len(matches),
            samples=samples,
        ))
    return findings


# ---------------------------------------------------------------------------
# Secret detection
# ---------------------------------------------------------------------------

SECRET_PATTERNS: Dict[str, tuple] = {
    "openai_api_key": (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), 40),
    "github_token": (re.compile(r"gh[pousr]_[a-zA-Z0-9]{30,}"), 40),
    "aws_access_key": (re.compile(r"AKIA[0-9A-Z]{16}"), 40),
    "jwt": (re.compile(r"\beyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"), 35),
    "api_key_generic": (re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{16,}['\"]?", re.IGNORECASE), 30),
    "password_field": (re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?", re.IGNORECASE), 25),
    "db_connection_string": (re.compile(r"(?:postgres(ql)?|mysql|mongodb(\+srv)?)://[^\s:]+:[^\s@]+@[^\s]+", re.IGNORECASE), 35),
    "private_key_block": (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), 50),
    "bearer_token": (re.compile(r"[Bb]earer\s+[a-zA-Z0-9._-]{20,}"), 30),
    "slack_token": (re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"), 40),
    "env_secret": (re.compile(r"(?:SECRET|TOKEN|KEY)\s*[:=]\s*['\"]?[a-zA-Z0-9+/=_-]{20,}['\"]?", re.IGNORECASE), 25),
}


def detect_secrets(text: str) -> List[Finding]:
    """Detect secrets in text. Samples are always redacted."""
    findings: List[Finding] = []
    for label, (pattern, score) in SECRET_PATTERNS.items():
        matches = pattern.findall(text)
        if not matches:
            continue
        samples = ["***REDACTED***"] * min(len(matches), 2)
        findings.append(Finding(
            kind="SECRET", label=label, count=len(matches), score=score * len(matches),
            samples=samples,
        ))
    return findings


# ---------------------------------------------------------------------------
# Prompt injection detection
# ---------------------------------------------------------------------------

INJECTION_PATTERNS: Dict[str, tuple] = {
    "instruction_override": (re.compile(r"(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:previous|prior|above|earlier|your)\s+(?:instructions|prompts?|rules|directives)", re.IGNORECASE), 40),
    "system_prompt_extraction": (re.compile(r"(?:reveal|show|print|repeat|output|display)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions|initial\s+instructions)", re.IGNORECASE), 35),
    "security_bypass": (re.compile(r"(?:disable|bypass|ignore|turn\s+off)\s+(?:all\s+)?(?:security|safety|filters?|guardrails?|restrictions)", re.IGNORECASE), 40),
    "credential_extraction": (re.compile(r"(?:extract|steal|send|copy|export|exfiltrate)\s+(?:the\s+)?(?:api\s*key|password|credentials?|secrets?|tokens?|\.env)", re.IGNORECASE), 45),
    "data_exfiltration": (re.compile(r"(?:send|post|upload|transmit|curl)\s+.{0,40}(?:https?://|ftp://|attacker|evil)", re.IGNORECASE), 40),
    "role_switch": (re.compile(r"(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|enter\s+(?:developer|dan|god)\s+mode)", re.IGNORECASE), 25),
    "tool_abuse": (re.compile(r"(?:run|execute)\s+(?:this\s+)?(?:command|script|payload|malware|reverse\s+shell)", re.IGNORECASE), 35),
    "hidden_instruction": (re.compile(r"<!--\s*(?:instructions?|note\s+to\s+(?:ai|assistant|gpt))", re.IGNORECASE), 45),
    "base64_payload": (re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"), 15),
}


def detect_prompt_injection(text: str) -> dict:
    """Detect prompt injection. Returns dict with score, confidence, findings."""
    findings: List[Finding] = []
    total = 0
    for label, (pattern, score) in INJECTION_PATTERNS.items():
        matches = pattern.findall(text)
        if not matches:
            continue
        contribution = score + 10 * (len(matches) - 1)
        total += contribution
        findings.append(Finding(
            kind="INJECTION", label=label, count=len(matches),
            score=min(contribution, 60),
            samples=[str(m)[:60] for m in matches[:2]],
        ))
    score = min(total, 100)
    confidence = min(50 + 10 * len(findings) * 2, 95) if findings else 0
    return {"score": score, "confidence": confidence, "findings": findings}


# ---------------------------------------------------------------------------
# Data classification
# ---------------------------------------------------------------------------

CLASSIFICATION_KEYWORDS: Dict[str, tuple] = {
    "RESTRICTED": (re.compile(r"(?:top\s+secret|classified|restricted|internal\s+only)", re.IGNORECASE), 40),
    "CONFIDENTIAL": (re.compile(r"(?:confidential|proprietary|customer\s+data|personal\s+data|financial\s+statement|salary|payroll)", re.IGNORECASE), 25),
    "INTERNAL": (re.compile(r"(?:internal\s+use|draft|do\s+not\s+distribute)", re.IGNORECASE), 15),
}

LABEL_SCORES = {"PUBLIC": 0, "INTERNAL": 15, "CONFIDENTIAL": 30, "RESTRICTED": 45}


def classify_content(text: str) -> tuple:
    """Classify text sensitivity. Returns (label, Finding|None)."""
    best = "PUBLIC"
    best_match = None
    for label, (pattern, score) in CLASSIFICATION_KEYWORDS.items():
        m = pattern.search(text)
        if m:
            if LABEL_SCORES[label] >= LABEL_SCORES[best]:
                best = label
                best_match = m
    if best == "PUBLIC":
        return best, None
    finding = Finding(
        kind="CLASSIFICATION", label=best, count=1,
        score=LABEL_SCORES[best],
        samples=[best_match.group(0)[:60]] if best_match else [],
    )
    return best, finding


def inspect_text(text: str) -> dict:
    """Full inspection pipeline for any text (prompt or extracted file content)."""
    pii = detect_pii(text)
    secrets = detect_secrets(text)
    injection = detect_prompt_injection(text)
    label, cls_finding = classify_content(text)

    return {
        "pii": [f.to_dict() for f in pii],
        "secrets": [f.to_dict() for f in secrets],
        "injection": {
            "score": injection["score"],
            "confidence": injection["confidence"],
            "findings": [f.to_dict() for f in injection["findings"]],
        },
        "classification": label,
        "classification_finding": cls_finding.to_dict() if cls_finding else None,
        "total_findings": len(pii) + len(secrets) + len(injection["findings"]) + (1 if cls_finding else 0),
    }