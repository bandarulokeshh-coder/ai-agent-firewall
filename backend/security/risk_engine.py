"""Transparent risk engine: every score comes with a reason list."""
from __future__ import annotations

from typing import Dict, List


RISK_THRESHOLDS = {
    "warn": 30,        # >= warn → MEDIUM
    "approval": 60,    # >= approval → HIGH (needs human)
    "block": 80,       # >= block → CRITICAL
}


def _level_for(score: int) -> str:
    if score >= RISK_THRESHOLDS["block"]:
        return "CRITICAL"
    if score >= RISK_THRESHOLDS["approval"]:
        return "HIGH"
    if score >= RISK_THRESHOLDS["warn"]:
        return "MEDIUM"
    return "LOW"


def _decision_for(score: int, redact_available: bool = True) -> str:
    """Map score to policy decision. REDACT preferred over APPROVE when possible."""
    if score >= RISK_THRESHOLDS["block"]:
        return "BLOCK"
    if score >= RISK_THRESHOLDS["approval"]:
        return "REDACT" if redact_available else "APPROVAL"
    if score >= RISK_THRESHOLDS["warn"]:
        return "REDACT" if redact_available else "WARN"
    return "ALLOW"


def compute_risk(
    pii_findings: List[dict],
    secret_findings: List[dict],
    injection: dict,
    classification: str,
    has_external_destination: bool = True,
    files: List[dict] | None = None,
) -> dict:
    """Compute a transparent risk score with a reason breakdown.

    Every point is accounted for. Returns:
        {"score": int, "level": str, "decision": str, "reasons": [
            {"points": int, "reason": str}
        ]}
    """
    reasons: List[dict] = []
    total = 0

    # 1. Secrets (highest severity)
    for s in secret_findings:
        reasons.append({"points": s["score"], "reason": f"Secret detected: {s['label']} ×{s['count']}"})
        total += s["score"]

    # 2. Prompt injection
    inj_score = injection.get("score", 0)
    if inj_score > 0:
        reasons.append({"points": inj_score, "reason": f"Prompt injection indicators (confidence {injection.get('confidence', 0)}%)"})
        total += inj_score

    # 3. PII volume
    pii_total = sum(p["score"] for p in pii_findings)
    if pii_total > 0:
        pii_count = sum(p["count"] for p in pii_findings)
        capped = min(pii_total, 40)
        reasons.append({"points": capped, "reason": f"PII detected: {pii_count} records"})
        total += capped

    # 4. Classification
    cls_points = {"PUBLIC": 0, "INTERNAL": 15, "CONFIDENTIAL": 30, "RESTRICTED": 45}.get(classification, 0)
    if cls_points > 0:
        reasons.append({"points": cls_points, "reason": f"Content classified {classification}"})
        total += cls_points

    # 5. File risk
    for f in (files or []):
        if f.get("risk_score", 0) > 0:
            bonus = min(int(f["risk_score"] * 0.3), 25)
            reasons.append({"points": bonus, "reason": f"File risk: {f.get('filename', 'file')}"})
            total += bonus

    # 6. External provider (always sending data outside)
    if has_external_destination:
        reasons.append({"points": 10, "reason": "Data leaves environment to external AI provider"})
        total += 10

    score = min(total, 100)
    level = _level_for(score)
    decision = _decision_for(score, redact_available=bool(secret_findings or pii_findings))

    return {"score": score, "level": level, "decision": decision, "reasons": reasons}


def explain(score: int, level: str, decision: str, reasons: List[dict]) -> str:
    """Human-readable explanation of a risk score."""
    lines = [f"RISK SCORE: {score} ({level}) → {decision}"]
    for r in reasons:
        lines.append(f"  +{r['points']:>3}  {r['reason']}")
    return "\n".join(lines)