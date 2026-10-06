"""Lab 10: 실행 중 멈추고 사용자 결정을 기다리는 승인 Workflow입니다."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.agents.input_guard_agent import inspect_input_fields
from app.agents.tool_guard_agent import authorize_tool, minimum_context
from app.agents.travel_agent import create_travel_draft
from app.mcp.client import call
from app.observability.tracker import GuardrailTracker
from app.schemas.contracts import ApprovalDecisionRequest, ApprovalRunRequest
from app.services.demo_seed_data import hotels_for_weather
from app.storage.redis_store import (
    claim_idempotency,
    claim_approval_decision,
    load_events,
    load_snapshot,
    save_itinerary,
    save_demo_booking,
    save_snapshot,
)


def action_hash(arguments: dict[str, object]) -> str:
    """사용자가 확인한 실행 인자가 나중에 변경되지 않았는지 확인합니다."""
    encoded = json.dumps(
        arguments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_approval_run(request: ApprovalRunRequest) -> tuple[str, dict[str, object], str]:
    """승인 Workflow의 최초 상태를 만듭니다."""
    run_id = f"run-{uuid4().hex[:12]}"
    approval_token = secrets.token_urlsafe(32)
    state = {
        "run_id": run_id,
        "workflow": "human_approval",
        "user_id": request.user_id,
        "status": "queued",
        "current_stage": "queued",
        "current_status": "waiting",
        "message": "여행 초안 생성을 기다리고 있습니다.",
        "progress": 0,
        "approval": None,
        "draft": None,
        "hotel_options": [],
        "result": None,
        "approval_token_hash": token_hash(approval_token),
    }
    return run_id, state, approval_token


async def prepare_approval(
    run_id: str,
    state: dict[str, object],
    request: ApprovalRunRequest,
) -> None:
    """초안을 만든 뒤 저장하지 않고 pending_approval 상태로 멈춥니다."""
    tracker = GuardrailTracker(run_id, state)
    tracker.sequence = len(load_events(run_id))
    state["status"] = "running"

    try:
        allowed, reason = inspect_input_fields({
            "destination": request.destination,
            "preferences": request.preferences,
            "user_message": request.user_message,
        })
        tracker.record("input_guard", "input_guard_agent", "allowed" if allowed else "blocked", reason)
        if not allowed:
            tracker.finish("blocked", {"blocked_at": "input_guard", "reason": reason})
            return

        full_context = {
            "destination": request.destination,
            "days": request.days,
            "preferences": request.preferences,
            "user_message": request.user_message,
        }
        weather_context = minimum_context("weather_agent", full_context)
        authorize_tool("weather_agent", "get_weather")
        try:
            weather = await call(
                "get_weather",
                {
                    "city": weather_context["destination"],
                    "days": weather_context["days"],
                },
                {"get_weather"},
            )
            if weather.get("success") is False:
                raise RuntimeError(weather.get("error", "날씨 조회에 실패했습니다."))
            tracker.record("weather", "weather_agent", "completed", "실제 날씨를 조회했습니다.")
        except Exception:
            weather = {"success": False, "source": "unavailable"}
            tracker.record("weather", "weather_agent", "failed", "실제 날씨 조회에 실패했습니다. 선택한 수업용 시나리오로 계속합니다.")

        # 실제 조회 결과는 화면에 남기고, 비교 실습에는 선택한 시나리오를 사용합니다.
        state["actual_weather"] = weather
        state["weather_scenario"] = request.weather_scenario
        state["hotel_options"] = hotels_for_weather(request.weather_scenario)
        tracker.record("hotel_search", "hotel_catalog", "completed", "날씨 시나리오에 맞춰 숙소 후보를 정렬했습니다.")

        travel_context = minimum_context(
            "travel_agent",
            {**full_context, "weather": {"scenario": request.weather_scenario, "actual_weather": weather}},
        )
        draft, metadata = await create_travel_draft(travel_context)
        tracker.record("draft", "travel_agent", "completed", "승인할 여행 초안을 만들었습니다.", metadata)

        arguments = {
            "destination": request.destination,
            "days": request.days,
            "preferences": request.preferences,
            "draft": draft.model_dump(),
        }
        now = datetime.now(timezone.utc)
        approval = {
            "approval_id": f"approval-{uuid4().hex[:12]}",
            "requested_by_agent": "itinerary_agent",
            "action": "book_demo_hotel",
            "action_arguments": arguments,
            "action_hash": action_hash(arguments),
            "summary": f"{request.destination} {request.days}일 일정과 선택한 숙소를 교육용 예약으로 저장합니다.",
            "requested_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "status": "pending",
        }
        state["draft"] = draft.model_dump()
        state["approval"] = approval
        state["status"] = "pending_approval"
        tracker.record(
            "approval_requested",
            "itinerary_agent",
            "waiting",
            "숙소 예약 기록을 저장하기 전에 사용자 승인을 기다립니다.",
            {"approval_id": approval["approval_id"], "action": approval["action"]},
        )
        save_snapshot(run_id, state)
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        tracker.record("workflow", "approval_orchestrator", "failed", message)
        tracker.finish("failed", {"error": message})


def decide_approval(
    run_id: str,
    decision: ApprovalDecisionRequest,
    authenticated_user_id: str,
    approval_token: str,
) -> dict[str, object]:
    """승인 또는 거부를 처리하고 승인된 경우에만 일정을 저장합니다."""
    state = load_snapshot(run_id)
    if state is None:
        raise LookupError("실행을 찾을 수 없습니다.")
    if state.get("status") != "pending_approval":
        raise ValueError("승인을 기다리는 실행만 처리할 수 있습니다.")
    if state.get("user_id") != authenticated_user_id:
        raise PermissionError("실행을 요청한 사용자만 결정할 수 있습니다.")
    expected_token_hash = state.get("approval_token_hash")
    if not isinstance(expected_token_hash, str) or not hmac.compare_digest(
        expected_token_hash, token_hash(approval_token)
    ):
        raise PermissionError("승인 실행 Token이 올바르지 않습니다.")

    approval = state.get("approval")
    if not isinstance(approval, dict):
        raise ValueError("승인 요청 정보가 없습니다.")
    if approval.get("approval_id") != decision.approval_id:
        raise ValueError("현재 대기 중인 승인 ID와 다릅니다.")
    if approval.get("status") != "pending":
        raise ValueError("이미 처리된 승인 요청입니다.")
    hotel_options = state.get("hotel_options", [])
    selected_hotel = next(
        (hotel for hotel in hotel_options if hotel["hotel_id"] == decision.hotel_id),
        None,
    )
    if decision.decision == "approve" and hotel_options and selected_hotel is None:
        raise ValueError("목록에서 예약할 숙소를 선택해 주세요.")
    if not claim_approval_decision(str(approval["approval_id"])):
        raise ValueError("승인 요청이 이미 처리 중입니다.")

    expires_at = datetime.fromisoformat(str(approval["expires_at"]))
    if datetime.now(timezone.utc) >= expires_at:
        approval["status"] = "expired"
        state["status"] = "expired"
        save_snapshot(run_id, state)
        raise ValueError("승인 요청이 만료되었습니다.")

    tracker = GuardrailTracker(run_id, state)
    tracker.sequence = len(load_events(run_id))
    if decision.decision == "reject":
        approval["status"] = "rejected"
        approval["reason"] = decision.reason
        tracker.record("approval", "user", "rejected", decision.reason or "사용자가 저장을 거부했습니다.")
        tracker.finish("rejected", {"saved": False, "draft": state.get("draft")})
        return state

    arguments = approval.get("action_arguments")
    if not isinstance(arguments, dict):
        raise ValueError("승인할 실행 인자가 없습니다.")
    if action_hash(arguments) != approval.get("action_hash"):
        raise PermissionError("승인 요청 이후 실행 인자가 변경되었습니다.")

    tool_name = "book_demo_hotel" if selected_hotel else "save_itinerary"
    authorize_tool("itinerary_agent", tool_name, approved=True)
    tracker.record("approval", "user", "approved", "사용자가 일정과 숙소를 확인하고 승인했습니다.")

    if selected_hotel:
        arguments = {**arguments, "hotel": selected_hotel}

    claim = claim_idempotency(
        authenticated_user_id,
        decision.idempotency_key,
        arguments,
    )
    if claim == "conflict":
        tracker.record("idempotency", "itinerary_agent", "blocked", "멱등성 키가 다른 요청에 사용되었습니다.")
        tracker.finish("blocked", {"saved": False, "reason": "idempotency_key_conflict"})
        return state

    stored = None
    if claim == "claimed":
        if selected_hotel:
            stored = save_demo_booking(authenticated_user_id, decision.approval_id, arguments)
            tracker.record("write_tool", "itinerary_agent", "executed", "승인된 수업용 숙소 예약을 Redis에 저장했습니다.")
        else:
            stored = save_itinerary(authenticated_user_id, decision.approval_id, arguments)
            tracker.record("write_tool", "itinerary_agent", "executed", "승인된 일정을 Redis에 저장했습니다.")
    else:
        tracker.record("write_tool", "itinerary_agent", "reused", "이미 처리된 동일 저장 요청을 재사용했습니다.")

    approval["status"] = "executed"
    state["status"] = "completed"
    tracker.finish(
        "completed",
        {
            "saved": True,
            "execution": claim,
            "stored": stored,
            "draft": state.get("draft"),
        },
    )
    return state
