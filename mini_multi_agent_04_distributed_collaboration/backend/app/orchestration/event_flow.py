"""Lab 08: 같은 Parallel + Join 구조를 온라인 행사 준비에 적용한다."""

import asyncio

from app.agents.registry import get_team
from app.orchestration.engine import RUNS, agent, trace
from app.schemas.contracts import CollaborationState


async def event_collaboration(message: str) -> dict[str, object]:
    """세 Worker를 동시에 실행하고 필수 결과가 있으면 행사안을 만듭니다."""
    team = get_team("event_collaboration_team")
    state = CollaborationState(
        task_id="event-001", status="running", current_step="parallel"
    )
    worker_ids = team["parallel_workers"]

    for agent_id in worker_ids:
        trace(state, agent_id, "agent_started", "started")

    responses = await asyncio.gather(
        *(agent(agent_id, message) for agent_id in worker_ids)
    )
    for agent_id, response in zip(worker_ids, responses):
        if response["error"]:
            state.errors[agent_id] = response["error"]
            state.failed_agents.append(agent_id)
            trace(state, agent_id, "agent_failed", "failed", response, response["error"])
        else:
            state.results[agent_id] = response["result"]
            state.completed_agents.append(agent_id)
            trace(state, agent_id, "agent_completed", "completed", response)

    missing_required = set(team["required_workers"]) - set(state.results)
    if missing_required:
        state.status = "failed"
        state.current_step = None
        trace(
            state,
            "join_guard_agent",
            "join_blocked",
            "blocked",
            error=f"필수 결과 누락: {sorted(missing_required)}",
        )
        result = {**state.model_dump(), "reason": "required_result_missing"}
        RUNS[state.run_id] = result
        return result

    state.current_step = "join"
    trace(state, "join_guard_agent", "join_completed", "completed")
    aggregator_id = team["aggregator"]
    response = await agent(aggregator_id, message, state.results)
    if response["error"]:
        state.status = "failed"
        state.errors[aggregator_id] = response["error"]
        state.failed_agents.append(aggregator_id)
        trace(state, aggregator_id, "agent_failed", "failed", response, response["error"])
    else:
        state.status = "completed"
        state.results[aggregator_id] = response["result"]
        state.completed_agents.append(aggregator_id)
        trace(state, aggregator_id, "agent_completed", "completed", response)

    state.current_step = None
    result = {**state.model_dump(), "reason": "all_required_results_joined"}
    RUNS[state.run_id] = result
    return result
