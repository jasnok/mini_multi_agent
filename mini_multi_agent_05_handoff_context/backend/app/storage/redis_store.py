import json
from redis import Redis
from app.core.config import settings

def client():
    return Redis.from_url(settings.redis_url, decode_responses=True)

def save_snapshot(run_id: str, state: dict):
    key = f"mini05:run:{run_id}"
    values = {name: json.dumps(value, ensure_ascii=False) for name, value in state.items()}
    with client() as redis:
        redis.hset(key, mapping=values)
        redis.expire(key, settings.run_ttl_seconds)

def load_snapshot(run_id: str):
    with client() as redis:
        values = redis.hgetall(f"mini05:run:{run_id}")
    return {name: json.loads(value) for name, value in values.items()} if values else None

def append_event(run_id: str, event: dict):
    key = f"mini05:run:{run_id}:events"
    values = {name: json.dumps(value, ensure_ascii=False) for name, value in event.items()}
    with client() as redis:
        event_id = redis.xadd(key, values, maxlen=300, approximate=True)
        redis.expire(key, settings.run_ttl_seconds)
    return event_id

def read_events(run_id: str, after_id: str = "0-0"):
    with client() as redis:
        rows = redis.xrange(f"mini05:run:{run_id}:events", min=f"({after_id}")
    return [{"event_id": event_id, **{name: json.loads(value) for name, value in row.items()}} for event_id, row in rows]
