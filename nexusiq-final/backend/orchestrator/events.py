"""
NexusIQ — Event Publisher.
Publishes domain events to Redis pub/sub channels.
Agents use this instead of touching the DB directly (they have no session).
"""
import json
from datetime import datetime, timezone


class EventPublisher:
    # ── Event name constants ───────────────────────────────────────────────
    COURSE_GENERATED   = "nexus:events:course_generated"
    ESCALATION_FLAGGED = "nexus:events:escalation_flagged"
    MODULE_PASSED      = "nexus:events:module_passed"
    MODULE_FAILED      = "nexus:events:module_failed"

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    async def publish(self, channel: str, payload: dict) -> None:
        """
        Publish a JSON event to a Redis pub/sub channel.
        Adds a timestamp automatically.
        """
        payload["_published_at"] = datetime.now(timezone.utc).isoformat()
        await self._redis.publish(channel, json.dumps(payload))
