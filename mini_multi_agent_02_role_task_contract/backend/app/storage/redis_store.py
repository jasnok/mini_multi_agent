"""Redis Hash와 Stream을 사용하는 작은 실행 저장소."""
import json
from redis import Redis
from app.core.config import settings


def redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def state_key(run_id: str) -> str:
    return f"mini02:run:{run_id}"


def event_key(run_id: str) -> str:
    return f"mini02:run:{run_id}:events"


def save_state(run_id: str, state: dict[str, object]) -> None:
    values = {key: json.dumps(value, ensure_ascii=False) for key, value in state.items()}
    with redis_client() as client:
        client.hset(state_key(run_id), mapping=values)
        client.expire(state_key(run_id), settings.run_ttl_seconds)


def load_state(run_id: str) -> dict[str, object] | None:
    with redis_client() as client:
        values = client.hgetall(state_key(run_id))
    return {key: json.loads(value) for key, value in values.items()} if values else None


def append_event(run_id: str, event: dict[str, object]) -> str:
    values = {key: json.dumps(value, ensure_ascii=False) for key, value in event.items()}
    with redis_client() as client:
        event_id = client.xadd(event_key(run_id), values, maxlen=500, approximate=True)
        client.expire(event_key(run_id), settings.run_ttl_seconds)
    return event_id


def load_events(run_id: str) -> list[dict[str, object]]:
    with redis_client() as client:
        rows = client.xrange(event_key(run_id))
    return [{"event_id": event_id, **{key: json.loads(value) for key, value in values.items()}} for event_id, values in rows]
