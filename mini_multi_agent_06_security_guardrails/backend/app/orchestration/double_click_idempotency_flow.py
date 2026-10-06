"""Lab 13: 사용자가 저장 버튼을 두 번 클릭해도 실제 저장은 한 번만 한다."""

from __future__ import annotations

from app.schemas.contracts import DoubleClickIdempotencyRequest
from app.storage.redis_store import claim_idempotency, save_itinerary


def run_double_click_idempotency(request: DoubleClickIdempotencyRequest) -> dict[str, object]:
    """같은 저장 요청이 두 번 도착하는 상황을 순서대로 재현합니다."""

    trace: list[dict[str, object]] = []
    save_count = 0
    payload = {
        "title": request.itinerary_title,
        "source": "double_click_demo",
    }

    for click_number in [1, 2]:
        claim = claim_idempotency(request.user_id, request.idempotency_key, payload)

        if claim == "claimed":
            save_count += 1
            stored = save_itinerary(
                request.user_id,
                f"double-click-{request.idempotency_key}",
                payload,
            )
            trace.append({
                "click": click_number,
                "stage": "save_button_click",
                "status": "executed",
                "message": "처음 도착한 요청이라 실제 저장을 실행했습니다.",
                "stored": stored,
            })
        elif claim == "reused":
            trace.append({
                "click": click_number,
                "stage": "save_button_click",
                "status": "reused",
                "message": "같은 요청이 이미 처리되어 실제 저장을 다시 실행하지 않았습니다.",
            })
        else:
            trace.append({
                "click": click_number,
                "stage": "save_button_click",
                "status": "blocked",
                "message": "같은 멱등성 키가 다른 저장 내용에 사용되어 차단했습니다.",
            })
            return {
                "status": "blocked",
                "save_count": save_count,
                "trace": trace,
            }

    if save_count == 1:
        explanation = "두 번 클릭했지만 같은 idempotency_key라 이번 실행에서 실제 저장은 한 번만 실행되었습니다."
    else:
        explanation = "이 idempotency_key는 이미 처리된 적이 있어 이번 실행에서는 저장 함수를 다시 실행하지 않았습니다. 새 키를 만들면 첫 클릭이 executed가 됩니다."

    return {
        "status": "completed",
        "save_count": save_count,
        "expected_save_count": 1,
        "explanation": explanation,
        "trace": trace,
    }
