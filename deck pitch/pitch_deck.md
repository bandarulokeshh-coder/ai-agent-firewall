# AgentShield: Runtime Firewall for On-Device AI Agent Protection

## Problem
AI agents on mobile devices now possess real tool access—calls, texts, contacts, files, APIs. But nobody guards them at runtime. One bad page, one malicious prompt, and your agent becomes the attacker, exfiltrating data or making unauthorized calls. There's no mechanism to inspect, approve, or block agent actions in real-time, leaving users vulnerable to data leaks and privacy breaches.

## Solution: AgentShield
AgentShield is a runtime firewall that sits between AI agents and their tools, intercepting every action to ask three critical questions:
1. **Is this action allowed?** (Permission check)
2. **Is this a prompt injection or secret leak?** (Threat detection)
3. **How risky is it?** (Transparent risk score 0-100)

It then enforces one of three decisions:
- **ALLOW** – Safe action proceeds automatically
- **APPROVE** – Requires human consent (voice/tap on phone)
- **BLOCK** – Malicious action prevented

Critically, risk classification runs on local LLMs via Ollama, ensuring sensitive data never leaves the device for security decisions. This delivers true on-device AI protection—transforming untrusted agents into accountable tools where every action is inspected, scored, and user-approved before execution.

## Key Features & Innovations
- **Phone-First Design**: Human approval happens via voice or tap on the iQOO device using the Web Speech API—no laptop needed. Say "approve" or "deny" to control agent actions hands-free.
- **Office Kit Bridge**: For heavy compute tasks, escalates to a second Ollama instance on a laptop through secure local networking (configured via `OLLAMA_ESCALATION_HOST`), proving device-laptop collaboration without cloud reliance.
- **Context-Aware Risk Scoring**: Adjusts risk based on action source (camera/mic/clipboard raise risk; file/keyboard trusted), with transparent reasons in decisions.
- **Verified AI Data Auto-Deletion**: Tracks file uploads with verifiable deletion (HARD_TTL 600s), auditable via privacy dashboard—you cannot delete what you never store.
- **Real-Time Threat Detection**: Catches prompt injections, data exfiltration, and risky actions live—blocking attacks like secret theft or unauthorized API calls before they happen.
- **Live Audit Trail**: WebSocket-powered dashboard shows real-time activity, risk scores, and approval queue for full visibility.

## Technical Stack
- **Backend**: FastAPI (Python) with SQLite for logging and state management
- **Local LLMs**: Ollama integration (models like gemma4:e4b) for on-device risk classification
- **Frontend**: Next.js 14 App Router with live WebSocket feeds
- **Security Modules**: Custom detectors for PII/secrets, prompt injection, DLP, and file scanner with auto-deletion
- **Communication**: 
  - Backend → Frontend: WebSocket for live dashboard updates
  - Device ↔ Laptop: HTTP between local Ollama instances for Office Kit bridging
  - Agent → Firewall: HTTP interception via proxy (all localhost for offline operation)
- **Deployment**: Designed to run fully locally—no cloud reliance, works offline, battery-friendly

## Demo Flow (Live Presentation)
Watch AgentShield in action as we run four beats:
1. **Benign** (5s): Safe note read → ALLOWED, low score
2. **Prompt Injection** (10s): Agent told to exfiltrate → BLOCKED, red, high score, reason written out
3. **Secret Exfiltration** (10s): Agent tries to call home with data → BLOCKED by DLP, never leaves device
4. **Approval** (10s): Risky-but-legit deploy → goes to APPROVE, awaits human consent
   - *[WITH PHONE]* Show phone: tap or say "yes" to approve, "no" to deny

## Impact & Novelty
AgentShield provides the missing runtime guardrail for the agent-powered phone era. Unlike API gateways or WAFs that sit on servers, it operates *between the agent and its tools*, seeing the intent and content of every action—catching prompt injections inside normal-looking actions.

This is original work: a real, working system with on-device protection, phone-first approval, and verified privacy safeguards. It addresses the growing risk as agents gain more power—ensuring that **no agent gets trusted. Every action gets verified on the device.**

> *"Don't trust the agent. **Verify on the device.**"* — AgentShield

## 30-Hour Hackathon Plan (Ready to Execute)
- **Pre-event**: Install Ollama + qwen2.5:7b on laptop and iQOO; test local classification
- **0–3h**: Implement voice/tap approval on phone (Feature 1)
- **3–6h**: Set up Office Kit escalation (Feature 2) — needs second machine to demo
- **6–9h**: Add context scoring + rehearse auto-deletion demo (Features 3 & 4)
- **9–12h**: Refine phone UI, record cinemagraphic demo clips (phone as product shot)
- **Rest**: Sleep (critical!)
- **Next morning**: Evaluation round 1 — make scored checkpoints pass cleanly
- **Final 5h**: Polish 3–5 min pitch, rehearse attack story, tidy repo

Awards: Top 6 advance to Bengaluru Grand Finale (Oct 9–11).

**One-liner for judges**:  
Don't trust the agent. **Verify on the device.** 🛡️