"""Direct lifecycle test of AI Data Auto-Deletion against the REAL singletons
main.py wires up (_file_cache, privacy_tracker). Replicates /api/files/scan's
register call, /api/ai/chat's mark_consumed call, then sweep + verify. No HTTP,
no provider, no TestClient lifespan.
"""
import io, sys, time
import main as M
import privacy as P

pass_all = []
def check(name, cond, detail=None):
    pass_all.append(cond)
    print(("PASS  " if cond else "FAIL  ") + name + (f"  -> {detail}" if detail else ""), flush=True)

s = M.privacy_tracker
print("="*64, flush=True)

# ---- A) upload a text document (mirrors scan endpoint) ----
rec = M.scan_file("q3_report.txt", b"Quarterly revenue summary, north region, budget 220k.\nNext quarter forecast 310k.\n", redact=True)
assert rec["sanitized_available"], rec
fid = M._cache_put({
    "filename": rec["filename"], "sanitized": rec["sanitized"],
    "risk_score": rec["risk_score"], "classification": rec["classification"],
    "pii_count": rec["pii_count"], "secret_count": rec["secret_count"],
})
s.register({"fid": fid, "filename": rec["filename"], "extension": rec["extension"],
            "size_bytes": rec["size_bytes"], "sha256": rec["sha256"],
            "classification": rec["classification"], "risk_score": rec["risk_score"],
            "risk_level": rec["risk_level"]})
r = [f for f in s.files() if f["fid"] == fid][0]
print("A) document tracked", flush=True)
check("fid returned & cached in real _file_cache", fid in M._file_cache, fid)
check("state=ACTIVE on upload", r["state"] == "ACTIVE", r["state"])
check("retention=post_processing", r["retention_policy"] == "post_processing", r["retention_policy"])
check("delete_at is None (not time-elapsed)", r["delete_at"] is None)

# ---- B) image upload -> never retained ----
png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f00050001810f0fbd0000000049454e44ae426082")
rec2 = M.scan_file("pixel.png", png, redact=False)
print("PASS  image has no sanitized text" if not rec2["sanitized_available"] else "FAIL  image unexpectedly has text", flush=True)
s.register({"fid": "", "filename": rec2["filename"], "extension": rec2["extension"],
            "size_bytes": rec2["size_bytes"], "sha256": rec2["sha256"],
            "classification": rec2["classification"], "risk_score": rec2["risk_score"],
            "risk_level": rec2["risk_level"]})
img = [f for f in s.files() if f["filename"] == "pixel.png"][0]
print("B) image tracked as never-retained", flush=True)
check("image state=DELETED already", img["state"] == "DELETED", img["state"])
check("image verified=True", img["verified"] is True)
check("image deleted_by=nothing_retained", img["deleted_by"] == "nothing_retained", img["deleted_by"])

# ---- C) chat consumes doc -> mark_consumed ----
print("C) mark consumed (exact call /api/ai/chat line 1355 makes)", flush=True)
s.mark_consumed(fid)
r = [f for f in s.files() if f["fid"] == fid][0]
check("consumed_at set", r["consumed_at"] is not None)
check("state=PENDING now (scheduled for auto-delete)", r["state"] == "PENDING", r["state"])

# ---- D) sweep -> delete + verify against real cache ----
print("D) sweep deletes + verifies against real cache", flush=True)
res = s.sweep()
check("sweep processed the consumed file", (res.get("processed") or 0) >= 1, res.get("processed"))
check("no delete failures", res["stats"]["delete_failed"] == 0, res["stats"]["delete_failed"])
r = [f for f in s.files() if f["fid"] == fid][0]
check("state=DELETED after sweep", r["state"] == "DELETED", r["state"])
check("deleted_by=auto-sweep", r["deleted_by"] == "auto-sweep", r["deleted_by"])
check("verified=True (no residual in cache)", r["verified"] is True, f"failure={r.get('failure')}")
check("verification_at set", r["verification_at"] is not None)
check("REAL _file_cache no longer holds fid", fid not in M._file_cache)

# ---- E) activity log full lifecycle (append-only, ordered) ----
acts = s.activity()
evs = [a for a in acts if a["fid"] == fid]
have = {a["event"] for a in evs}
print("E) activity log events:", [a["event"] for a in reversed(evs)], flush=True)
for k in ["uploaded", "consumed", "deleted", "delete_verified"]:
    check(f"activity has '{k}'", k in have)
# post_processing consume path: mark_consumed sets PENDING directly, so no
# separate scheduled_for_deletion event here — that fires via the sweep/ACTIVE path.
# _activity is stored newest-first (insert(0)), so assert that top-down order.
order = [a["event"] for a in evs]
check("activity newest-first (delete_verified on top)", order == ["delete_verified", "deleted", "consumed", "uploaded"], order)
check("events oldest-first are chronological", list(reversed(order)) == ["uploaded", "consumed", "deleted", "delete_verified"])

# ---- F) manual delete-now on a second upload (idempotent) ----
rec3 = M.scan_file("report_b.txt", b"PII: 555-12-3456 . BEGIN PRIVATE KEY begin key", redact=True)
fid2 = M._cache_put({"filename": rec3["filename"], "sanitized": rec3["sanitized"],
    "risk_score": rec3["risk_score"], "classification": rec3["classification"],
    "pii_count": rec3["pii_count"], "secret_count": rec3["secret_count"]})
s.register({"fid": fid2, "filename": rec3["filename"], "extension": rec3["extension"],
    "size_bytes": rec3["size_bytes"], "sha256": rec3["sha256"],
    "classification": rec3["classification"], "risk_score": rec3["risk_score"],
    "risk_level": rec3["risk_level"]})
print("F) manual Delete now", flush=True)
d1 = s.delete_now(fid2, source="manual")
check("delete_now ok=True + verified", d1["ok"] is True and d1["verified"] is True, d1)
check("manual delete recorded as manual", [f for f in s.files() if f["fid"]==fid2][0]["deleted_by"] == "manual")
d2 = s.delete_now(fid2, source="manual")
check("delete_now idempotent (already_deleted)", d2["already_deleted"] is True, d2)
check("manual_deletes counter=1", s._counters["manual_deletes"] == 1, s._counters["manual_deletes"])

# ---- G) retention policy switching ----
print("G) retention policy changes", flush=True)
ok = s.set_policy("manual")
check("set_policy('manual') accepted", ok and s.policy == "manual", s.policy)
ok = s.set_policy("bogus")
check("set_policy('bogus') rejected, policy unchanged", ok is False and s.policy == "manual", s.policy)
s.set_policy("post_processing")

# ---- H) hard-TTL safety cap: unconsumed old file swept + scheduled_for_deletion ----
rec4 = M.scan_file("abandoned.txt", b"no one ever asked the AI to use this file", redact=True)
fid3 = M._cache_put({"filename": rec4["filename"], "sanitized": rec4["sanitized"],
    "risk_score": rec4["risk_score"], "classification": rec4["classification"],
    "pii_count": rec4["pii_count"], "secret_count": rec4["secret_count"]})
s.register({"fid": fid3, "filename": rec4["filename"], "extension": rec4["extension"],
    "size_bytes": rec4["size_bytes"], "sha256": rec4["sha256"],
    "classification": rec4["classification"], "risk_score": rec4["risk_score"],
    "risk_level": rec4["risk_level"]})
# Simulate: file uploaded LONG ago and never consumed -> exceeds HARD_TTL safety cap.
r = [f for f in s.files() if f["fid"] == fid3][0]
r["uploaded_epoch"] = time.time() - (P.HARD_TTL_SECONDS + 60)
print("H) hard-TTL safety-cap sweep of an abandoned file", flush=True)
res = s.sweep()
check("abandoned file swept", fid3 not in M._file_cache)
ev4 = [a["event"] for a in s.activity() if a["fid"] == fid3]
for k in ["scheduled_for_deletion", "deleted", "delete_verified"]:
    check(f"hard-TTL path logs '{k}'", k in ev4)
r3 = [f for f in s.files() if f["fid"] == fid3][0]
check("abandoned file DELETED + verified", r3["state"] == "DELETED" and r3["verified"] is True)

print("="*64, flush=True)
fails = sum(1 for p in pass_all if not p)
print(f"RESULT: {len(pass_all)-fails}/{len(pass_all)} checks passed", flush=True)
sys.exit(0 if not fails else 1)
