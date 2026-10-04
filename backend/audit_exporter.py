"""Audit export and compliance reporting."""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import StringIO


class AuditExporter:
    """Export audit logs for compliance and analysis."""

    def __init__(self, db_session):
        self.db = db_session

    def _get_tool_call_model(self):
        """Get ToolCall model from main module to avoid circular import."""
        from main import ToolCall
        return ToolCall

    def export_csv(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        decision: Optional[str] = None,
    ) -> str:
        """Export audit logs as CSV."""

        from main import ToolCall  # Import here to avoid circular dependency

        query = self.db.query(ToolCall)

        if start_date:
            query = query.filter(ToolCall.created_at >= start_date)
        if end_date:
            query = query.filter(ToolCall.created_at <= end_date)
        if agent_id:
            query = query.filter(ToolCall.agent_id == agent_id)
        if decision:
            query = query.filter(ToolCall.decision == decision)

        calls = query.order_by(ToolCall.created_at.desc()).all()

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Timestamp", "Agent ID", "Tool Name", "Arguments",
            "Decision", "Risk Score", "Risk Level", "Reason"
        ])

        # Rows
        for call in calls:
            writer.writerow([
                call.created_at.isoformat(),
                call.agent_id,
                call.tool_name,
                call.arguments,
                call.decision.value if call.decision else "",
                call.risk_score,
                call.risk_level.value if call.risk_level else "",
                call.reason or "",
            ])

        return output.getvalue()

    def export_json(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        """Export audit logs as JSON."""

        from main import ToolCall

        query = self.db.query(ToolCall)

        if start_date:
            query = query.filter(ToolCall.created_at >= start_date)
        if end_date:
            query = query.filter(ToolCall.created_at <= end_date)
        if agent_id:
            query = query.filter(ToolCall.agent_id == agent_id)

        calls = query.order_by(ToolCall.created_at.desc()).all()

        return json.dumps([
            {
                "id": call.id,
                "timestamp": call.created_at.isoformat(),
                "agent_id": call.agent_id,
                "tool_name": call.tool_name,
                "arguments": json.loads(call.arguments),
                "decision": call.decision,
                "risk_score": call.risk_score,
                "risk_level": call.risk_level,
                "reason": call.reason,
                "status": call.status,
            }
            for call in calls
        ], indent=2)

    def generate_compliance_report(
        self,
        period_days: int = 30,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""

        from main import ToolCall

        start_date = datetime.now() - timedelta(days=period_days)

        query = self.db.query(ToolCall).filter(ToolCall.created_at >= start_date)
        if agent_id:
            query = query.filter(ToolCall.agent_id == agent_id)

        calls = query.all()

        # Statistics
        total_calls = len(calls)
        blocked = sum(1 for c in calls if c.decision == "BLOCK")
        approved = sum(1 for c in calls if c.decision == "APPROVE")
        allowed = sum(1 for c in calls if c.decision == "ALLOW")

        # Risk breakdown
        critical = sum(1 for c in calls if c.risk_level == "CRITICAL")
        high = sum(1 for c in calls if c.risk_level == "HIGH")
        medium = sum(1 for c in calls if c.risk_level == "MEDIUM")
        low = sum(1 for c in calls if c.risk_level == "LOW")

        # Top blocked reasons
        blocked_calls = [c for c in calls if c.decision == "BLOCK"]
        reasons = {}
        for call in blocked_calls:
            reason = call.reason or "Unknown"
            reasons[reason] = reasons.get(reason, 0) + 1

        top_blocked_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top tools used
        tools = {}
        for call in calls:
            tools[call.tool_name] = tools.get(call.tool_name, 0) + 1

        top_tools = sorted(tools.items(), key=lambda x: x[1], reverse=True)[:10]

        # Daily activity
        daily = {}
        for call in calls:
            day = call.created_at.date().isoformat()
            daily[day] = daily.get(day, 0) + 1

        return {
            "report_period": f"{period_days} days",
            "generated_at": datetime.now().isoformat(),
            "agent_id": agent_id or "ALL",
            "summary": {
                "total_calls": total_calls,
                "allowed": allowed,
                "blocked": blocked,
                "awaiting_approval": approved,
                "block_rate": round(blocked / total_calls * 100, 2) if total_calls > 0 else 0,
            },
            "risk_distribution": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
            },
            "top_blocked_reasons": [
                {"reason": r, "count": c} for r, c in top_blocked_reasons
            ],
            "top_tools": [
                {"tool": t, "count": c} for t, c in top_tools
            ],
            "daily_activity": daily,
        }

    def export_security_incidents(
        self,
        min_risk_score: int = 80,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Export high-severity security incidents."""

        from main import ToolCall

        start_date = datetime.now() - timedelta(days=days)

        incidents = self.db.query(ToolCall).filter(
            ToolCall.created_at >= start_date,
            ToolCall.risk_score >= min_risk_score,
        ).order_by(ToolCall.created_at.desc()).all()

        return [
            {
                "id": inc.id,
                "timestamp": inc.created_at.isoformat(),
                "agent_id": inc.agent_id,
                "tool_name": inc.tool_name,
                "risk_score": inc.risk_score,
                "risk_level": inc.risk_level,
                "decision": inc.decision,
                "reason": inc.reason,
                "arguments": json.loads(inc.arguments),
            }
            for inc in incidents
        ]
