"""
[통합 실행 시나리오]
사용자가 여행 요청을 보내면 Input Guard Agent가 LLM 호출 전에 공격 문구를 검사합니다.
Weather Agent에는 목적지와 일수만 전달하고, 권한 확인 뒤 Open-Meteo MCP를 호출합니다.
OpenAI Travel Agent가 실제 날씨로 초안을 만듭니다. Gemma가 답변을 정리한 뒤 Response Guard Agent가
최종 Policy를 검사합니다. 각 단계는 Redis에 기록되어 Frontend 폴링 화면에 표시됩니다.
"""

from __future__ import annotations

from uuid import uuid4

from app.agents.input_guard_agent import inspect_input_fields
from app.agents.response_guard_agent import inspect_response_payload
from app.agents.tool_guard_agent import authorize_tool, minimum_context
from app.agents.travel_agent import create_travel_draft, revise_final_answer
from app.mcp.client import call
from app.observability.tracker import GuardrailTracker
from app.schemas.contracts import GuardrailRunRequest


def new_run(request: GuardrailRunRequest) -> tuple[str, dict[str, object]]:
    run_id = str(uuid4())
    state: dict[str, object] = {
        "run_id": run_id,
        "status": "queued",
        "current_stage": "queued",
        "current_status": "waiting",
        "message": "Guardrail 실행을 기다리고 있습니다.",
        "progress": 0,
        "user_id": request.user_id,
        "result": None,
    }
    return run_id, state


async def run_guardrail_workflow(run_id: str, state: dict[str, object], request: GuardrailRunRequest) -> None:
    tracker = GuardrailTracker(run_id, state)
    state["status"] = "running"

    try:
        input_allowed, input_reason = inspect_input_fields({
            "destination": request.destination,
            "preferences": request.preferences,
            "user_message": request.user_message,
        })
        tracker.record("input_guard", "input_guard_agent", "allowed" if input_allowed else "blocked", input_reason)
        if not input_allowed:
            tracker.finish("blocked", {"blocked_at": "input_guard", "reason": input_reason})
            return

        full_context = {
            "destination": request.destination,
            "days": request.days,
            "preferences": request.preferences,
            "user_message": request.user_message,
            "internal_note": "다른 Agent에 전달하면 안 되는 운영 메모",
        }
        weather_context = minimum_context("weather_agent", full_context)
        tracker.record("context_guard", "weather_agent", "allowed", "Weather Agent에 최소 Context만 전달했습니다.", weather_context)

        authorize_tool("weather_agent", "get_weather")
        tracker.record("tool_guard", "weather_agent", "allowed", "get_weather MCP Tool 권한을 확인했습니다.")

        weather_arguments = {"city": weather_context["destination"], "days": weather_context["days"]}
        weather = await call("get_weather", weather_arguments, {"get_weather"})
        if weather.get("success") is False:
            raise RuntimeError(f"get_weather 조회 실패: {weather.get('error', '원인 미상')}")
        tracker.record("mcp_tool", "weather_agent", "completed", "Open-Meteo 실제 날씨를 조회했습니다.", {"source": weather.get("source")})

        travel_context = minimum_context("travel_agent", {**full_context, "weather": weather})
        draft, openai_trace = await create_travel_draft(travel_context)
        tracker.record("draft", "travel_agent", "completed", "OpenAI Travel Agent가 초안을 만들었습니다.", openai_trace)

        final_answer, gemma_trace = await revise_final_answer(draft)
        tracker.record("revision", "response_guard_agent", "completed", "Gemma가 사용자용 답변을 정리했습니다.", gemma_trace)

        response_allowed, response_reason = inspect_response_payload({
            "draft": draft.model_dump(),
            "final_answer": final_answer.model_dump(),
        })
        tracker.record("response_guard", "response_guard_agent", "allowed" if response_allowed else "blocked", response_reason)
        if not response_allowed:
            tracker.finish("blocked", {"blocked_at": "response_guard", "reason": response_reason})
            return

        tracker.finish("completed", {"draft": draft.model_dump(), "final_answer": final_answer.model_dump(), "weather": weather})
    except Exception as error:
        error_message = f"{type(error).__name__}: {error}"
        tracker.record("workflow", "guardrail_orchestrator", "failed", error_message)
        tracker.finish("failed", {"error": error_message})
