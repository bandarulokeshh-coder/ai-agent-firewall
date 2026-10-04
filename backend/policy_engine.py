"""Advanced policy engine with templates and custom rules."""

from typing import List, Dict, Any, Optional
from datetime import datetime, time
import re


class PolicyRule:
    """Single policy rule."""

    def __init__(
        self,
        name: str,
        conditions: Dict[str, Any],
        action: str,  # ALLOW, BLOCK, APPROVE
        priority: int = 50,
        enabled: bool = True,
    ):
        self.name = name
        self.conditions = conditions
        self.action = action
        self.priority = priority
        self.enabled = enabled

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if rule matches the context."""
        if not self.enabled:
            return False

        for key, condition in self.conditions.items():
            if key == "tool_name":
                if not self._match_pattern(context.get("tool_name", ""), condition):
                    return False

            elif key == "risk_score_min":
                if context.get("risk_score", 0) < condition:
                    return False

            elif key == "risk_score_max":
                if context.get("risk_score", 0) > condition:
                    return False

            elif key == "agent_tags":
                agent_tags = context.get("agent_tags", [])
                if not any(tag in agent_tags for tag in condition):
                    return False

            elif key == "time_range":
                if not self._in_time_range(condition):
                    return False

            elif key == "argument_pattern":
                args_str = str(context.get("arguments", {}))
                if not re.search(condition, args_str, re.IGNORECASE):
                    return False

            elif key == "ip_whitelist":
                if context.get("source_ip") not in condition:
                    return False

        return True

    def _match_pattern(self, value: str, pattern: str) -> bool:
        """Match value against pattern (supports wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(value, pattern)

    def _in_time_range(self, time_range: Dict[str, str]) -> bool:
        """Check if current time is within range."""
        now = datetime.now().time()
        start = datetime.strptime(time_range["start"], "%H:%M").time()
        end = datetime.strptime(time_range["end"], "%H:%M").time()

        if start <= end:
            return start <= now <= end
        else:  # Overnight range
            return now >= start or now <= end


class PolicyEngine:
    """Manages and evaluates policy rules."""

    def __init__(self):
        self.rules: List[PolicyRule] = []
        self._load_default_templates()

    def _load_default_templates(self):
        """Load built-in policy templates."""

        # Production safety template
        self.add_rule(PolicyRule(
            name="block_prod_modifications",
            conditions={
                "tool_name": "*",
                "argument_pattern": r"(production|prod|live).*(?:delete|drop|truncate|rm)",
            },
            action="BLOCK",
            priority=100,
        ))

        # Business hours only for deployments
        self.add_rule(PolicyRule(
            name="deploy_business_hours_only",
            conditions={
                "tool_name": "deploy",
                "time_range": {"start": "09:00", "end": "17:00"},
            },
            action="APPROVE",
            priority=80,
        ))

        # High-risk actions need approval
        self.add_rule(PolicyRule(
            name="high_risk_approval",
            conditions={"risk_score_min": 70},
            action="APPROVE",
            priority=70,
        ))

        # Database safety
        self.add_rule(PolicyRule(
            name="block_destructive_db",
            conditions={
                "tool_name": "query_db",
                "argument_pattern": r"(?:DROP|TRUNCATE|DELETE\s+FROM.*WHERE\s+1=1)",
            },
            action="BLOCK",
            priority=90,
        ))

        # File system protection
        self.add_rule(PolicyRule(
            name="block_sensitive_file_read",
            conditions={
                "tool_name": "read_file",
                "argument_pattern": r"(?:\.env|\.pem|\.key|id_rsa|password|secret)",
            },
            action="BLOCK",
            priority=95,
        ))

    def add_rule(self, rule: PolicyRule):
        """Add a new rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str):
        """Remove a rule by name."""
        self.rules = [r for r in self.rules if r.name != name]

    def evaluate(self, context: Dict[str, Any]) -> Optional[str]:
        """Evaluate context against rules.

        Returns:
            action (ALLOW/BLOCK/APPROVE) if a rule matches, else None
        """
        for rule in self.rules:
            if rule.matches(context):
                return rule.action
        return None

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules as dicts."""
        return [
            {
                "name": r.name,
                "conditions": r.conditions,
                "action": r.action,
                "priority": r.priority,
                "enabled": r.enabled,
            }
            for r in self.rules
        ]

    def enable_template(self, template_name: str):
        """Enable a policy template."""
        templates = {
            "strict_production": self._strict_production_template,
            "dev_friendly": self._dev_friendly_template,
            "compliance_mode": self._compliance_template,
        }

        if template_name in templates:
            templates[template_name]()

    def _strict_production_template(self):
        """Ultra-strict production safety."""
        self.add_rule(PolicyRule(
            name="block_all_writes_prod",
            conditions={"argument_pattern": r"production.*(?:write|modify|delete)"},
            action="BLOCK",
            priority=100,
        ))

    def _dev_friendly_template(self):
        """Relaxed rules for development."""
        self.add_rule(PolicyRule(
            name="allow_dev_env",
            conditions={"agent_tags": ["dev", "staging"]},
            action="ALLOW",
            priority=40,
        ))

    def _compliance_template(self):
        """Compliance & audit requirements."""
        self.add_rule(PolicyRule(
            name="require_approval_pii",
            conditions={"argument_pattern": r"(?:email|phone|ssn|credit_card)"},
            action="APPROVE",
            priority=85,
        ))
