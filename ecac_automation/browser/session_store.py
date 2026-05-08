import json
import redis


class SessionStore:
    def __init__(self, redis_url: str, ttl_seconds: int):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    def get(self, tenant_id: str) -> dict | None:
        data = self.client.get(f"ecac:session:{tenant_id}")
        return json.loads(data) if data else None

    def set(self, tenant_id: str, storage_state: dict) -> None:
        self.client.setex(
            f"ecac:session:{tenant_id}",
            self.ttl_seconds,
            json.dumps(storage_state),
        )
