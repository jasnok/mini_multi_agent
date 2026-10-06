import json
from hashlib import sha256

from redis import Redis

from app.core.config import settings


def client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def save_snapshot(run_id: str, state: dict[str, object]) -> None:
    values = {name: json.dumps(value, ensure_ascii=False) for name, value in state.items()}
    with client() as redis:
        redis.hset(f"mini06:run:{run_id}", mapping=values)
        redis.expire(f"mini06:run:{run_id}", settings.run_ttl_seconds)


def load_snapshot(run_id: str) -> dict[str, object] | None:
    with client() as redis:
        values = redis.hgetall(f"mini06:run:{run_id}")
    return {name: json.loads(value) for name, value in values.items()} if values else None


def append_event(run_id: str, event: dict[str, object]) -> None:
    with client() as redis:
        redis.rpush(f"mini06:run:{run_id}:events", json.dumps(event, ensure_ascii=False))
        redis.expire(f"mini06:run:{run_id}:events", settings.run_ttl_seconds)


def load_events(run_id: str) -> list[dict[str, object]]:
    with client() as redis:
        values = redis.lrange(f"mini06:run:{run_id}:events", 0, -1)
    return [json.loads(value) for value in values]


def claim_idempotency(user_id: str, idempotency_key: str, request_payload: dict[str, object]) -> str:
    """동일 키·동일 요청은 재사용하고, 동일 키·다른 요청은 충돌로 차단합니다."""
    digest = sha256(
        json.dumps([user_id, idempotency_key], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    key = f"mini06:idempotency:{digest}"
    fingerprint = sha256(
        json.dumps(request_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with client() as redis:
        if redis.set(key, fingerprint, nx=True, ex=settings.run_ttl_seconds):
            return "claimed"
        return "reused" if redis.get(key) == fingerprint else "conflict"


def claim_approval_decision(approval_id: str) -> bool:
    """동일 승인에 대한 동시 결정을 한 요청만 처리하도록 원자적으로 선점합니다."""
    with client() as redis:
        return bool(redis.set(
            f"mini06:approval-lock:{approval_id}",
            "processing",
            nx=True,
            ex=settings.run_ttl_seconds,
        ))


def save_itinerary(user_id: str, itinerary_id: str, itinerary: dict[str, object]) -> dict[str, object]:
    """승인된 여행 일정을 Redis에 실제로 저장합니다."""
    key = f"mini06:itinerary:{user_id}:{itinerary_id}"
    stored = {
        "itinerary_id": itinerary_id,
        "user_id": user_id,
        "itinerary": itinerary,
    }
    with client() as redis:
        redis.set(
            key,
            json.dumps(stored, ensure_ascii=False),
            ex=settings.run_ttl_seconds,
        )
    return stored


def save_demo_booking(user_id: str, approval_id: str, details: dict[str, object]) -> dict[str, object]:
    """Lab 10의 교육용 예약을 Redis에 저장합니다. 실제 숙소에는 요청하지 않습니다."""
    booking = {
        "booking_id": approval_id,
        "user_id": user_id,
        "hotel": details["hotel"],
        "itinerary": details["draft"],
        "status": "demo_confirmed",
    }
    with client() as redis:
        redis.set(
            f"mini06:demo-booking:{user_id}:{approval_id}",
            json.dumps(booking, ensure_ascii=False),
            ex=settings.run_ttl_seconds,
        )
    return booking
