"""Rate limiting and quota management for agents."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading


class RateLimiter:
    """Token bucket rate limiter for agent actions."""

    def __init__(self):
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": 100,
            "last_refill": datetime.now(),
            "call_count": 0,
            "blocked_count": 0,
        })
        self.lock = threading.Lock()

        # Configurable limits
        self.max_tokens = 100
        self.refill_rate = 10  # tokens per minute
        self.max_calls_per_hour = 1000
        self.max_high_risk_per_hour = 10

    def check_limit(self, agent_id: str, risk_score: int) -> tuple[bool, str]:
        """Check if agent is within rate limits.

        Returns:
            (allowed: bool, reason: str)
        """
        with self.lock:
            bucket = self.buckets[agent_id]
            now = datetime.now()

            # Refill tokens based on time elapsed
            elapsed = (now - bucket["last_refill"]).total_seconds() / 60
            refill_amount = int(elapsed * self.refill_rate)

            if refill_amount > 0:
                bucket["tokens"] = min(self.max_tokens, bucket["tokens"] + refill_amount)
                bucket["last_refill"] = now

            # Check hourly call count
            if bucket["call_count"] >= self.max_calls_per_hour:
                return False, f"Hourly limit exceeded: {self.max_calls_per_hour} calls/hour"

            # High-risk action quota
            if risk_score > 60 and bucket.get("high_risk_count", 0) >= self.max_high_risk_per_hour:
                return False, f"High-risk action quota exceeded: {self.max_high_risk_per_hour}/hour"

            # Token bucket check
            cost = 1 + (risk_score // 20)  # Higher risk = more tokens
            if bucket["tokens"] < cost:
                return False, f"Rate limit: insufficient tokens ({bucket['tokens']}/{cost} needed)"

            # Deduct tokens
            bucket["tokens"] -= cost
            bucket["call_count"] += 1
            if risk_score > 60:
                bucket["high_risk_count"] = bucket.get("high_risk_count", 0) + 1

            return True, ""

    def get_stats(self, agent_id: str) -> dict:
        """Get rate limit stats for an agent."""
        with self.lock:
            bucket = self.buckets[agent_id]
            return {
                "tokens_remaining": bucket["tokens"],
                "max_tokens": self.max_tokens,
                "calls_this_hour": bucket["call_count"],
                "max_calls_per_hour": self.max_calls_per_hour,
                "high_risk_calls": bucket.get("high_risk_count", 0),
                "max_high_risk_per_hour": self.max_high_risk_per_hour,
            }

    def reset_hourly_counters(self):
        """Reset hourly counters (call from a cron job)."""
        with self.lock:
            for bucket in self.buckets.values():
                bucket["call_count"] = 0
                bucket["high_risk_count"] = 0
