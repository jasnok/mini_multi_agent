import json

from redis import Redis

from app.core.config import settings


def client():
    return Redis.from_url(settings.redis_url, decode_responses=True)


def save_state(run_id: str, state: dict):
    key = f"mini03:run:{run_id}"
    values = {name: json.dumps(value, ensure_ascii=False) for name, value in state.items()}
    with client() as redis:
        redis.hset(key, mapping=values)
        redis.expire(key, settings.run_ttl_seconds)


def load_state(run_id: str):
    with client() as redis:
        data = redis.hgetall(f"mini03:run:{run_id}")
    return {name: json.loads(value) for name, value in data.items()} if data else None


def add_event(run_id: str, event: dict):
    key = f"mini03:run:{run_id}:events"
    values = {name: json.dumps(value, ensure_ascii=False) for name, value in event.items()}
    with client() as redis:
        redis.xadd(key, values, maxlen=500, approximate=True)
        redis.expire(key, settings.run_ttl_seconds)


def events(run_id: str):
    with client() as redis:
        rows = redis.xrange(f"mini03:run:{run_id}:events")
    return [
        {"event_id": event_id, **{name: json.loads(value) for name, value in row.items()}}
        for event_id, row in rows
    ]
