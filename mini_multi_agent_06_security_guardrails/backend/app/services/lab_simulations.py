"""Labs 01~07: 외부 서비스 없이 입력, 가상 답변, Guard 결과를 비교합니다."""

from threading import Lock
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.agents.input_guard_agent import inspect_input
from app.agents.response_guard_agent import inspect_response
from app.agents.tool_guard_agent import authorize_tool, minimum_context


# 06번 수업용 메모리 저장소입니다. 서버 재시작 시 초기화되며 실제 서비스에는 쓰지 않습니다.
_practice_saves: dict[tuple[str, str, str], dict[str, object]] = {}
_practice_saves_lock = Lock()


class PracticeTravelRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=50)
    days: int = Field(ge=1, le=14)
    people: int = Field(ge=1, le=20)
    user_message: str = Field(min_length=1, max_length=500)

    @field_validator("destination")
    @classmethod
    def destination_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("여행지는 공백일 수 없습니다.")
        return value.strip()


def simulate_lab(lab_id: str, values: dict[str, object]) -> dict[str, object]:
    """하나의 Lab만 실행하고, 화면에 표시할 단계별 결과를 반환합니다."""
    steps: list[dict[str, str]] = []

    def record(stage: str, status: str, detail: str) -> None:
        steps.append({"stage": stage, "status": status, "detail": detail})

    if lab_id == "01":
        message = str(values.get("message", ""))
        allowed, reason = inspect_input(message)
        record("사용자 입력", "received", message)
        record("Prompt Guard", "allowed" if allowed else "blocked", reason)
        answer = f"{message} 요청을 바탕으로 여행 일정을 제안합니다." if allowed else None
        record("가상 LLM 답변", "shown" if allowed else "skipped", answer or "차단되어 생성하지 않았습니다.")
        return {"allowed": allowed, "reason": reason, "mock_answer": answer, "steps": steps}

    if lab_id == "02":
        try:
            request = PracticeTravelRequest.model_validate(values)
        except ValidationError as error:
            issues = [f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors()]
            record("Pydantic 입력 검증", "blocked", "; ".join(issues))
            record("가상 LLM 답변", "skipped", "검증된 입력이 없어 생성하지 않았습니다.")
            return {"allowed": False, "reason": "입력 형식 또는 범위가 맞지 않습니다.", "issues": issues, "mock_answer": None, "steps": steps}
        record("Pydantic 입력 검증", "allowed", str(request.model_dump()))
        answer = f"{request.destination} {request.days}일, {request.people}명 여행 일정을 제안합니다."
        record("가상 LLM 답변", "shown", answer)
        return {"allowed": True, "reason": "검증된 값만 다음 단계로 전달했습니다.", "mock_answer": answer, "steps": steps}

    if lab_id == "03":
        answer = str(values.get("answer", ""))
        allowed, reason = inspect_response(answer)
        record("가상 LLM 답변", "created", answer)
        record("Response Guard", "allowed" if allowed else "blocked", reason)
        record("사용자에게 전달", "shown" if allowed else "skipped", answer if allowed else "위험한 답변을 전달하지 않았습니다.")
        return {"allowed": allowed, "reason": reason, "mock_answer": answer, "displayed_answer": answer if allowed else None, "steps": steps}

    if lab_id == "04":
        agent = str(values.get("agent", "weather_agent"))
        tool = str(values.get("tool", "get_weather"))
        record("가상 Agent의 Tool 요청", "created", f"{agent} → {tool}")
        try:
            authorize_tool(agent, tool)
            allowed, reason = True, "서버의 Agent별 Tool 허용 목록을 통과했습니다."
        except PermissionError as error:
            allowed, reason = False, str(error)
        record("Tool Guard", "allowed" if allowed else "blocked", reason)
        answer = "수업용 날씨: 부산 맑음" if allowed and tool == "get_weather" else None
        record("가상 Tool 결과", "shown" if answer else "skipped", answer or "Tool은 실행되지 않았습니다.")
        return {"allowed": allowed, "reason": reason, "mock_answer": answer, "steps": steps}

    if lab_id == "05":
        task_id = str(values.get("task_id", "travel-001"))
        approval_task_id = str(values.get("approval_task_id", ""))
        user_id = str(values.get("user_id", "user-101"))
        approval_user_id = str(values.get("approval_user_id", ""))
        approval_tool = str(values.get("approval_tool", ""))
        approved = bool(values.get("approved", False))
        record("가상 Agent의 저장 요청", "created", f"task={task_id}, user={user_id}, tool=save_itinerary")
        if not approved:
            reason = "사용자 승인이 없습니다. 일정 저장을 실행할 수 없습니다."
        elif task_id != approval_task_id:
            reason = f"승인된 작업 ID({approval_task_id})가 현재 작업 ID({task_id})와 다릅니다."
        elif user_id != approval_user_id:
            reason = f"승인 사용자 ID({approval_user_id})가 요청 사용자 ID({user_id})와 다릅니다."
        elif approval_tool != "save_itinerary":
            reason = "승인된 Tool이 일정 저장 Tool(save_itinerary)과 다릅니다."
        else:
            reason = "현재 작업·사용자·Tool과 일치하는 승인입니다."
        allowed = approved and (task_id, user_id, "save_itinerary") == (approval_task_id, approval_user_id, approval_tool)
        if allowed:
            authorize_tool("itinerary_agent", "save_itinerary", approved=True)
        record("Approval Guard", "allowed" if allowed else "blocked", reason)
        answer = "수업용 일정 저장 완료" if allowed else None
        record("가상 저장 결과", "shown" if allowed else "skipped", answer or "저장하지 않았습니다.")
        return {"allowed": allowed, "reason": reason, "mock_answer": answer, "steps": steps}

    if lab_id == "06":
        session_id = str(values.get("session_id", "classroom-demo"))
        user_id = str(values.get("user_id", "user-101"))
        key = str(values.get("idempotency_key", "travel-save-v1"))
        title = str(values.get("title", "부산 여행"))
        claim = (session_id, user_id, key)
        with _practice_saves_lock:
            if claim in _practice_saves:
                saved = _practice_saves[claim]
                saved["click_count"] = int(saved["click_count"]) + 1
                decision = "reused"
            else:
                saved = {"result": {"itinerary_id": f"itinerary-{uuid4().hex[:8]}", "title": title}, "click_count": 1}
                _practice_saves[claim] = saved
                decision = "executed"
            result = dict(saved["result"])
            click_count = int(saved["click_count"])
        record("이번 저장 클릭", decision, f"사용자={user_id}, 키={key}, 결과={result}")
        record("실제 저장 횟수", "1", "같은 키로 다시 눌러도 첫 저장 결과를 재사용합니다.")
        reason = "처음 요청이므로 저장했습니다." if decision == "executed" else "같은 사용자와 키의 이전 저장 결과를 재사용했습니다."
        return {"allowed": True, "reason": reason, "mock_answer": result, "save_count": 1, "click_count": click_count, "decision": decision, "steps": steps}

    if lab_id == "07":
        context = {
            "destination": str(values.get("destination", "부산")),
            "days": int(values.get("days", 3)),
            "preferences": ["바다", "맛집"],
            "weather": {"condition": "맑음"},
            "internal_note": str(values.get("internal_note", "운영자 전용 메모")),
        }
        weather_context = minimum_context("weather_agent", context)
        travel_context = minimum_context("travel_agent", context)
        record("Supervisor 전체 Context", "created", str(context))
        record("Weather Agent", "filtered", str(weather_context))
        record("Travel Agent", "filtered", str(travel_context))
        expected_user = str(values.get("user_id", "user-101"))
        tool_user = str(values.get("tool_user_id", "user-101"))
        allowed = expected_user == tool_user
        reason = "같은 사용자 요청입니다." if allowed else "다른 사용자 ID의 Tool 요청을 차단했습니다."
        record("Tool 요청의 사용자 확인", "allowed" if allowed else "blocked", reason)
        answer = f"{travel_context['destination']} 여행 초안을 만듭니다." if allowed else None
        return {"allowed": allowed, "reason": reason, "mock_answer": answer, "weather_context": weather_context, "travel_context": travel_context, "steps": steps}

    raise ValueError(f"지원하지 않는 Lab입니다: {lab_id}")
