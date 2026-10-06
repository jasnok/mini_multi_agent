"""Lab 10: 날씨에 따라 장소를 선택하고 전체 비용을 검증합니다.

실행 순서
1. 사용자가 강수확률을 입력했는지 확인합니다.
2. 입력값이 없으면 날씨 Agent를 실행해 강수확률을 구합니다.
3. 비가 올 가능성이 높으면 실내, 낮으면 실외 장소를 선택합니다.
4. 선택한 장소의 입장료를 여행 예산에 더합니다.
5. 계산된 비용이 사용자의 예산 한도 안에 있는지 확인합니다.
"""

from typing import TypedDict

from app.orchestration.engine import agent, tool_arguments
from app.schemas.contracts import new_run_id


class DecisionState(TypedDict, total=False):
    """그래프의 모든 노드가 함께 사용하는 상태입니다."""

    message: str
    city: str
    days: int
    people: int
    budget_limit: int
    rain_threshold: int
    rain_probability_override: int | None
    weather_source: str
    weather_agent: dict
    weather_risk: str
    precipitation_probability: int
    place_agent: dict
    selected_place: dict
    budget_agent: dict
    budget: dict
    error: str


def select_weather_path(state: DecisionState) -> str:
    """사용자 입력과 실시간 조회 중 어떤 날씨 경로를 사용할지 선택합니다."""
    if state.get("rain_probability_override") is not None:
        return "manual"
    return "live"


def select_place_path(state: DecisionState) -> str:
    """날씨 판단 결과에 맞는 장소 경로를 선택합니다."""
    if state.get("error"):
        return "stop"
    return state["weather_risk"]


def select_budget_path(state: DecisionState) -> str:
    """장소 선택이 성공했을 때만 예산 계산으로 이동합니다."""
    if state.get("error"):
        return "stop"
    return "budget"


def place_sort_key(place: dict) -> tuple[int, str]:
    """장소를 비용이 낮은 순서, 이름 순서로 정렬하기 위한 기준입니다."""
    return int(place["estimated_cost"]), place["name"]


def extract_inputs(message: str) -> dict | None:
    """사용자 문장에서 도시, 여행 일수, 인원을 추출합니다."""
    budget_args = tool_arguments("calculate_budget", message)
    if budget_args:
        return budget_args
    return None


def weather_probability(response: dict) -> int:
    """날씨 Tool 응답에서 가장 높은 강수확률을 반환합니다."""
    tool = response.get("tool_context", {}).get("get_weather", {})
    if not tool.get("success"):
        raise ValueError(tool.get("error") or "날씨 조회 결과가 없습니다.")

    values = tool.get("forecast", {}).get("precipitation_probability_max") or []
    if not values:
        raise ValueError("강수확률이 없어 장소 경로를 결정할 수 없습니다.")

    probabilities = []
    for value in values:
        if value is None:
            raise ValueError("강수확률이 없어 장소 경로를 결정할 수 없습니다.")
        probabilities.append(int(value))

    return max(probabilities)


def choose_place(response: dict, *, indoor: bool) -> dict:
    """날씨 조건에 맞는 장소 중 비용이 가장 낮은 장소를 선택합니다."""
    tool = response.get("tool_context", {}).get("search_places", {})
    if not tool.get("success"):
        raise ValueError("장소 조회 결과가 없습니다.")

    places = tool.get("places", [])
    candidates = []

    for place in places:
        if "is_indoor" not in place or "estimated_cost" not in place:
            raise ValueError(
                "장소 Tool 응답에 실내·실외/예상 비용 필드가 없습니다. "
                "MCP 서버를 최신 코드로 재시작해 주세요."
            )
        if place.get("is_indoor") is indoor:
            candidates.append(place)

    if not candidates:
        raise ValueError("해당 날씨에 맞는 장소 후보가 없습니다.")

    return min(candidates, key=place_sort_key)


def calculate_total(response: dict, place: dict, people: int, budget_limit: int) -> dict:
    """기본 여행비와 장소 입장료를 더해 전체 예상 비용을 계산합니다."""
    reference = response.get("tool_context", {}).get("calculate_budget", {})
    if not reference.get("success"):
        raise ValueError(reference.get("error") or "예산 기준 조회 결과가 없습니다.")
    base = int(reference["total"])
    admission = int(place["estimated_cost"]) * people
    estimate = base + admission
    return {
        "base_travel_cost": base,
        "place_cost_per_person": int(place["estimated_cost"]),
        "place_cost_total": admission,
        "estimated_total": estimate,
        "budget_limit": budget_limit,
        "remaining": budget_limit - estimate,
        "within_budget": estimate <= budget_limit,
        "currency": "KRW",
    }


def build_weather_place_budget_graph():
    """날씨 판단 → 장소 선택 → 예산 계산 그래프를 만듭니다."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(DecisionState)

    async def weather_node(state: DecisionState) -> dict:
        """날씨 Agent를 실행합니다."""
        response = await agent("weather_agent", state["message"])
        result = {"weather_agent": response}
        if response.get("error"):
            result["error"] = response["error"]
        return result

    def weather_input(state: DecisionState) -> dict:
        """사용자가 입력한 강수확률을 그래프 상태에 저장합니다."""
        return {
            "precipitation_probability": state["rain_probability_override"],
            "weather_source": "user_input",
        }

    def weather_guard(state: DecisionState) -> dict:
        """강수확률을 확인하고 비 또는 맑음 경로를 결정합니다."""
        if state.get("rain_probability_override") is not None:
            probability = state["rain_probability_override"]
            source = "user_input"
        else:
            if state["weather_agent"].get("error"):
                return {"error": state["weather_agent"]["error"]}
            try:
                probability = weather_probability(state["weather_agent"])
            except ValueError as error:
                return {"error": str(error)}
            source = "open-meteo"

        if probability >= state["rain_threshold"]:
            weather_risk = "rain"
        else:
            weather_risk = "dry"

        return {
            "precipitation_probability": probability,
            "weather_source": source,
            "weather_risk": weather_risk,
        }

    def create_place_node(indoor: bool):
        """실내 또는 실외 장소를 찾는 노드 함수를 생성합니다."""

        async def run_place_agent(state: DecisionState) -> dict:
            if indoor:
                environment = "실내"
            else:
                environment = "실외"

            response = await agent(
                "place_agent",
                state["message"],
                {
                    "weather_risk": state["weather_risk"],
                    "required_environment": environment,
                },
            )
            if response.get("error"):
                return {"place_agent": response, "error": response["error"]}

            try:
                place = choose_place(response, indoor=indoor)
            except ValueError as error:
                return {"place_agent": response, "error": str(error)}

            return {"place_agent": response, "selected_place": place}

        return run_place_agent

    async def budget_node(state: DecisionState) -> dict:
        """선택한 장소를 포함한 전체 여행 비용을 계산합니다."""
        response = await agent(
            "budget_agent", state["message"],
            {"selected_place": state["selected_place"]},
        )
        if response.get("error"):
            return {"budget_agent": response, "error": response["error"]}
        try:
            budget = calculate_total(
                response, state["selected_place"], state["people"], state["budget_limit"]
            )
        except ValueError as error:
            return {"budget_agent": response, "error": str(error)}
        return {"budget_agent": response, "budget": budget}

    graph.add_node("weather_agent", weather_node)
    graph.add_node("weather_input", weather_input)
    graph.add_node("weather_guard", weather_guard)
    graph.add_node("indoor_place", create_place_node(True))
    graph.add_node("outdoor_place", create_place_node(False))
    graph.add_node("budget_agent", budget_node)

    # 강수확률 직접 입력 여부에 따라 시작 경로가 달라집니다.
    graph.add_conditional_edges(
        START,
        select_weather_path,
        {"manual": "weather_input", "live": "weather_agent"},
    )
    graph.add_edge("weather_input", "weather_guard")
    graph.add_edge("weather_agent", "weather_guard")

    # 날씨가 비면 실내 장소, 맑으면 실외 장소를 찾습니다.
    graph.add_conditional_edges(
        "weather_guard",
        select_place_path,
        {"rain": "indoor_place", "dry": "outdoor_place", "stop": END},
    )

    # 장소 선택이 성공한 경우에만 예산을 계산합니다.
    for node in ("indoor_place", "outdoor_place"):
        graph.add_conditional_edges(
            node,
            select_budget_path,
            {"budget": "budget_agent", "stop": END},
        )
    graph.add_edge("budget_agent", END)
    return graph.compile()


async def run_weather_place_budget(
    message: str,
    budget_limit: int,
    rain_threshold: int = 50,
    rain_probability_override: int | None = None,
) -> dict:
    """그래프를 실행하고 실행 과정과 결과를 API 응답으로 반환합니다."""
    inputs = extract_inputs(message)
    if inputs is None:
        return {
            "run_id": new_run_id(),
            "status": "needs_information",
            "reason": "city_days_people_required",
            "error": "지원 도시(서울·부산·제주), 여행 일수와 인원을 입력해 주세요.",
            "trace": [],
            "results": {},
        }

    state: DecisionState = {
        "message": message,
        "budget_limit": budget_limit,
        "rain_threshold": rain_threshold,
        "rain_probability_override": rain_probability_override,
    }
    state.update(inputs)

    trace = []
    async for update in build_weather_place_budget_graph().astream(state, stream_mode="updates"):
        for node, values in update.items():
            if not values:
                continue

            state.update(values)

            if values.get("error"):
                action = "failed"
                node_status = "failed"
            else:
                action = "completed"
                node_status = "completed"

            details = {}
            detail_keys = (
                "weather_risk",
                "precipitation_probability",
                "selected_place",
                "budget",
                "error",
            )
            for key in detail_keys:
                if key in values:
                    details[key] = values[key]

            trace.append({
                "step": len(trace) + 1,
                "actor": node,
                "action": action,
                "status": node_status,
                "details": details,
            })

    budget = state.get("budget")

    if state.get("error"):
        status = "failed"
    elif budget and budget["within_budget"]:
        status = "completed"
    else:
        status = "over_budget"

    results = {}
    failed_agents = []
    agent_ids = ("weather_agent", "place_agent", "budget_agent")

    for agent_id in agent_ids:
        agent_response = state.get(agent_id, {})
        if agent_response.get("result"):
            results[agent_id] = agent_response["result"]
        if agent_response.get("error"):
            failed_agents.append(agent_id)

    if state.get("error"):
        reason = state["error"]
    elif status == "over_budget":
        reason = "budget_limit_exceeded"
    else:
        reason = None

    return {
        "run_id": new_run_id(),
        "status": status,
        "reason": reason,
        "graph": "weather_place_budget_graph",
        "weather_risk": state.get("weather_risk"),
        "precipitation_probability": state.get("precipitation_probability"),
        "rain_threshold": rain_threshold,
        "weather_source": state.get("weather_source"),
        "error": state.get("error"),
        "selected_place": state.get("selected_place"),
        "budget": budget,
        "completed_agents": list(results),
        "failed_agents": failed_agents,
        "results": results,
        "trace": trace,
    }
