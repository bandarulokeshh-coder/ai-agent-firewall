# iQOO Hackathon 2026 · Hyderabad City Battle — Build Plan
> Solo · Students bucket · 30-hour phone-first
> Prep file: **commit to the "private on-device AI-agent firewall" pitch, polish, and film the 25% you're missing.**

---

## The pitch (60 seconds, judges)
> *"AI agents on your phone now hold real tool access — calls, texts, contacts, files, APIs. But nobody guards them at runtime. This is the firewall: every action an agent wants to take is intercepted, analyzed, and risk-scored **on device**, then allowed, approved by you, or blocked. No agent gets trusted. No data has to leave your phone."*

Track: **Developer Tools** or **Open Innovation** (wildcard). Best fit: Open Innovation.

---

## THE JUDGING RUBRIC — where your marks come from (100%)

| Criterion | Weight | Your build plan |
|---|---|---|
| End product quality | **30%** | Already strong — real, working, robust |
| Novelty and impact | **20%** | The on-device / private-security angle IS the novelty |
| **Creative phone use** (camera, voice, on-device AI) | **15%** | **❌ MISSING — this is priority #1 to add** |
| Technical depth | **15%** | Already strong — real architecture, local LLM |
| **Office Kit usage** (phone↔laptop bridge) | **10%** | **❌ MISSING — priority #2** |
| Demo & presentation | **10%** | Script it — 3–5 min, demo on the phone |

> You already bank ~45% (quality 30% + depth 15%) if it works live. The whole fight is the
> **25% split between creative-phone-use and Office Kit.** Everything below aims at that.

---

## Existing modules → what they already win you

These are DONE and are your foundation. Don't rebuild them.

| Module (file) | Does | Wins you |
|---|---|---|
| `security/detectors.py` | PII, secrets, **prompt injection**, content classification | Quality + detection story |
| `security/risk_engine.py` | Transparent 0–100 score + reasons | Technical depth (explainable) |
| `security/redaction.py` | Sanitizes data before it reaches any AI provider | Privacy / "novelty" |
| `security/file_scanner.py` | Real file extract + scan + auto-delete temp | Breadth |
| `providers.py` (`OllamaProvider`) | **Local Ollama, default localhost:11434** | **Local-model brownie points** |
| `main.py` (line ~552) | **Local LLM prompt-injection classifier** (qwen2.5:7b) **already wired into tool-call path**, regex fallback | **The on-device AI hook — already live** |
| `privacy.py` | **Verified auto-deletion** (HARD_TTL 600s, auditable delete) | Novelty & impact (you cannot delete what you never store) |
| Frontend dashboard | Live WebSocket activity, approval queue, risk charts | End-product quality (visible) |

---

## The 25% — STATUS AS OF PREP (all four built & tested on the dev machine)

### 🔴 Feature 1 — Voice approval on device (creative phone use · the big one) ✅ DONE
Goal: the 🟡/🔴 human-approval step is confirmed by **voice or tap on the phone**, not a laptop button.
- **Built:** `backend/static/phone.html` served by FastAPI at **`GET /phone`** — mobile-first queue, big ✓ APPROVE / ✕ DENY cards, and **on-device voice via Web Speech API** (say "approve"/"deny"/"yes"/"no" — no cloud, works in iQOO Chrome). Hands-free focus mode: first voice activation arms it, then it acts on the top pending action.
- **Novelty line:** *"Approve a risky agent action by just saying 'yes' to your phone."*
- **To demo:** open `http://<laptop-ip>:8000/phone` on the iQOO, run `phone_first_demo.py`, approve Beat 4 by voice.

### 🔴 Feature 2 — "Build route" via Office Kit (the 10%) ✅ CODE DONE — needs 2nd machine to demo
Goal: Red Light (phone-only) blocks still escalate to the laptop for heavy compute **through Office Kit** — proving the bridge.
- **Built:** `detect_prompt_injection()` now escalates to a second Ollama: on local model error, OR a borderline verdict (confidence 40–75), the verdict is re-requested from the escalation host and the reason records **"Office Kit bridge"**.
- **Configure for the event:** `export OLLAMA_ESCALATION_HOST=http://<laptop-ip>:11434` on the phone-side server (or in the run command). Empty = bridge off (safe default).
- **Bonus fix:** the injection classifier no longer hardcodes the uninstalled `qwen2.5:7b` — it resolves the first installed model at runtime (currently `gemma4:e4b`), so the **on-device AI hook actually fires** (verified: real LLM verdicts in decision reasons).

### 🟠 Feature 3 — Agent's *context* feeds the risk score ✅ DONE
Goal: judge-beatable "creative phone use" — the firewall considers where the agent is:
- **Built:** `_context_source_risk()` in `main.py` — `ToolCallRequest.context.source` now scores the call: untrusted sources (camera +30, voice/mic +25, clipboard/message/sms +20, mail/web/notification/barcode +15, unknown +10) raise the risk score with a transparent reason; trusted (file/user/keyboard/local) add nothing.
- **Verified:** `npm test` = 0/ALLOW → with `context.source=camera` = 30/ALLOW.

### 🟠 Feature 4 — Narrate the privacy auto-deletion ✅ ALREADY BUILT (privacy.py + /privacy dashboard)
Goal: turn `privacy.py`'s verified auto-deletion into a **demo moment**, not background.
- `privacy.py` (RLock, auditable delete-verify) + `/api/privacy*` + frontend `/privacy` page exist. Rehearse the upload → consumed → verified-deleted narration for judges; no new code needed.

---

## The 30-hour schedule (solo — protect these blocks)

**Friday evening → Saturday 10:00** — BEFORE the clock starts:
- Install Ollama + `qwen2.5:7b` on both laptop AND iQOO (test local classification works on device).
- Get `phone_first_demo.py` green against the backend on the phone's localhost.
- Render a clean one-screen phone dashboard (approve/deny + live feed) — **no laptop-only UI on stage.**

**Saturday (active hacking):**
- **0–3h:** Feature 1 (voice/tap approval on phone). This is 15% of the score. Nail it first.
- **3–6h:** Feature 2 (Office Kit escalation) — the 10%.
- **6–9h:** Feature 3 + Feature 4 (context scoring + auto-delete demo). Sleep can't happen until these two exist in some form.
- **9–12h (Red Light, phone-only):** Refine the phone approval surface + record cinemagraphic demo clips (the phone IS the product shot).
- **Rest block:** sleep. Don't touch the thing.
- **Next morning:** evaluation round 1 — make scored checkpoints pass cleanly.
- **Last 5h:** polish the 3–5 min pitch; rehearse the exact attack story; tidy repo.

**Awards:** Top 6 advance → **Bengaluru Grand Finale, Oct 9–11.**

---

## Do-NOT-do list (solo kill-switch)
- ❌ No new languages/frameworks. Everything in FastAPI + the existing frontend.
- ❌ No networking with a remote agent/laptop on stage — if WiFi fails, the demo must run **fully local** (localhost). Test offline.
- ❌ Don't rebuild detection. It works. Add, don't rename.
- ❌ Don't charge the phone layout mid-build. Fix the approval screen early, keep it.

---

## If they ask "did you build this fresh?" 
Be honest and confident: *"I brought a security project I'd built and re-aimed it at phone-side agent protection. The local-model classification and Office Kit bridging are what I added this weekend."* Judges reward depth + honesty; the competition's terms allow reusing prior work.

---
**One-liner for the judge:**
> Don't trust the agent. **Verify on the device.** 🛡️