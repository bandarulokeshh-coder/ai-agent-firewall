"""Real-time alerting system for security events."""

from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import threading


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertChannel:
    """Base class for alert destinations."""

    def send(self, alert: Dict[str, Any]):
        raise NotImplementedError


class WebhookAlert(AlertChannel):
    """Send alerts to webhook URL."""

    def __init__(self, url: str, headers: Optional[Dict] = None):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}

    def send(self, alert: Dict[str, Any]):
        import urllib.request
        import json

        data = json.dumps(alert).encode()
        req = urllib.request.Request(
            self.url, data=data,
            headers=self.headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"Webhook alert failed: {e}")


class LogAlert(AlertChannel):
    """Log alerts to console/file."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file

    def send(self, alert: Dict[str, Any]):
        import logging

        if self.log_file:
            logging.basicConfig(filename=self.log_file, level=logging.WARNING)

        severity = alert.get("severity", "MEDIUM")
        log_fn = {
            "LOW": logging.info,
            "MEDIUM": logging.warning,
            "HIGH": logging.error,
            "CRITICAL": logging.critical,
        }.get(severity, logging.warning)

        log_fn(f"[ALERT] {alert['title']}: {alert['message']}")


class AlertRule:
    """Condition-based alert rule."""

    def __init__(
        self,
        name: str,
        condition: Dict[str, Any],
        severity: str = "MEDIUM",
        cooldown_minutes: int = 5,
    ):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.last_triggered: Optional[datetime] = None
        self.trigger_count = 0

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if alert condition matches."""
        for key, expected in self.condition.items():
            actual = context.get(key)

            if key == "risk_score_min":
                if (actual or 0) < expected:
                    return False

            elif key == "risk_score_max":
                if (actual or 0) > expected:
                    return False

            elif key == "decision":
                if actual != expected:
                    return False

            elif key == "tool_name":
                if actual != expected:
                    return False

            elif key == "repeated_count":
                # Check cooldown
                if self.last_triggered:
                    if datetime.now() - self.last_triggered < self.cooldown:
                        return False
                return True

        return True

    def trigger(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert payload."""
        self.last_triggered = datetime.now()
        self.trigger_count += 1

        return {
            "title": f"Security Alert: {self.name}",
            "message": f"Alert '{self.name}' triggered",
            "severity": self.severity,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "rule": self.name,
            "trigger_count": self.trigger_count,
        }


class AlertManager:
    """Manages alert rules and notifications."""

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.channels: List[AlertChannel] = []
        self._lock = threading.Lock()
        self._load_default_rules()

    def _load_default_rules(self):
        """Load built-in alert rules."""

        # Critical risk alerts
        self.add_rule(AlertRule(
            name="critical_risk_detected",
            condition={"risk_score_min": 90},
            severity="CRITICAL",
            cooldown_minutes=1,
        ))

        # High risk blocked
        self.add_rule(AlertRule(
            name="high_risk_blocked",
            condition={"risk_score_min": 70, "decision": "BLOCK"},
            severity="HIGH",
            cooldown_minutes=5,
        ))

        # Multiple blocked requests
        self.add_rule(AlertRule(
            name="repeated_blocks",
            condition={"decision": "BLOCK"},
            severity="MEDIUM",
            cooldown_minutes=10,
        ))

        # Specific dangerous tools
        self.add_rule(AlertRule(
            name="dangerous_tool_called",
            condition={"tool_name": "run_command"},
            severity="MEDIUM",
            cooldown_minutes=2,
        ))

    def add_channel(self, channel: AlertChannel):
        """Add notification channel."""
        self.channels.append(channel)

    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.rules.append(rule)

    def check_and_alert(self, context: Dict[str, Any]):
        """Check all rules and trigger alerts."""
        with self._lock:
            for rule in self.rules:
                if rule.matches(context):
                    alert = rule.trigger(context)
                    self._send_alert(alert)

    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert to all channels."""
        for channel in self.channels:
            try:
                channel.send(alert)
            except Exception as e:
                print(f"Alert channel failed: {e}")

        # Also emit via WebSocket if available
        if hasattr(self, 'ws_manager'):
            self.ws_manager.broadcast_alert(alert)

    def set_ws_manager(self, ws_manager):
        """Set WebSocket manager for real-time alerts."""
        self.ws_manager = ws_manager


# Singleton instance
alert_manager = AlertManager()

# Add default logging channel
alert_manager.add_channel(LogAlert())