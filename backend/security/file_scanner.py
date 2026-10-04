"""Real file scanner: extract text from PDF/DOCX/CSV/JSON/TXT, then inspect it."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
import time
from typing import Any, Dict, Optional

from .detectors import inspect_text
from .redaction import redact_file_content


MAX_TEXT_CHARS = 100_000  # don't inspect beyond this

SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".py": "text/x-python",
    ".js": "text/javascript",
    ".ts": "text/typescript",
    ".html": "text/html",
    ".md": "text/markdown",
    ".env": "text/plain",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_text(filename: str, data: bytes) -> Dict[str, Any]:
    """Extract text from a file's raw bytes based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    pages: Optional[int] = None
    error = None

    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            pages = len(reader.pages)
            parts = []
            for i, page in enumerate(reader.pages):
                t = page.extract_text() or ""
                parts.append(f"[page {i + 1}] {t}")
            text = "\n".join(parts)
        elif ext == ".docx":
            import docx
            document = docx.Document(io.BytesIO(data))
            text = "\n".join(p.text for p in document.paragraphs)
        elif ext == ".csv":
            decoded = data.decode("utf-8", errors="replace")
            rows = list(csv.reader(io.StringIO(decoded)))
            text = "\n".join(",".join(r) for r in rows[:500])
        elif ext == ".json":
            text = json.dumps(json.loads(data.decode("utf-8", errors="replace")), indent=2)[:MAX_TEXT_CHARS]
        elif ext in (".png", ".jpg", ".jpeg"):
            text = ""  # image OCR is out of scope; metadata only
        else:
            text = data.decode("utf-8", errors="replace")
    except Exception as exc:  # malformed file should not crash the gateway
        error = str(exc)
        text = ""

    return {"text": text[:MAX_TEXT_CHARS], "pages": pages, "error": error}


def scan_file(filename: str, data: bytes, redact: bool = False) -> dict:
    """Scan an uploaded file: real extraction, real inspection, real decision."""
    started = time.time()
    ext = os.path.splitext(filename)[1].lower()
    extracted = extract_text(filename, data)
    text = extracted["text"]

    if text:
        inspection = inspect_text(text)
    else:
        inspection = {
            "pii": [], "secrets": [],
            "injection": {"score": 0, "confidence": 0, "findings": []},
            "classification": "PUBLIC", "classification_finding": None,
            "total_findings": 0,
        }

    pii_findings = inspection["pii"]
    secret_findings = inspection["secrets"]
    injection = inspection["injection"]
    classification = inspection["classification"]

    # Reuse the shared risk engine so files and prompts score consistently.
    from .risk_engine import compute_risk
    file_risk = compute_risk(
        pii_findings=pii_findings,
        secret_findings=secret_findings,
        injection=injection,
        classification=classification,
        has_external_destination=True,
    )

    sanitized = None
    redactions = []
    if redact and text:
        sanitized, redactions = redact_file_content(text)
        if file_risk["decision"] in ("BLOCK", "REDACT"):
            file_risk["decision"] = "REDACTED"

    record = {
        "filename": filename,
        "extension": ext,
        "mime_type": SUPPORTED_EXTENSIONS.get(ext, "application/octet-stream"),
        "size_bytes": len(data),
        "sha256": _sha256(data),
        "pages": extracted["pages"],
        "text_extracted_chars": len(text),
        "extraction_error": extracted["error"],
        "pii": pii_findings,
        "secrets": secret_findings,
        "injection": injection,
        "classification": classification,
        "risk_score": file_risk["score"],
        "risk_level": file_risk["level"],
        "risk_reasons": file_risk["reasons"],
        "decision": file_risk["decision"],
        "pii_count": sum(p["count"] for p in pii_findings),
        "secret_count": sum(s["count"] for s in secret_findings),
        "sanitized_available": bool(sanitized),
        "sanitized": sanitized,
        "redactions": redactions,
        "scan_duration_ms": int((time.time() - started) * 1000),
    }
    # Secrets must never be echoed back in plaintext samples.
    for s in record["secrets"]:
        s["samples"] = ["***REDACTED***"] * len(s["samples"])
    return record


class TempFileStore:
    """Secure temp-file handling: writes to a private temp dir, auto-deletes."""

    def __init__(self) -> None:
        self._dir = tempfile.mkdtemp(prefix="aifw_")
        self._files: list = []

    def save(self, filename: str, data: bytes) -> str:
        safe = os.path.basename(filename)
        path = os.path.join(self._dir, safe)
        with open(path, "wb") as fh:
            fh.write(data)
        self._files.append(path)
        return path

    def cleanup(self) -> int:
        removed = 0
        for path in self._files:
            try:
                os.remove(path)
                removed += 1
            except OSError:
                pass
        self._files.clear()
        try:
            os.rmdir(self._dir)
        except OSError:
            pass
        return removed

    @property
    def dir(self) -> str:
        return self._dir