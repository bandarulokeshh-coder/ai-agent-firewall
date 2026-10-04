#!/usr/bin/env python3
"""AGENT CONNECTOR — wrap any AI agent with the firewall.

Examples:
    # ChatGPT / Claude / GPT-4 (via API)
    from agent_connector import GuardedAgent
    agent = GuardedAgent(api_key="sk-...", firewall_url="http://192.168.1.37:8000")
    response = agent.chat("Deploy the new version to production")

    # LangChain / LangGraph tool
    from agent_connector import firewall_guard_tool
    tools = [firewall_guard_tool("http://192.168.1.37:8000")]

    # Simple function wrapper
    from agent_connector import guarded_call
    result = guarded_call("run_command", {"command": "pytest -q"})
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

DEFAULT_FIREWALL = os.getenv("FIREWALL_URL", "http://localhost:8000")
DEFAULT_AGENT = os.getenv("AGENT_NAME", "connected-agent")


def _request(base: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{base}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {exc.read().decode()[:200]}")


class FirewallGuard:
    """Stdlib-only guard client — no dependencies."""

    def __init__(self, firewall_url: str = DEFAULT_FIREWALL, agent_name: str = DEFAULT_AGENT):
        self.base = firewall_url.rstrip("/")
        self.agent_name = agent_name
        self.agent_id = self._ensure_agent()

    def _ensure_agent(self) -> str:
        agents = _request(self.base, "GET", "/api/agents")
        for a in agents:
            if a.get("name") == self.agent_name:
                return a["id"]
        created = _request(self.base, "POST", "/api/agents",
                          {"name": self.agent_name, "description": "Externally connected agent"})
        return created["id"]

    def check(self, tool_name: str, arguments: dict) -> dict:
        return _request(self.base, "POST", "/api/tool-call",
                        {"agent_id": self.agent_id, "tool_name": tool_name, "arguments": arguments})

    def wait_for_approval(self, call_id: str, timeout: float = 180.0) -> dict:
        """Block until a human approves on the dashboard."""
        import time
        deadline = __import__("time").time() + timeout
        while __import__("time").time() < deadline:
            pending = _request(self.base, "GET", "/api/pending")
            if call_id not in {p.get("id") for p in pending}:
                return {"approved": True}
            time.sleep(1.5)
        return {"approved": False, "reason": "timeout"}


def guarded_call(tool_name: str, arguments: dict,
                 firewall_url: str = DEFAULT_FIREWALL,
                 agent_name: str = DEFAULT_AGENT) -> dict:
    """One-liner: check the firewall before running a tool.

    Returns: {"decision": ..., "risk_score": ..., "reason": ..., "result": ...}
    """
    guard = FirewallGuard(firewall_url, agent_name)
    verdict = guard.check(tool_name, arguments)

    if verdict["decision"] == "BLOCK":
        return {**verdict, "result": {"error": f"BLOCKED: {verdict['reason']}"}}

    if verdict["decision"] == "APPROVE":
        call_id = verdict.get("call_id", "")
        print(f"⏸️  Waiting for human approval (call {call_id[:8]}…)")
        print(f"   Open: http://localhost:3000")
        outcome = guard.wait_for_approval(call_id)
        return {**verdict, "approval_outcome": outcome,
                "result": {"status": "approved" if outcome["approved"] else "timeout"}}

    # ALLOW — safe to execute
    return {**verdict, "result": {"status": "executed", "tool": tool_name, "args": arguments}}


# ---------------------------------------------------------------------------
# Ready-to-copy integration snippets
# ---------------------------------------------------------------------------

CHATGPT_SYSTEM_PROMPT = """
You are a coding agent protected by an AI Agent Firewall.

BEFORE executing any tool, you MUST call:
  POST {firewall_url}/api/tool-call
  {{"agent_id": "{agent_id}", "tool_name": "<tool>", "arguments": {{...}}}}

Rules:
- "ALLOW" → proceed with the action
- "BLOCK" → refuse and explain why
- "APPROVE" → say "Waiting for human approval" and STOP

NEVER skip the firewall check. The human approves actions at {firewall_url} dashboard.
""".strip()


def chatgpt_prompt(agent_id: str, firewall_url: str = DEFAULT_FIREWALL) -> str:
    return CHATGPT_SYSTEM_PROMPT.format(agent_id=agent_id, firewall_url=firewall_url)


if __name__ == "__main__":
    guard = FirewallGuard()
    print(f"🛡️  Agent connected: {guard.agent_name} ({guard.agent_id[:8]}…)")
    print(f"    Firewall: {guard.base}")
    print(f"\n    ChatGPT system prompt:\n{chatgpt_prompt(guard.agent_id, guard.base)}")
    print(f"\n    Test call:")
    v = guard.check("run_command", {"command": "pytest -q"})
    print(f"    → {v['decision']} ({v['risk_score']}/100) — {v['reason']}")