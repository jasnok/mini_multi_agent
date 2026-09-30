from uuid import uuid4

from pydantic import ValidationError

from app.agents.registry import get_agent
from app.agents.runtime import run_profile
from app.observability.tracker import RunTracker
from app.schemas.workflow import MessageRequest, SupervisorDecision, SupervisorRequest, SupportRouteDecision, WorkerResult


FULL_PLAN = ["analyst_agent", "developer_agent", "reviewer_agent"]


def rule_router_agent(message: str) -> SupportRouteDecision:
    """01에서 본 Router Pattern을 가장 단순한 Keyword 규칙으로 실행합니다."""
    routes = {
        "delivery_agent": ("배송", "택배", "도착"),
        "refund_agent": ("환불", "취소", "반품"),
        "technical_support_agent": ("로그인", "오류", "비밀번호"),
    }
    for agent_id, keywords in routes.items():
        if any(keyword in message for keyword in keywords):
            return SupportRouteDecision(selected_agent=agent_id, reason=f"{keywords} Keyword 규칙과 일치")
    return SupportRouteDecision(selected_agent="request_information", reason="담당자를 결정할 정보가 부족합니다.", missing_information=["배송·환불·기술지원 중 필요한 도움"])


def validate_route(payload: dict[str, object]) -> dict[str, object]:
    try:
        result = SupportRouteDecision.model_validate(payload)
        return {"valid": True, "result": result.model_dump(), "errors": []}
    except ValidationError as error:
        errors = [{"location": list(item["loc"]), "message": item["msg"], "type": item["type"]} for item in error.errors()]
        return {"valid": False, "result": None, "errors": errors}


async def safe_agent(agent_id: str, prompt: str, schema, tracker=None) -> dict[str, object]:
    return await run_profile(get_agent(agent_id), prompt, schema, tracker)


async def llm_router_flow(request: MessageRequest, tracker=None) -> dict[str, object]:
    """LLM Router는 선택만 하고 실제 고객지원 업무는 선택된 Worker가 수행합니다."""
    route_prompt = f"""당신은 router_agent입니다. 답변을 직접 작성하지 마세요.
배송 상태는 delivery_agent, 환불·취소는 refund_agent, 로그인·앱 오류는 technical_support_agent를 선택하세요.
판단할 수 없으면 request_information과 필요한 정보를 반환하세요.
요청: {request.message}
SupportRouteDecision 계약으로 반환하세요."""
    route = await safe_agent("router_agent", route_prompt, SupportRouteDecision, tracker)
    trace = [{"step": 1, "actor": "router_agent", "action": "route", "status": route["status"]}]
    if route["result"] is None:
        return {"run_id": f"run-{uuid4().hex[:12]}", "status": "failed", "route": route, "worker": None, "trace": trace}
    selected = route["result"]["selected_agent"]
    if selected == "request_information":
        trace.append({"step": 2, "actor": "router_agent", "action": "request_information", "status": "completed"})
        return {"run_id": f"run-{uuid4().hex[:12]}", "status": "needs_information", "route": route, "worker": None, "trace": trace}
    profile = get_agent(selected)
    worker_prompt = f"당신은 {selected}입니다. Goal: {profile.goal}\nInstructions: {profile.instructions}\n요청: {request.message}\nWorkerResult 계약으로 반환하고 agent_id는 {selected}로 작성하세요."
    worker = await safe_agent(selected, worker_prompt, WorkerResult, tracker)
    trace.append({"step": 2, "actor": selected, "action": "execute", "status": worker["status"]})
    return {"run_id": f"run-{uuid4().hex[:12]}", "status": worker["status"], "route": route, "worker": worker, "trace": trace}


async def supervisor_decision(request: SupervisorRequest) -> dict[str, object]:
    """완료된 작업 수로 지금 허용된 다음 Agent 하나를 계산하고 LLM 결정과 비교합니다."""
    state = {"completed_agents": request.completed_agents, "outputs": request.outputs}
    expected = FULL_PLAN[len(request.completed_agents)] if len(request.completed_agents) < len(FULL_PLAN) else "finish"
    prompt = f"""당신은 supervisor_agent입니다. Worker 업무를 직접 수행하지 마세요.
허용 순서: analyst_agent → developer_agent → reviewer_agent → finish
현재 State: {state}
현재 허용된 다음 행동: {expected}
요청: {request.message}
SupervisorDecision 계약으로 반환하세요."""
    result = await safe_agent("supervisor_agent", prompt, SupervisorDecision)
    return {"expected_next": expected, "decision": result, "transition_valid": bool(result["result"] and result["result"]["next_agent"] == expected)}


async def supervisor_loop(message: str, plan: list[str], max_llm_calls: int, tracker=None) -> dict[str, object]:
    """01에서 미리 본 Supervisor Pattern을 State와 최대 호출 수로 반복 실행합니다."""
    state: dict[str, object] = {"completed_agents": [], "outputs": {}}
    trace: list[dict[str, object]] = []
    while len(trace) < max_llm_calls:
        completed = state["completed_agents"]
        expected = plan[len(completed)] if len(completed) < len(plan) else "finish"
        prompt = f"""당신은 supervisor_agent입니다. 직접 Worker 업무를 하지 마세요.
허용 작업 순서: {' → '.join(plan)} → finish
현재 State: {state}
현재 허용된 다음 행동: {expected}
요청: {message}
SupervisorDecision 계약으로 반환하세요."""
        decision = await safe_agent("supervisor_agent", prompt, SupervisorDecision, tracker)
        trace.append({"step": len(trace) + 1, "action": "select", **decision})
        if decision["result"] is None:
            return {"status": "failed", "reason": "supervisor_failed", "state": state, "trace": trace}
        selected = decision["result"]["next_agent"]
        if selected != expected:
            return {"status": "blocked", "reason": "invalid_transition", "state": state, "trace": trace}
        if selected == "finish":
            return {"status": "completed", "reason": "all_workers_completed", "state": state, "trace": trace}
        if selected in completed:
            return {"status": "blocked", "reason": "duplicate_worker", "state": state, "trace": trace}
        if len(trace) >= max_llm_calls:
            break
        profile = get_agent(selected)
        worker_prompt = f"당신은 {selected}입니다. Goal: {profile.goal}\nInstructions: {profile.instructions}\n요청: {message}\n이전 결과: {state['outputs']}\nWorkerResult 계약으로 반환하세요."
        worker = await safe_agent(selected, worker_prompt, WorkerResult, tracker)
        trace.append({"step": len(trace) + 1, "action": "execute", **worker})
        if worker["result"] is None:
            return {"status": "failed", "reason": "worker_failed", "state": state, "trace": trace}
        completed.append(selected)
        state["outputs"][selected] = worker["result"]
    return {"status": "failed", "reason": "max_llm_calls", "state": state, "trace": trace}


async def small_supervisor_loop(request: MessageRequest) -> dict[str, object]:
    return await supervisor_loop(request.message, ["analyst_agent", "reviewer_agent"], 5)


async def full_supervisor_team(request: MessageRequest) -> dict[str, object]:
    return await supervisor_loop(request.message, FULL_PLAN, 7)


async def execute_tracked(run_id: str, flow_name: str, request: MessageRequest) -> None:
    total_steps = {"router": 4, "supervisor-loop": 5, "supervisor-team": 8}[flow_name]
    tracker = RunTracker(run_id, total_steps)
    tracker.update("orchestrator", "queued", "실행이 등록되었습니다.")
    try:
        if flow_name == "router":
            result = await llm_router_flow(request, tracker)
        elif flow_name == "supervisor-loop":
            result = await supervisor_loop(
                request.message, ["analyst_agent", "reviewer_agent"], 5, tracker
            )
        else:
            result = await supervisor_loop(request.message, FULL_PLAN, 7, tracker)
        result["run_id"] = run_id
        if result["status"] == "completed": tracker.finish(result)
        else: tracker.fail(f"종료 이유: {result.get('reason', result['status'])}", result)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
