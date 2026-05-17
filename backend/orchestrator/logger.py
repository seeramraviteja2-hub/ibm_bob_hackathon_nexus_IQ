"""
NexusIQ — Agent Logger.
No FastAPI imports. Pure async Python + Redis.

FIX: Added TTL (7 days) to the Redis list after each rpush.
Previously, log entries accumulated forever with no expiry.
"""

import json
from datetime import datetime, timezone

_LOG_TTL_SECONDS = 86_400 * 7  # 7 days — matches session state TTL


class AgentLogger:
    """
    Structured per-session logger for agent activity.

    Each log entry is:
      - Appended to a Redis list  (nexus:logs:{session_id}) for history retrieval
        by the manager dashboard.
      - Published to a Redis pub/sub channel (nexus:logs:{session_id}) for
        real-time streaming to the WebSocket client.

    Agent status updates are published to a separate channel
    (nexus:status:{session_id}) so the frontend can track which agents
    are running vs idle without parsing log messages.
    """

    def __init__(self, session_id: str, agent_name: str, redis_client) -> None:
        self.session_id = session_id
        self.agent_name = agent_name
        self.redis      = redis_client
        self._list_key  = f"nexus:logs:{session_id}"
        self._chan_key  = f"nexus:logs:{session_id}"
        self._stat_key  = f"nexus:status:{session_id}"

    async def log(
        self,
        level: str,
        message: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Append a structured log entry to the Redis list and publish it to
        the pub/sub channel so the WebSocket picks it up instantly.
        """
        entry = {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "level":      level,
            "message":    message,
            "metadata":   metadata or {},
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        payload = json.dumps(entry)

        # Pipeline: rpush + expire in one round-trip to Redis
        async with self.redis.pipeline(transaction=False) as pipe:
            pipe.rpush(self._list_key, payload)
            pipe.expire(self._list_key, _LOG_TTL_SECONDS)  # FIX: prevents memory leak
            await pipe.execute()

        await self.redis.publish(self._chan_key, payload)

    async def set_status(self, status: str) -> None:
        """
        Publish agent status to the status channel.
        Frontend uses this to update the agent activity panel in real time.
        Valid statuses: idle | running | complete | failed
        """
        entry = {
            "agent_name": self.agent_name,
            "status":     status,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        await self.redis.publish(self._stat_key, json.dumps(entry))
