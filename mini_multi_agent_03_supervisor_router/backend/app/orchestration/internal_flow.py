"""Lab 08: 같은 Router 구조를 사내 요청 시나리오에 적용한다."""

from uuid import uuid4

from app.agents.registry import get_agent
from app.observability.tracker import RunTracker
from app.orchestration.engine import safe_agent
from app.schemas.workflow import InternalRouteDecision, MessageRequest, WorkerResult


async def run_internal_router_flow(request: MessageRequest, tracker=None) -> dict[str, object]:
    route_prompt = f"""당신은 internal_router_agent입니다. 요청을 직접 처리하지 마세요.
계정·권한은 account_agent, 노트북·장비는 equipment_agent,
회의실·사무실 시설은 facility_agent를 선택하세요.
판단할 정보가 부족하면 request_information과 필요한 정보를 반환하세요.
요청: {request.message}
InternalRouteDecision 계약으로 반환하세요."""
    route = await safe_agent(
        "internal_router_agent", route_prompt, InternalRouteDecision, tracker
    )
    trace = [{"step": 1, "actor": "internal_router_agent", "action": "route", "status": route["status"]}]
    if route["result"] is None:
        return {"run_id": f"run-{uuid4().hex[:12]}", "status": "failed", "route": route, "worker": None, "trace": trace}

    selected = route["result"]["selected_agent"]
    if selected == "request_information":
        trace.append({"step": 2, "actor": "internal_router_agent", "action": "request_information", "status": "completed"})
        return {"run_id": f"run-{uuid4().hex[:12]}", "status": "needs_information", "route": route, "worker": None, "trace": trace}

    profile = get_agent(selected)
    worker_prompt = f"""당신은 {selected}입니다.
Goal: {profile.goal}
Instructions: {profile.instructions}
요청: {request.message}
WorkerResult 계약으로 반환하고 agent_id는 {selected}로 작성하세요."""
    worker = await safe_agent(selected, worker_prompt, WorkerResult, tracker)
    trace.append({"step": 2, "actor": selected, "action": "execute", "status": worker["status"]})
    return {"run_id": f"run-{uuid4().hex[:12]}", "status": worker["status"], "route": route, "worker": worker, "trace": trace}


async def execute_internal_tracked(run_id: str, request: MessageRequest) -> None:
    tracker = RunTracker(run_id, 4)
    tracker.update("orchestrator", "queued", "사내 요청 실행을 등록했습니다.")
    try:
        result = await run_internal_router_flow(request, tracker)
        result["run_id"] = run_id
        if result["status"] in {"completed", "needs_information"}:
            tracker.finish(result)
        else:
            tracker.fail(f"종료 이유: {result['status']}", result)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
