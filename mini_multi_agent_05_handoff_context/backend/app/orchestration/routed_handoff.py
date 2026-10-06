"""Lab 08: one router, three guarded Handoff routes."""
from uuid import uuid4

from app.agents.registry import get_agent, get_route
from app.agents.runtime import run_agent
from app.orchestration.guards import validate_handoff
from app.schemas.contracts import (
    AccessSupportResult, AccountSupportResult, DeviceSupportResult,
    HandoffEnvelope, HandoffState, RoutedSupportDecision, RoutedSupportRequest,
)

RESULT_CONTRACTS = {
    "account_support_agent": AccountSupportResult,
    "device_support_agent": DeviceSupportResult,
    "access_support_agent": AccessSupportResult,
}


def route_blueprints():
    """Show the actual YAML route requirements in the teaching UI."""
    return [
        {"target_agent": agent, "required_context": get_route("support_router", agent)["required_context"],
         "optional_context": get_route("support_router", agent)["optional_context"],
         "output_contract": contract.__name__}
        for agent, contract in RESULT_CONTRACTS.items()
    ]


async def run_routed_handoff(request: RoutedSupportRequest) -> dict[str, object]:
    state = HandoffState(run_id=f"run-{uuid4().hex[:12]}", task_id="routed-it-001",
                         owner_agent="support_router", status="running")
    decision = None
    safe_context = None

    def record(title, status, message, data=None):
        state.trace.append({"title": title, "status": status, "message": message,
                            "data": data, "owner_agent": state.owner_agent})

    def response():
        return {**state.model_dump(), "decision": decision.model_dump() if decision else None,
                "safe_context": safe_context}

    record("1 · 요청 접수", "received", "라우터가 사내 IT 요청을 받았습니다.", request.model_dump())
    try:
        router = get_agent("support_router")
        decision, _, _ = await run_agent(
            router,
            f"당신은 support_router입니다. Goal: {router.goal}\nInstructions: {router.instructions}\n"
            f"요청: {request.model_dump_json()}\nRoutedSupportDecision 계약으로 인계 대상, 이유와 책임을 반환하세요.",
            RoutedSupportDecision,
        )
        record("2 · 라우터 판단 · RoutedSupportDecision", "completed", decision.reason, decision.model_dump())
        if decision.target_agent not in RESULT_CONTRACTS:
            raise ValueError("지원하지 않는 인계 대상입니다.")
        route = get_route("support_router", decision.target_agent)
        values = request.model_dump()
        safe_context = {key: values[key] for key in route["required_context"] + route["optional_context"]
                        if values.get(key) not in (None, "")}
        handoff = HandoffEnvelope(
            handoff_id=f"handoff-{state.run_id}", task_id=state.task_id, trace_id=state.run_id,
            from_agent="support_router", to_agent=decision.target_agent,
            responsibility=decision.responsibility, context=safe_context, user_id=request.employee_id,
        )
        record("3 · 선택된 경로의 HandoffEnvelope", "proposed",
               f"{decision.target_agent}에 필요한 Context만 담았습니다.", handoff.model_dump())
        try:
            checked = validate_handoff(handoff, state, request.employee_id)
        except Exception as error:
            record("4 · Guard 점검", "failed", str(error), {
                "required_context": route["required_context"],
                "optional_context": route["optional_context"],
            })
            raise
        state.handoff_status = checked.status
        record("4 · Guard 점검", "validated", "경로, 책임자, 사용자, 필수·허용 Context와 중복 ID를 검증했습니다.", {
            "required_context": route["required_context"],
            "optional_context": route["optional_context"],
            "checked_context_keys": list(checked.context),
        })
        record("5 · 검증 후 대상 Agent에 전달", "validated", "검증된 Envelope를 대상 Agent의 입력으로 전달합니다.",
               checked.model_dump())
        profile = get_agent(decision.target_agent)
        contract = RESULT_CONTRACTS[decision.target_agent]
        result, _, _ = await run_agent(
            profile,
            f"당신은 {profile.agent_id}입니다. Goal: {profile.goal}\nInstructions: {profile.instructions}\n"
            f"검증된 Handoff: {checked.model_dump_json()}\n{contract.__name__} 계약으로 실제 확인 절차를 반환하세요.",
            contract,
        )
        state.owner_agent = decision.target_agent
        state.hop_count = checked.hop_count
        state.processed_handoff_ids.append(checked.handoff_id)
        state.handoff_status = "completed"
        state.status = "completed"
        state.result = result.model_dump()
        record("6 · 대상 Agent 결과와 책임 이전", "completed",
               f"{contract.__name__} 결과를 받은 뒤 책임을 이전했습니다.", state.result)
    except Exception as error:
        state.status = "failed"
        state.handoff_status = "failed"
        state.error = f"{type(error).__name__}: {error}"
        record("실행 실패", "failed", state.error)
    return response()
