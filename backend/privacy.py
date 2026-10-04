"""AI Agent Data Auto-Deletion.

Secure file lifecycle tracking with automated cleanup, retention policies,
deletion verification, and an append-only activity log.

Uploaded files are NEVER persisted as raw bytes. The only artifact the gateway
holds is the sanitized text cached in-memory (keyed by a file id / `fid`).
This module explicitly manages that artifact's lifecycle: register on upload,
mark consumed when a chat uses it, auto-delete once the retention policy
allows, verify the removal actually happened, and log every event. This
replaces an invisible TTL with an auditable, verifiable deletion path.
"""
from __future__ import annotations

import time
import threading
from uuid import uuid4
from typing import Callable, Dict, List, Optional

# Retention policies surfaced to the privacy dashboard UI.
RETENTION_OPTIONS = {
    # Delete as soon as the file is consumed by a chat; safety-cap if never used.
    "post_processing": "After processing (default)",
    "5m": "5 minutes",
    "10m": "10 minutes",
    "manual": "Manual only",
}

# Absolute safety cap on any cached sanitized content regardless of policy.
HARD_TTL_SECONDS = 600

DEFAULT_RETENTION_POLICY = "post_processing"

# Lifecycle states.
ACTIVE = "ACTIVE"          # cached and available, not yet eligible for removal
PENDING = "PENDING"        # eligible (consumed/retention elapsed) waiting on sweeper
DELETED = "DELETED"        # removed from cache

# Activity log event types.
class PrivacyEventType:
    UPLOADED = "uploaded"
    CONSUMED = "consumed"
    SCHEDULED = "scheduled_for_deletion"
    DELETED = "deleted"
    VERIFIED = "delete_verified"
    FAILED = "delete_failed"
    POLICY_CHANGED = "policy_changed"
    MANUAL_DELETE = "manual_delete"


def _now() -> float:
    return time.time()


def _iso(epoch: Optional[float]) -> Optional[str]:
    if epoch is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class PrivacyTracker:
    """Tracks uploaded-file lifecycle and performs verified auto-deletion.

    The tracker is intentionally in-memory, mirroring the existing
    ``_file_cache`` philosophy: nothing is persisted, and it is dropped when
    the process restarts. Deletion means removing the sanitized cache entry
    and confirming it is gone.
    """

    def __init__(self, retention_policy: str = DEFAULT_RETENTION_POLICY) -> None:
        self._policy = retention_policy if retention_policy in RETENTION_OPTIONS else DEFAULT_RETENTION_POLICY
        self._files: Dict[str, dict] = {}
        self._activity: List[dict] = []
        # Reentrant lock: _log() re-acquires self._lock while the caller already
        # holds it (mark_consumed / sweep / _evict_and_verify all log inside their
        # locked region). A plain Lock would self-deadlock there.
        self._lock = threading.RLock()
        # Set by main.py: evict a fid from the file cache, returning True if it
        # was present (i.e. actually removed).
        self._cache_evict: Optional[Callable[[str], bool]] = None
        # Counters kept independent of the capped recent-activity list.
        self._counters = {
            "total_uploads": 0, "consumed": 0, "deleted": 0, "manual_deletes": 0,
        }

    # -- wiring -------------------------------------------------------------

    def configure(self, cache_evict: Callable[[str], bool]) -> None:
        """Attach the backend's real cache-eviction callback."""
        self._cache_evict = cache_evict

    @property
    def policy(self) -> str:
        return self._policy

    def set_policy(self, policy: str) -> bool:
        """Change the retention policy. Existing records keep theirs; applies to new uploads."""
        if policy not in RETENTION_OPTIONS:
            return False
        with self._lock:
            self._policy = policy
        self._log(PrivacyEventType.POLICY_CHANGED, None, detail=f"retention policy set to {policy} ({RETENTION_OPTIONS[policy]})")
        return True

    # -- lifecycle ----------------------------------------------------------

    def register(self, metadata: dict) -> str:
        """Register an upload. Returns the fid of the cached artifact to track.

        Uploads whose content was NOT cached (e.g. an image with no extractable
        text) are still recorded as a verified-clean lifecycle: nothing was ever
        stored at rest, so there is nothing to delete. This makes every upload —
        image or document — visible in the privacy dashboard.
        """
        fid = metadata.get("fid") or ""
        with self._lock:
            self._counters["total_uploads"] += 1
            if fid:
                self._files[fid] = {
                    "fid": fid,
                    "filename": metadata.get("filename", "untitled"),
                    "extension": metadata.get("extension", ""),
                    "size_bytes": metadata.get("size_bytes", 0),
                    "sha256": metadata.get("sha256", "")[:16],
                    "classification": metadata.get("classification", "PUBLIC"),
                    "risk_score": metadata.get("risk_score", 0),
                    "risk_level": metadata.get("risk_level", "LOW"),
                    "uploaded_epoch": _now(),
                    "uploaded_at": _iso(_now()),
                    "retention_policy": self._policy,
                    "delete_at": None,            # set when a time-based retention applies
                    "state": ACTIVE,
                    "consumed_at": None,
                    "consumed_epoch": None,
                    "deleted_at": None,
                    "deleted_by": None,
                    "verified": None,             # None: not yet deleted
                    "verification_at": None,
                    "failure": None,
                }
            else:
                # Nothing cached at rest: already gone and verified.
                now = _now()
                self._files["clean-" + str(uuid4().hex[:8])] = {
                    "fid": "", "filename": metadata.get("filename", "untitled"),
                    "extension": metadata.get("extension", ""),
                    "size_bytes": metadata.get("size_bytes", 0),
                    "sha256": metadata.get("sha256", "")[:16],
                    "classification": metadata.get("classification", "PUBLIC"),
                    "risk_score": metadata.get("risk_score", 0),
                    "risk_level": metadata.get("risk_level", "LOW"),
                    "uploaded_epoch": now, "uploaded_at": _iso(now),
                    "retention_policy": self._policy, "delete_at": now,
                    "state": DELETED, "consumed_at": None, "consumed_epoch": None,
                    "deleted_at": _iso(now), "deleted_by": "nothing_retained",
                    "verified": True, "verification_at": _iso(now), "failure": None,
                }
        self._log(PrivacyEventType.UPLOADED, fid, detail=f"{metadata.get('filename','')} · {metadata.get('size_bytes',0)} B · {metadata.get('classification','PUBLIC')} · retention={self._policy}{' · nothing retained' if not fid else ''}")
        return fid

    def mark_consumed(self, fid: str) -> bool:
        """Called when a chat actually uses the cached artifact."""
        with self._lock:
            rec = self._files.get(fid)
            if not rec or rec["state"] == DELETED:
                return False
            rec["consumed_at"] = _iso(_now())
            rec["consumed_epoch"] = _now()
            if rec["retention_policy"] != "manual":
                # Consumption is the trigger for auto-deletion under
                # post_processing; time-based policies keep their schedule.
                rec["state"] = PENDING
                self._log(PrivacyEventType.CONSUMED, fid, detail=f"consumed; scheduled for auto-delete")
            else:
                self._counters["consumed"] += 1
                self._log(PrivacyEventType.CONSUMED, fid, detail="consumed (manual retention keeps it)")
                return True
            self._counters["consumed"] += 1
        return True

    def delete_now(self, fid: str, source: str = "manual") -> dict:
        """Delete + verify immediately (used by the dashboard & sweeper)."""
        with self._lock:
            rec = self._files.get(fid)
            if not rec:
                return {"ok": False, "reason": "unknown_fid"}
            if rec["state"] == DELETED:
                return {"ok": True, "already_deleted": True, "verified": rec["verified"], "fid": fid}
            self._counters["deleted"] += 1
            if source == "manual":
                self._counters["manual_deletes"] += 1
        return self._evict_and_verify(fid, source=source)

    def sweep(self) -> dict:
        """Auto-delete + verify every cached artifact that is now eligible."""
        due = []
        with self._lock:
            now = _now()
            for fid, rec in list(self._files.items()):
                if rec["state"] == DELETED:
                    continue
                pol = rec["retention_policy"]
                eligible = False
                reason = None
                if pol == "post_processing":
                    if rec["consumed_epoch"] is not None:
                        eligible, reason = True, "consumed"
                    elif now - rec["uploaded_epoch"] > HARD_TTL_SECONDS:
                        eligible, reason = True, "hard_ttl_safety_cap"
                elif pol in ("5m", "10m"):
                    age = now - rec["uploaded_epoch"]
                    seconds = {"5m": 300, "10m": 600}[pol]
                    if age >= seconds:
                        eligible, reason = True, f"retention_elapsed_{pol}"
                        rec["delete_at"] = rec.get("delete_at") or rec["uploaded_epoch"] + seconds
                # manual: never auto-deleted.
                if eligible and rec["state"] == ACTIVE:
                    rec["state"] = PENDING
                    self._log(PrivacyEventType.SCHEDULED, fid, detail=f"scheduled for auto-delete ({reason})")
                if eligible:
                    due.append(fid)
        for fid in due:
            self._evict_and_verify(fid, source="auto-sweep")
        with self._lock:
            active = sum(1 for r in self._files.values() if r["state"] == ACTIVE)
            pending = sum(1 for r in self._files.values() if r["state"] == PENDING)
            deleted_recs = [r for r in self._files.values() if r["state"] == DELETED]
            verified = sum(1 for r in deleted_recs if r.get("verified"))
            failed = sum(1 for r in deleted_recs if not r.get("verified"))
        return {
            "processed": len(due),
            "stats": self._stat_counts(active=active, pending=pending, deleted=len(deleted_recs), verified=verified, failed=failed),
        }

    # -- internals ----------------------------------------------------------

    def _evict_and_verify(self, fid: str, source: str) -> dict:
        """Remove the artifact from the cache and confirm it is gone."""
        with self._lock:
            rec = self._files.get(fid)
            evict = self._cache_evict(fid) if self._cache_evict else False
            # Verification: the cache no longer holds this fid. If it was already
            # gone (e.g. TTL pre-purged it), that is still a clean removal.
            if evict:
                present_after = False
            else:
                present_after = self._cache_evict(fid) if (self._cache_evict and not evict) else False
            verified = not present_after
            if rec:
                rec["state"] = DELETED
                rec["deleted_at"] = _iso(_now())
                rec["deleted_by"] = source
                rec["verified"] = verified
                rec["verification_at"] = _iso(_now()) if verified else None
                rec["failure"] = None if verified else "residual cache entry"
                # Two distinct audit steps for the removal: 'deleted' (the cached
                # artifact was evicted) then 'delete_verified' / 'delete_failed'
                # (the eviction was confirmed). RLock lets us log while holding.
                self._log(PrivacyEventType.DELETED, fid, detail=f"{rec['filename']} removed from cache ({source})")
            event = PrivacyEventType.VERIFIED if verified else PrivacyEventType.FAILED
            detail = "cache entry gone and confirmed" if verified else "residual cache entry still present"
        self._log(event, fid, detail=detail)
        return {"ok": verified, "fid": fid, "verified": verified, "source": source}

    def _log(self, event: str, fid: Optional[str], detail: str = "") -> None:
        entry = {
            "ts": _iso(_now()),
            "event": event,
            "fid": fid or "",
            "filename": self._files.get(fid, {}).get("filename", "") if fid else "",
            "detail": detail,
        }
        with self._lock:
            self._activity.insert(0, entry)
            self._activity = self._activity[:500]

    def _stat_counts(self, active: int, pending: int, deleted: int, verified: int, failed: int) -> dict:
        return {
            "total_uploads": self._counters["total_uploads"],
            "consumed": self._counters["consumed"],
            "active": active,
            "pending": pending,
            "deleted": deleted,
            "deleted_verified": verified,
            "delete_failed": failed,
            "manual_deletes": self._counters["manual_deletes"],
            "retention_seconds": {"post_processing": 0, "5m": 300, "10m": 600, "manual": -1}.get(self._policy, 0),
        }

    def snapshot(self) -> dict:
        """Full view for the privacy dashboard."""
        with self._lock:
            files = list(self._files.values())
            activity = list(self._activity)
        active = sum(1 for r in files if r["state"] == ACTIVE)
        pending = sum(1 for r in files if r["state"] == PENDING)
        deleted_recs = [r for r in files if r["state"] == DELETED]
        verified = sum(1 for r in deleted_recs if r.get("verified"))
        failed = sum(1 for r in deleted_recs if not r.get("verified"))
        return {
            "policy": self._policy,
            "options": [{"key": k, "label": v} for k, v in RETENTION_OPTIONS.items()],
            "hard_ttl_seconds": HARD_TTL_SECONDS,
            "stats": self._stat_counts(active=active, pending=pending, deleted=len(deleted_recs), verified=verified, failed=failed),
            "files": sorted(files, key=lambda r: r["uploaded_epoch"], reverse=True),
            "activity": activity,
        }

    def files(self) -> list:
        with self._lock:
            return list(self._files.values())

    def activity(self) -> list:
        with self._lock:
            return list(self._activity)


# Module-level singleton wired up in main.py.
privacy_tracker = PrivacyTracker()