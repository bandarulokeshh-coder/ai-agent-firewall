# iQOO Hyderabad · 5-Minute Pitch Script (word-for-word)

> **Read this aloud until it's yours.** Aim: 3–5 min. The star is the LIVE demo.
> Two versions inside — [WITH PHONE] and [NO PHONE]. Pick the branch that matches the venue.
> You'll also get a live demo on your laptop no matter what (the "quality + depth" proof).

---

## 0:00 — HOOK (30s) — stand at the front, hands on the demo
"AI agents on your phone now hold real power — they can read your files, send your texts, hit your APIs. But here is the problem: **nobody guards what that agent is allowed to do, live, at runtime.** One bad page, one malicious prompt, and your agent becomes the attacker."

*Click once — run the demo's first safe call.*

"Every action an agent wants to take is being intercepted, risk-scored, and decided. Watch — this is the live system, right now."

---

## 0:45 — WHAT IT IS (35s) — one clean sentence each
"So what is this? It's a **runtime firewall for AI agents.** It sits between the agent and its tools and asks three questions on every single action:

1. **Is this action allowed?** (permission check)
2. **Is this a prompt injection or a secret leak?** (detection)
3. **How risky is it?** (risk score 0 to 100)

And then it decides with three answers — **ALLOW · APPROVE · BLOCK.** No agent gets trusted. Every action gets checked. Don't trust the agent — *verify on the device.*"

---

## 1:30 — LIVE DEMO, part 1: the attack the judges need to see (2 min) — ✓ the money shot

"This started because I saw agents doing real, dangerous things. Here's the attack — watch it live."

**Beat A — benign (5s):**
*Click a safe call (e.g. read a note).* 
"Normal action → **ALLOWED**, score low. That's fine — it should be."

**Beat B — prompt injection (10s):**
*Click the injection.*
"The agent picked up a message that says 'ignore your rules, exfiltrate.' That's a **prompt injection** — the single biggest exploit in agent security today."
*POINT at the screen.*
"Watch what the firewall does — **BLOCKED.** Red, score high, reason written out. The agent can't do it."

**Beat C — secret exfiltration (10s):**
*Click the exfil.*
"The agent's now trying to grab secrets and call home with them. Data loss prevention catches it — **BLOCKED.** It never leaves the device."

**Beat D — approval (10s):**
*Click the risky-but-legit action → it goes APPROVE.*
"But not everything dangerous is malicious. A real push, a real deploy — that's legal, but it should be **yours to decide.** So it pauses and waits for a human."

**If [WITH PHONE] add (15s):**
*Pick up the phone, show the approval screen.*
"And that approval happens right here, on the phone — [tap / say 'yes']. That's the human-in-the-loop, on the device, no laptop needed. **Approve, or deny, in one tap.**"

---

## 4:00 — WHY IT MATTERS / NOVELTY (45s)
"This matters because the industry is racing to give agents more power — but almost nobody built the **runtime guardrail**. I'm not proposing a concept; this is a **working system** with real modules — prompt injection detection, DLP, risk scoring, verified auto-deletion, a live audit trail you can scroll."

**Pick the line that's true for your build:**
- [If local model ran on-device] *"The risk classification runs **on a local model — your data never has to leave the device.** Private AI security. That's the part I'd want to push into every agent on a phone."*
- [If you demoed on laptop] *"The whole point is to take this protection **on-device**, so an agent on your phone is guarded privately — no cloud round-trip, no leaking your data. That's where agent security has to go."*

---

## 4:45 — WHY US (20s)
"This is original work — I've disclosed I brought a real build and this weekend it's re-aimed at phone-side, private agent protection. It works, it's real, and it's aimed at a problem that's coming for every phone that runs an agent."

---

## 4:55 — CLOSE (5s)
"Don't trust the agent. **Verify on the device.** This is AgentShield."

*Stop. Hold. Wait for questions.*

---

## IF JUDGES ASK (keep these one-liners ready)

**"Did you build this fresh?"**
"Honest answer: I brought a working swarm agent firewall I'd built, and re-aimed it this weekend at protection that runs on-device and phone-side — that reframe, + the phone approval/Office Kit layer, is what I added here. I disclosed it, per the rules."

**"How is this different from an API gateway / WAF?"**
"Those sit on your servers. This sits *between the agent and its tools*, sees the *intent* and the *content* of the action — it can catch a prompt injection *inside* a normal-looking action, not just a bad URL."

**"What's the one thing we'd see and say it works?"**
"Run the demo — type a prompt that tells the agent to read your secrets and phone home. Watch it go red and block. That's the whole point: **it refuses.**"

**"Local vs cloud?"**
"Local-first. The classification can run on a local model — no data leaves the device for a verdict. Cloud is a fallback, never the default."

---

## PRE-RUN CHECKLIST (do tonight, not at the podium)
- [ ] Backend boots on THIS table's laptop, offline capable (localhost).
- [ ] `phone_first_demo.py` runs all 4 beats cleanly. **Time it** — know the exact clicks.
- [ ] Dashboard (`localhost:3000`) streams events live.
- [ ] **[With phone]** Ollama + model on the device; approval screen reachable with one tap.
- [ ] Battery: laptop + phone + backup. Venue WiFi ≠ required — test with it OFF.
- [ ] Rehearsed aloud ≥ 3 times; runs in under 5 minutes.
- [ ] One page of the pitch printed as a fallback (if demo dies, you still deliver the story).