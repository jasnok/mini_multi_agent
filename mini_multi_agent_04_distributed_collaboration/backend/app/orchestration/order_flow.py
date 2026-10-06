"""Lab 11: parallel checks followed by a Python Join Guard."""
import asyncio

from app.agents.registry import get_team
from app.orchestration.engine import RUNS, agent, trace
from app.schemas.contracts import CollaborationState


async def order_collaboration(message: str, fail_agent: str | None = None) -> dict[str, object]:
    """모의 재고·결제·쿠폰 결과를 모아 필수 결과가 있을 때만 안내를 만듭니다."""
    team = get_team("order_confirmation_team")
    workers = team["parallel_workers"]
    if fail_agent is not None and fail_agent not in workers:
        raise ValueError("실패를 지정할 수 없는 Agent입니다.")
    state = CollaborationState(task_id="order-demo-001", status="running", current_step="parallel")
    for worker in workers:
        trace(state, worker, "agent_started", "started")

    async def run_worker(worker: str):
        if worker == fail_agent:
            return {"result": None, "error": "교육용 실패 주입", "provider": None,
                    "model": None, "latency_ms": None}
        return await agent(worker, message)

    responses = await asyncio.gather(*(run_worker(worker) for worker in workers))
    for worker, response in zip(workers, responses):
        result = response.get("result")
        if response.get("error") or not result or not result.get("completed", False):
            error = response.get("error") or "완료된 Agent 결과가 없습니다."
            state.errors[worker] = error
            state.failed_agents.append(worker)
            trace(state, worker, "agent_failed", "failed", response, error)
        else:
            state.results[worker] = result
            state.completed_agents.append(worker)
            trace(state, worker, "agent_completed", "completed", response)

    missing = [worker for worker in team["required_workers"] if worker not in state.results]
    if missing:
        state.status = "failed"
        state.current_step = None
        trace(state, "join_guard_agent", "join_blocked", "blocked",
              error=f"필수 결과 누락: {missing}")
        output = {**state.model_dump(), "reason": "required_result_missing",
                  "join_guard": {"passed": False, "missing_required": missing,
                                 "optional_failed": [w for w in team["optional_workers"] if w in state.failed_agents]}}
        RUNS[state.run_id] = output
        return output

    trace(state, "join_guard_agent", "join_completed", "completed")
    state.current_step = "join"
    aggregator = team["aggregator"]
    response = await agent(aggregator, message, state.results)
    result = response.get("result")
    if response.get("error") or not result or not result.get("completed", False):
        error = response.get("error") or "완료된 주문 안내 결과가 없습니다."
        state.status = "failed"
        state.errors[aggregator] = error
        state.failed_agents.append(aggregator)
        trace(state, aggregator, "agent_failed", "failed", response, error)
    else:
        state.status = "completed"
        state.results[aggregator] = result
        state.completed_agents.append(aggregator)
        trace(state, aggregator, "agent_completed", "completed", response)
    state.current_step = None
    output = {**state.model_dump(), "reason": "all_required_results_joined" if state.status == "completed" else "aggregator_failed",
              "join_guard": {"passed": True, "missing_required": [],
                             "optional_failed": [w for w in team["optional_workers"] if w in state.failed_agents]}}
    RUNS[state.run_id] = output
    return output
