"""Lab 09: 여행 Agent들의 순차 협업을 LangGraph로 실행합니다.

날씨 → 장소 → 숙소 → 예산 → 가이드 순서로 실행하며, 각 단계가 실패하면
이후 Agent를 실행하지 않습니다.
"""

from typing import TypedDict

from app.orchestration.engine import agent
from app.schemas.contracts import new_run_id


SEQUENTIAL_WORKERS = ("weather_agent", "place_agent", "lodging_agent", "budget_agent")
GUIDE_AGENT = "itinerary_agent"


class TravelGraphState(TypedDict, total=False):
    message: str
    weather_agent: dict
    place_agent: dict
    lodging_agent: dict
    budget_agent: dict
    itinerary_agent: dict


def completed_context(state: TravelGraphState, before_agent: str | None = None) -> dict:
    """현재 단계보다 먼저 완료된 Agent 결과만 다음 Context로 만듭니다."""
    context = {}
    for agent_id in SEQUENTIAL_WORKERS:
        if agent_id == before_agent:
            break
        response = state.get(agent_id, {})
        if response.get("result"):
            context[agent_id] = response["result"]
    return context


def route_after(agent_id: str):
    """현재 Agent가 성공했을 때만 다음 단계로 이동하는 Guard를 만듭니다."""
    def select(state: TravelGraphState) -> str:
        return "continue" if state.get(agent_id, {}).get("result") else "stop"
    return select


def build_travel_graph():
    """날씨 → 장소 → 숙소 → 예산 → 가이드 순차 그래프를 만듭니다."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(TravelGraphState)

    def create_worker_node(agent_id: str):
        async def run_worker(state: TravelGraphState) -> dict:
            context = completed_context(state, before_agent=agent_id)
            return {agent_id: await agent(agent_id, state["message"], context or None)}
        return run_worker

    for agent_id in SEQUENTIAL_WORKERS:
        graph.add_node(agent_id, create_worker_node(agent_id))

    async def create_guide(state: TravelGraphState) -> dict:
        return {GUIDE_AGENT: await agent(GUIDE_AGENT, state["message"], completed_context(state))}

    graph.add_node(GUIDE_AGENT, create_guide)
    graph.add_edge(START, SEQUENTIAL_WORKERS[0])

    next_nodes = (*SEQUENTIAL_WORKERS[1:], GUIDE_AGENT)
    for current_agent, next_agent in zip(SEQUENTIAL_WORKERS, next_nodes):
        graph.add_conditional_edges(
            current_agent,
            route_after(current_agent),
            {"continue": next_agent, "stop": END},
        )

    graph.add_edge(GUIDE_AGENT, END)
    return graph.compile()


async def run_langgraph_travel(message: str) -> dict:
    """순차 여행 그래프를 실행하고 API 응답과 Trace를 정리합니다."""
    state: TravelGraphState = {"message": message}
    trace: list[dict] = []

    async for update in build_travel_graph().astream(state, stream_mode="updates"):
        for node, values in update.items():
            if not values:
                continue
            state.update(values)
            response = values[node]
            trace.append({"step": len(trace) + 1, "actor": node, "action": "agent_started", "status": "started"})

            succeeded = bool(response.get("result"))
            details = {"context_agents": list(completed_context(state, before_agent=node))}
            if response.get("error"):
                details["error"] = response["error"]
            trace.append({
                "step": len(trace) + 1,
                "actor": node,
                "action": "agent_completed" if succeeded else "agent_failed",
                "status": "completed" if succeeded else "failed",
                "provider": response.get("provider"),
                "model": response.get("model"),
                "latency_ms": response.get("latency_ms"),
                "details": details,
            })

    results = {}
    failed = []
    for agent_id in (*SEQUENTIAL_WORKERS, GUIDE_AGENT):
        response = state.get(agent_id)
        if not response:
            continue
        if response.get("result"):
            results[agent_id] = response["result"]
        else:
            failed.append(agent_id)

    guide_completed = GUIDE_AGENT in results
    failed_agent = failed[0] if failed else None
    return {
        "run_id": new_run_id(),
        "status": "completed" if guide_completed else "failed",
        "reason": None if guide_completed else f"{failed_agent}_failed" if failed_agent else "guide_not_completed",
        "graph": "sequential_travel_guide_graph",
        "completed_agents": list(results),
        "failed_agents": failed,
        "missing_required": failed,
        "results": results,
        "trace": trace,
    }
