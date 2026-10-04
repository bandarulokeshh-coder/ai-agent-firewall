#!/usr/bin/env python3
"""Demo script showcasing the upgraded firewall features.

New features:
- Rate limiting with token buckets
- Advanced policy engine with templates
- Real-time alerting system
- Audit export (CSV/JSON)
- Compliance reporting
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"


def demo_rate_limiting():
    """Demonstrate rate limiting in action."""
    print("\n" + "=" * 60)
    print("📊 RATE LIMITING DEMO")
    print("=" * 60)

    agent_id = "rate-test-agent"

    # Create agent
    requests.post(f"{API_BASE}/api/agents", json={"name": agent_id})

    # Check initial rate limit status
    resp = requests.get(f"{API_BASE}/api/rate-limit/{agent_id}")
    status = resp.json()
    print(f"\n🔹 Initial Rate Limit Status:")
    print(f"   Tokens: {status['rate_limit']['tokens_remaining']}/{status['rate_limit']['max_tokens']}")
    print(f"   Calls this hour: {status['rate_limit']['calls_this_hour']}/{status['rate_limit']['max_calls_per_hour']}")

    # Make some calls
    print(f"\n🔹 Making 5 tool calls...")
    for i in range(5):
        requests.post(f"{API_BASE}/api/tool-call", json={
            "agent_id": agent_id,
            "tool_name": "web_search",
            "arguments": {"query": f"test query {i}"}
        })
        time.sleep(0.2)

    # Check updated status
    resp = requests.get(f"{API_BASE}/api/rate-limit/{agent_id}")
    status = resp.json()
    print(f"\n🔹 After 5 calls:")
    print(f"   Tokens: {status['rate_limit']['tokens_remaining']}/{status['rate_limit']['max_tokens']}")
    print(f"   Calls this hour: {status['rate_limit']['calls_this_hour']}")


def demo_policy_engine():
    """Demonstrate custom policy rules."""
    print("\n" + "=" * 60)
    print("🛡️  POLICY ENGINE DEMO")
    print("=" * 60)

    # List default policies
    resp = requests.get(f"{API_BASE}/api/policies")
    rules = resp.json()["rules"]
    print(f"\n🔹 Default Policy Rules: {len(rules)}")
    for rule in rules[:3]:
        print(f"   • {rule['name']} (priority: {rule['priority']}) → {rule['action']}")

    # Create custom policy
    print(f"\n🔹 Creating custom policy: 'block_weekend_deploys'")
    custom_rule = {
        "name": "block_weekend_deploys",
        "conditions": {
            "tool_name": "deploy",
            "time_range": {"start": "00:00", "end": "23:59"}
        },
        "action": "BLOCK",
        "priority": 95,
    }
    requests.post(f"{API_BASE}/api/policies", json=custom_rule)
    print("   ✅ Policy created")

    # Enable compliance template
    print(f"\n🔹 Enabling compliance policy template...")
    requests.post(f"{API_BASE}/api/policies/compliance_mode/enable")
    print("   ✅ Compliance template enabled")


def demo_audit_export():
    """Demonstrate audit export and compliance reporting."""
    print("\n" + "=" * 60)
    print("📋 AUDIT & COMPLIANCE DEMO")
    print("=" * 60)

    # Generate compliance report
    print(f"\n🔹 Generating 30-day compliance report...")
    resp = requests.get(f"{API_BASE}/api/audit/compliance?period_days=30")
    report = resp.json()

    print(f"\n   Summary:")
    print(f"   • Total calls: {report['summary']['total_calls']}")
    print(f"   • Blocked: {report['summary']['blocked']}")
    print(f"   • Block rate: {report['summary']['block_rate']}%")

    print(f"\n   Risk Distribution:")
    for level, count in report['risk_distribution'].items():
        print(f"   • {level}: {count}")

    if report['top_blocked_reasons']:
        print(f"\n   Top Blocked Reasons:")
        for item in report['top_blocked_reasons'][:3]:
            print(f"   • {item['reason']}: {item['count']}x")

    # Export CSV
    print(f"\n🔹 Exporting audit logs to CSV...")
    resp = requests.get(f"{API_BASE}/api/audit/export?format=csv&decision=BLOCK")
    if resp.status_code == 200:
        lines = resp.text.strip().split('\n')
        print(f"   ✅ Exported {len(lines) - 1} blocked actions")

    # Security incidents
    print(f"\n🔹 Fetching high-severity incidents (risk ≥ 80)...")
    resp = requests.get(f"{API_BASE}/api/audit/incidents?min_risk_score=80&days=7")
    incidents = resp.json()
    print(f"   ⚠️  Found {len(incidents)} critical incidents in last 7 days")


def demo_alerts():
    """Demonstrate alert system."""
    print("\n" + "=" * 60)
    print("🚨 ALERT SYSTEM DEMO")
    print("=" * 60)

    # List alert rules
    resp = requests.get(f"{API_BASE}/api/alerts")
    rules = resp.json()["rules"]
    print(f"\n🔹 Active Alert Rules: {len(rules)}")
    for rule in rules:
        print(f"   • {rule['name']} → {rule['severity']} (triggered {rule['trigger_count']}x)")

    print(f"\n🔹 Alert channels: Console logs (default)")
    print(f"   Can add: Webhook, Slack, Email, PagerDuty")


def main():
    print("\n" + "=" * 60)
    print("🛡️  AI AGENT FIREWALL - UPGRADE DEMO")
    print("=" * 60)
    print("\nShowcasing new enterprise features:")
    print("  ✓ Rate limiting & quotas")
    print("  ✓ Advanced policy engine")
    print("  ✓ Real-time alerting")
    print("  ✓ Audit export & compliance")

    try:
        demo_rate_limiting()
        demo_policy_engine()
        demo_audit_export()
        demo_alerts()

        print("\n" + "=" * 60)
        print("✅ UPGRADE DEMO COMPLETE")
        print("=" * 60)
        print("\n📊 New API Endpoints:")
        print("  • GET  /api/rate-limit/{agent_id}")
        print("  • GET  /api/policies")
        print("  • POST /api/policies")
        print("  • GET  /api/audit/export?format=csv|json")
        print("  • GET  /api/audit/compliance")
        print("  • GET  /api/audit/incidents")
        print("  • GET  /api/alerts")
        print("\n🎯 Dashboard: http://localhost:3000")
        print("📖 API Docs: http://localhost:8000/docs")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Backend not running at http://localhost:8000")
        print("   Start it with: python -m uvicorn main:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
