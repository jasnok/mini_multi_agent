import re

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.observability.tracker import HandoffTracker
from app.orchestration.guards import validate_handoff
from app.schemas.contracts import (
    HandoffEnvelope, HandoffRunRequest, HandoffState,
    ItineraryResult, WeatherHandoffDecision,
)


INTERNAL_CONTEXT_NAMES = {"weather_summary", "weather_cautions", "transport", "check_travel_details"}


def validate_itinerary_content(itinerary: ItineraryResult, request: HandoffRunRequest) -> None:
    """Reject a structurally valid response that does not contain a usable itinerary."""
    if itinerary.destination != request.destination:
        raise ValueError("일정 목적지가 요청과 다릅니다.")
    if len(itinerary.day_plans) != request.days:
        raise ValueError(f"{request.days}일 여행에는 {request.days}개의 일별 일정이 필요합니다.")
    for index, plan in enumerate(itinerary.day_plans, 1):
        detail = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", plan).strip(" -:·\n")
        if len(detail) < 15 or re.search(r"[가-힣A-Za-z]", detail) is None:
            raise ValueError(f"{index}일차에 방문 활동과 날씨를 반영한 이동 내용을 적어야 합니다.")
    if any(item.strip().lower() in INTERNAL_CONTEXT_NAMES for item in itinerary.applied_constraints):
        raise ValueError("반영한 조건에는 내부 필드 이름 대신 여행자가 이해할 설명이 필요합니다.")


async def execute_handoff(run_id: str, request: HandoffRunRequest) -> None:
    state = HandoffState(run_id=run_id)
    tracker = HandoffTracker(state)
    state.status = "running"
    tracker.save()
    tracker.emit("weather_agent", "handoff_workflow_started", "started", "실제 날씨 조회 시작")
    def record(title, status, message, data=None):
        state.trace.append({"title": title, "status": status, "message": message,
                            "data": data, "owner_agent": state.owner_agent})
        tracker.save()

    try:
        weather_profile = get_agent("weather_agent")
        weather_prompt = f"""당신은 weather_agent입니다.
Goal: {weather_profile.goal}
Instructions: {weather_profile.instructions}
목적지: {request.destination}, 기간: {request.days}일
일정 조정이 필요하면 itinerary_agent Handoff를 제안하세요.
WeatherHandoffDecision 계약으로 반환하세요."""
        decision, _, tool_results = await run_agent(
            weather_profile,
            weather_prompt,
            WeatherHandoffDecision,
            {"get_weather": {"city": request.destination, "days": request.days}},
        )
        weather = tool_results["get_weather"]
        record("1 · Weather Agent 판단", "completed", decision.reason, {
            "handoff_required": decision.handoff_required,
            "target_agent": decision.target_agent,
            "responsibility": decision.responsibility,
            "weather_cautions": decision.handoff_context.weather_cautions,
        })
        tracker.emit("weather_agent", "tool_completed", "completed", "Open-Meteo 날씨 조회 완료")
        tracker.emit("weather_agent", "handoff_proposed", "completed", "OpenAI가 Handoff를 제안했습니다.")
        if not decision.handoff_required:
            state.status = "rejected"
            state.handoff_status = "rejected"
            tracker.emit("weather_agent", "handoff_rejected", "rejected", decision.reason)
            tracker.save()
            return

        safe_context = {
            "destination": request.destination,
            "days": request.days,
            "weather_summary": weather,
            "weather_cautions": decision.handoff_context.weather_cautions,
            "transport": request.transport,
        }
        handoff = HandoffEnvelope(
            handoff_id=f"handoff-{run_id}", task_id=state.task_id, trace_id=run_id,
            from_agent="weather_agent", to_agent="itinerary_agent",
            responsibility=decision.responsibility or "실제 날씨를 반영한 일정을 작성한다.",
            context=safe_context, user_id=request.user_id,
        )
        record("2 · 인계 제안: weather_agent → itinerary_agent", "proposed",
               handoff.responsibility, handoff.model_dump())
        try:
            checked = validate_handoff(handoff, state, request.user_id)
        except Exception as error:
            record("3 · Guard 점검", "failed", str(error))
            raise
        record("3 · Guard 점검", "validated",
               "모든 Guard 검사를 통과했습니다. 아직 책임자는 weather_agent입니다.", {
                   "통과한 검사": ["proposed 상태", "사용자 일치", "현재 책임자 일치",
                               "중복 Handoff 없음", "허용 경로", "최대 인계 횟수",
                               "필수 Context 존재", "필수 값 비어 있지 않음",
                               "금지 Context Key 없음", "허용된 Context Key만 포함"],
               })
        record("4 · 점검 후 Itinerary Agent에 전달", "validated",
               "아래 검증된 Envelope가 일정 작성 요청에 포함됩니다. Guard는 Context를 변경하지 않습니다.",
               checked.model_dump())
        state.handoff_status = checked.status
        tracker.emit("handoff_guard", "handoff_validated", "completed", "경로와 최소 Context 검증 완료")

        itinerary_profile = get_agent("itinerary_agent")
        itinerary_prompt = f"""당신은 itinerary_agent입니다.
Goal: {itinerary_profile.goal}
Instructions: {itinerary_profile.instructions}
검증된 Handoff: {checked.model_dump_json()}
ItineraryResult 계약으로 반환하세요.
각 day_plans 항목은 해당 날짜의 구체적인 방문 활동, 날씨에 맞춘 조정, 이동 방법을 한국어 문장으로 설명하세요.
날짜만 쓰거나 확인되지 않은 장소·예약 정보를 만들지 마세요.
applied_constraints에는 weather_summary, transport, check_travel_details 같은 내부 이름 대신 실제 반영한 날씨와 이동 조건을 자연어로 적으세요."""
        tracker.emit("itinerary_agent", "handoff_acceptance_started", "started", "Gemma 응답 대기")
        for attempt in range(2):
            itinerary, _, _ = await run_agent(
                itinerary_profile, itinerary_prompt, ItineraryResult
            )
            try:
                validate_itinerary_content(itinerary, request)
                break
            except ValueError as error:
                if attempt:
                    raise
                record("5 · 일정 내용 점검", "retrying", str(error))
                itinerary_prompt += f"\n이전 응답은 일정으로 사용할 수 없습니다: {error} 구체적인 일정으로 다시 작성하세요."

        state.owner_agent = "itinerary_agent"
        state.hop_count = checked.hop_count
        state.processed_handoff_ids.append(checked.handoff_id)
        state.handoff_status = "transferred"
        tracker.emit("itinerary_agent", "ownership_transferred", "completed", "Itinerary Agent가 책임을 인수했습니다.")
        state.result = itinerary.model_dump()
        record("5 · 일정 결과와 책임 이전", "completed",
               "ItineraryResult 계약에 맞는 응답을 받은 뒤 itinerary_agent로 책임을 이전했습니다.",
               state.result)
        state.handoff_status = "completed"
        state.status = "completed"
        tracker.emit("itinerary_agent", "target_agent_completed", "completed", "일정 작성 완료")
        tracker.save()
    except Exception as error:
        state.status = "failed"
        state.handoff_status = "failed"
        state.error = f"{type(error).__name__}: {error}"
        tracker.emit(state.owner_agent, "handoff_failed", "failed", state.error)
        tracker.save()


def minimum_context_demo():
    full_state = {
        "destination": "부산", "days": 3, "weather_summary": "둘째 날 비",
        "weather_cautions": ["우산 준비"], "raw_messages": ["전체 대화"],
        "api_key": "전달 금지", "internal_prompt": "전달 금지",
    }
    allowed = {"destination", "days", "weather_summary", "weather_cautions"}
    selected = {key: value for key, value in full_state.items() if key in allowed}
    return {"full_keys": list(full_state), "selected_context": selected, "removed_keys": sorted(set(full_state) - allowed)}


def guard_cases_demo():
    return [
        {"case": "다른 사용자", "expected": "blocked"},
        {"case": "다른 task_id 또는 trace_id", "expected": "blocked"},
        {"case": "허용되지 않은 경로", "expected": "blocked"},
        {"case": "중첩 값을 포함한 민감 Context", "expected": "blocked"},
        {"case": "필수 Context 누락", "expected": "blocked"},
        {"case": "연속되지 않은 hop_count", "expected": "blocked"},
        {"case": "같은 handoff_id 재처리", "expected": "blocked"},
    ]
