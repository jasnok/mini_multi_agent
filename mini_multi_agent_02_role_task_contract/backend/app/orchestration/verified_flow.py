from uuid import uuid4
from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.schemas.contracts import BudgetResult, MultiLlmRequest
from app.observability.tracker import RunTracker

async def run_multi_llm(request: MultiLlmRequest, tracker: RunTracker | None = None) -> dict[str, object]:
    results = []
    for agent_id in ("weather_agent", "place_agent", "budget_agent", "safety_agent"):
        results.append(await run_agent(get_agent(agent_id), request.message, tracker=tracker))
    count = sum(item["status"] == "completed" for item in results)
    return {"run_id": f"run-{uuid4().hex[:12]}", "status": "completed" if count == len(results) else "partial_failure", "success_count": count, "total_count": len(results), "results": results}

async def run_verified_flow(request: MultiLlmRequest, tracker: RunTracker | None = None) -> dict[str, object]:
    """Lab 08의 가장 작은 검증 결과 전달 예제입니다.

    01의 Sequential Pattern과 실행 모양은 비슷하지만, 02에서는 앞 Agent가 끝났다는 이유만으로
    다음 Agent를 실행하지 않습니다. BudgetResult 계약을 통과한 결과가 있을 때만 Itinerary
    Agent를 호출합니다. 날씨·장소·안전까지 합치는 전체 여행 Workflow는 이 Lab의 범위가
    아닙니다.
    """
    trace = [{"step": 1, "actor": "budget_agent", "action": "started"}]
    budget = await run_agent(get_agent("budget_agent"), request.message, tracker=tracker)
    if budget["result"] is None:
        trace.extend([{"step": 2, "actor": "contract_guard", "action": "budget_rejected"}, {"step": 3, "actor": "itinerary_agent", "action": "skipped"}])
        return {"run_id": f"run-{uuid4().hex[:12]}", "status": "failed", "budget": budget, "itinerary": None, "trace": trace}
    verified = BudgetResult.model_validate(budget["result"])
    if tracker:
        tracker.advance("contract_guard", "context_verified", "BudgetResult를 다음 Agent의 Context로 전달합니다.")
    trace.extend([{"step": 2, "actor": "contract_guard", "action": "budget_verified"}, {"step": 3, "actor": "itinerary_agent", "action": "started"}])
    itinerary = await run_agent(get_agent("itinerary_agent"), request.message, verified.model_dump(), tracker)
    trace.append({"step": 4, "actor": "contract_guard", "action": "itinerary_verified" if itinerary["result"] else "itinerary_rejected"})
    return {"run_id": f"run-{uuid4().hex[:12]}", "status": "completed" if itinerary["result"] else "failed", "budget": budget, "itinerary": itinerary, "trace": trace}


async def execute_tracked(run_id: str, flow_name: str, request: MultiLlmRequest) -> None:
    total_steps = 11 if flow_name == "multi-llm" else 6
    tracker = RunTracker(run_id, total_steps)
    tracker.start("실행 요청이 등록되어 첫 Agent를 준비하고 있습니다.")
    try:
        result = await (run_multi_llm(request, tracker) if flow_name == "multi-llm" else run_verified_flow(request, tracker))
        result["run_id"] = run_id
        if result["status"] == "completed":
            tracker.finish(result)
        else:
            tracker.fail("하나 이상의 Agent 또는 계약 검증이 실패했습니다.", result)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
