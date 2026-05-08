import json
import redis


class SmartCache:
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get_json(self, key: str) -> dict | None:
        payload = self.client.get(key)
        return json.loads(payload) if payload else None

    def set_json(self, key: str, value: dict, ttl: int = 300):
        self.client.setex(key, ttl, json.dumps(value))
