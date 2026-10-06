import asyncio
import re
from typing import Literal
from pydantic import ValidationError, create_model
from app.agents.registry import get_agent, get_team
from app.observability.tracker import DistributedTracker
from app.providers.registry import ProviderExecutionError, generate, model_for
from app.schemas.contracts import AgentResult, CollaborationState, ExecutionPlan, HandoffDecision, PlanStep, TraceEvent
from app.mcp.client import call

RUNS: dict[str, dict[str, object]] = {}
SUPPORTED_CITIES = ("서울", "부산", "제주")


def tool_arguments(tool_name: str, message: str) -> dict[str, object] | None:
    city = next((value for value in SUPPORTED_CITIES if value in message), None)
    if tool_name in {"get_weather", "search_places"}:
        return {"city": city} if city else None
    if tool_name == "calculate_budget":
        stay = re.search(r"(\d+)\s*박\s*(\d+)\s*일", message)
        days_match = re.search(r"(\d+)\s*일", message)
        people_match = re.search(r"(\d+)\s*(?:명|인)(?:\b|\s|,)", message)
        days = int(stay.group(2)) if stay else int(days_match.group(1)) if days_match else None
        if not (city and days and people_match):
            return None
        return {"days": days, "people": int(people_match.group(1)), "city": city}
    if tool_name == "get_order_status":
        order = re.search(r"\bORDER[-_ ]?\d+\b", message, re.IGNORECASE)
        return {"order_id": order.group(0).replace("_", "-").replace(" ", "-").upper()} if order else None
    if tool_name == "get_refund_policy":
        return {}
    return None

def plan() -> ExecutionPlan:
    """세 전문 Agent를 먼저 실행하고 마지막에 일정을 만드는 가장 작은 계획입니다."""
    return ExecutionPlan(goal="부산 여행 일정", steps=[PlanStep(step_id="research", agents=["weather_agent", "place_agent", "budget_agent"]), PlanStep(step_id="compose", agents=["itinerary_agent"], depends_on=["research"], join=True)])

def validate_plan(payload: dict[str, object]) -> dict[str, object]:
    try:
        return {"valid": True, "result": ExecutionPlan.model_validate(payload).model_dump(), "errors": []}
    except ValidationError as error:
        return {"valid": False, "result": None, "errors": [{"location": list(item["loc"]), "message": item["msg"]} for item in error.errors()]}

def error_message(error: Exception) -> str:
    """MCP TaskGroup이 감싼 실제 Tool 오류를 화면에 전달합니다."""
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return str(error)


def agent_result_contract(agent_id: str) -> type[AgentResult]:
    """호출한 Agent만 반환할 수 있도록 agent_id를 출력 계약에 고정합니다."""
    return create_model(
        f"{agent_id}_Result", __base__=AgentResult,
        agent_id=(Literal[agent_id], ...),
    )


def trace(state: CollaborationState, actor: str, action: str, status: str, metadata: dict | None = None, error: str | None = None) -> None:
    metadata = metadata or {}
    state.trace.append(TraceEvent(step=len(state.trace)+1, actor=actor, action=action, status=status, provider=metadata.get("provider"), model=metadata.get("model"), latency_ms=metadata.get("latency_ms"), details={"error": error} if error else {}))

async def agent(agent_id: str, message: str, context: object = None) -> dict[str, object]:
    profile = get_agent(agent_id)
    provider = profile.provider
    try:
        tool_context = {}
        for tool_name in profile.allowed_tools:
            arguments = tool_arguments(tool_name, message)
            if arguments is None:
                raise ValueError(f"{tool_name} 호출에 필요한 도시·기간·인원·주문번호 정보가 없습니다.")
            tool_context[tool_name] = await call(
                tool_name, arguments, profile.allowed_tools
            )
        prompt = f"""당신은 {agent_id}입니다.
이름: {profile.name}
Goal: {profile.goal}
Instructions: {profile.instructions}
요청: {message}
검증된 Context: {context}
MCP Tool Context: {tool_context}
AgentResult 계약으로 반환하고 agent_id는 {agent_id}로 작성하세요."""
        result, metadata = await generate(provider, prompt, agent_result_contract(agent_id))
        if result.agent_id != agent_id:
            raise ValueError(f"Agent 역할 불일치: 기대={agent_id}, 실제={result.agent_id}")
        return {"result": result.model_dump(), "error": None, "tool_context": tool_context, **metadata}
    except Exception as error:
        return {"result": None, "error": error_message(error), "error_code": error.code if isinstance(error, ProviderExecutionError) else "agent_error", "retryable": error.retryable if isinstance(error, ProviderExecutionError) else False, "retry_after_seconds": error.retry_after_seconds if isinstance(error, ProviderExecutionError) else None, "provider": provider, "model": model_for(provider), "latency_ms": None}

async def sequential(message: str) -> dict[str, object]:
    """01의 Sequential Pattern에 Shared State 기록을 추가한 예제입니다."""
    state = CollaborationState(status="running", current_step="sequential")
    context = None
    for agent_id in ("research_agent", "writer_agent", "reviewer_agent"):
        trace(state, agent_id, "agent_started", "started")
        response = await agent(agent_id, message, context)
        if response["error"]:
            state.status = "failed"
            state.errors[agent_id] = response["error"]
            state.failed_agents.append(agent_id)
            trace(state, agent_id, "agent_failed", "failed", response, response["error"])
            break

        state.results[agent_id] = response["result"]
        state.completed_agents.append(agent_id)
        context = response["result"]
        trace(state, agent_id, "agent_completed", "completed", response)
    else:
        state.status = "completed"

    state.current_step = None
    RUNS[state.run_id] = state.model_dump()
    return state.model_dump()

async def parallel(message: str, fail_agent: str | None = None) -> CollaborationState:
    """서로의 결과가 필요 없는 Weather·Place·Budget Agent를 동시에 실행합니다."""
    state = CollaborationState(status="running", current_step="parallel")
    agent_ids = ("weather_agent", "place_agent", "budget_agent")
    for agent_id in agent_ids:
        trace(state, agent_id, "agent_started", "started")

    responses = await asyncio.gather(
        *(agent(agent_id, message) for agent_id in agent_ids)
    )
    for agent_id, response in zip(agent_ids, responses):
        if agent_id == fail_agent:
            response = {**response, "result": None, "error": "교육용 선택 실패"}
        if response["error"]:
            state.errors[agent_id] = response["error"]
            state.failed_agents.append(agent_id)
            trace(state, agent_id, "agent_failed", "failed", response, response["error"])
            continue
        state.results[agent_id] = response["result"]
        state.completed_agents.append(agent_id)
        trace(state, agent_id, "agent_completed", "completed", response)

    state.status = "completed" if not state.errors else "partial_failure"
    return state

def partial_policy(state: CollaborationState, policy: str) -> dict[str, object]:
    """실패가 있어도 계속할지 미리 선택한 정책으로 결정합니다."""
    required_agents = {"weather_agent", "budget_agent"}
    missing_required = sorted(required_agents - set(state.results))

    if policy == "fail_fast":
        can_continue = not state.errors
    elif policy == "best_effort":
        can_continue = bool(state.results)
    else:
        can_continue = not missing_required

    return {
        "policy": policy,
        "can_continue": can_continue,
        "missing_required": missing_required,
        "failed_agents": state.failed_agents,
        "reason": "continue" if can_continue else "policy_blocked",
    }


HANDOFF_CONTEXT_KEYS = {
    "refund_agent": ("order_id", "issue"),
    "delivery_agent": ("order_id", "delivery_issue"),
}


def sanitize_handoff_context(raw_context: dict[str, object], target_agent: str = "refund_agent", *, require: bool = False) -> dict[str, object]:
    forbidden = {"payment_token", "password", "secret", "raw_messages"}
    exposed = sorted(forbidden.intersection(raw_context))
    if exposed:
        raise ValueError(f"금지 Context: {exposed}")
    if target_agent not in HANDOFF_CONTEXT_KEYS:
        raise ValueError("허용되지 않은 Handoff 대상입니다.")
    allowed = HANDOFF_CONTEXT_KEYS[target_agent]
    context = {key: raw_context[key] for key in allowed if raw_context.get(key) not in (None, "")}
    if require:
        missing = [key for key in allowed if key not in context]
        if missing:
            raise ValueError(f"{target_agent}에 필요한 Context 누락: {missing}")
    return context


async def join(message: str, fail_agent: str | None = None, policy: str = "required_optional") -> dict[str, object]:
    """필수 병렬 결과가 준비된 경우에만 Itinerary Agent로 결과를 합칩니다."""
    state = await parallel(message, fail_agent)
    decision = partial_policy(state, policy)
    if not decision["can_continue"]:
        state.status = "failed"
        trace(state, "join_guard_agent", "join_blocked", "blocked", error=decision["reason"])
        state.current_step = None
        RUNS[state.run_id] = state.model_dump()
        return {**state.model_dump(), "policy": decision}

    trace(state, "join_guard_agent", "join_completed", "completed")
    response = await agent("itinerary_agent", message, state.results)
    if response["error"]:
        state.status = "failed"
        state.errors["itinerary_agent"] = response["error"]
        trace(state, "itinerary_agent", "agent_failed", "failed", response, response["error"])
    else:
        state.status = "completed"
        state.results["itinerary_agent"] = response["result"]
        state.completed_agents.append("itinerary_agent")
        trace(state, "itinerary_agent", "agent_completed", "completed", response)

    state.current_step = None
    RUNS[state.run_id] = state.model_dump()
    return {**state.model_dump(), "policy": decision}

async def handoff(message: str, inject_secret: bool = False) -> dict[str, object]:
    """질문에 따라 환불·배송·직접 답변 중 하나를 선택합니다."""
    support_profile = get_agent("support_agent")
    prompt = f"""당신은 support_agent입니다.
고객 문의: {message}
환불·취소 조건을 물으면 refund_agent, 배송 위치·지연을 물으면 delivery_agent로 인계하세요.
그 밖의 일반 질문은 handoff_required=false로 답하고 direct_answer에 답변을 적으세요.
인계할 때는 요청에 있는 주문번호만 order_id에 담고, 환불은 issue, 배송은 delivery_issue에 문의를 담으세요.
다른 경로의 Context 필드는 null로 두고, 넘길 업무는 responsibility에 적으세요.
주문번호나 조회 결과를 만들지 마세요. HandoffDecision 계약으로 반환하세요."""
    try:
        decision, metadata = await generate(support_profile.provider, prompt, HandoffDecision)
    except Exception as error:
        return {"status": "failed", "owner_agent": "support_agent",
                "error": f"{type(error).__name__}: {error}"}
    base = {"decision": decision.model_dump(), "owner_agent": "support_agent",
            "selected_route": "direct_answer", "handoff": None, "safe_context": None,
            "support_provider": metadata}
    if not decision.handoff_required:
        return {**base, "status": "completed", "answer": decision.direct_answer or decision.reason}
    raw_context = decision.handoff_context.model_dump(exclude_none=True)
    if inject_secret:
        raw_context["payment_token"] = "blocked-value"
    try:
        context = sanitize_handoff_context(raw_context, decision.target_agent, require=True)
        order = tool_arguments("get_order_status", message)
        if not order or context["order_id"] != order["order_id"]:
            raise ValueError("고객 문의의 주문번호와 Handoff 주문번호가 일치하지 않습니다.")
    except ValueError as error:
        return {**base, "status": "blocked", "selected_route": decision.target_agent,
                "error": str(error)}
    handoff_data = {
        "from_agent": "support_agent", "to_agent": decision.target_agent,
        "responsibility": decision.responsibility or decision.reason,
        "context": context,
    }
    response = await agent(decision.target_agent, message, context)
    success = response["result"] is not None
    return {**base, "status": "completed" if success else "failed",
            "owner_agent": decision.target_agent if success else "support_agent",
            "selected_route": decision.target_agent, "handoff": handoff_data,
            "safe_context": context, "target_result": response,
            "error": response.get("error") if not success else None}


async def distributed(message: str) -> dict[str, object]:
    return await join(message)


async def distributed_tracked(run_id: str, message: str) -> None:
    """병렬 완료 순서를 Redis Stream에 기록해 SSE에서 즉시 전달합니다."""
    tracker = DistributedTracker(run_id, total_steps=5)
    team = get_team("travel_collaboration_team")
    worker_ids = team["parallel_workers"]
    tracker.emit("coordinator_agent", "workflow_started", "started", "병렬 Worker 실행 시작")

    async def run_named(agent_id: str):
        tracker.emit(agent_id, "agent_started", "started", f"{agent_id} 실행 시작")
        try:
            response = await asyncio.wait_for(
                agent(agent_id, message), timeout=team["timeout_seconds"]
            )
        except Exception as error:
            profile = get_agent(agent_id)
            response = {
                "result": None,
                "error": f"{type(error).__name__}: {error}",
                "provider": profile.provider,
                "model": model_for(profile.provider),
                "latency_ms": None,
            }
        return agent_id, response

    try:
        tasks = [asyncio.create_task(run_named(agent_id)) for agent_id in worker_ids]
        worker_results = {}
        for completed_task in asyncio.as_completed(tasks):
            agent_id, response = await completed_task
            if response["error"]:
                tracker.emit(agent_id, "agent_failed", "failed", response["error"])
            else:
                worker_results[agent_id] = response["result"]
                tracker.emit(agent_id, "agent_completed", "completed", f"{agent_id} 완료", response["result"])

        missing_required = set(team["required_workers"]) - set(worker_results)
        if missing_required:
            tracker.fail(f"필수 Worker 결과 누락: {sorted(missing_required)}")
            return

        aggregator_id = team["aggregator"]
        tracker.emit(aggregator_id, "join_started", "started", "병렬 결과 Join 시작")
        joined = await agent(aggregator_id, message, worker_results)
        if joined["error"]:
            tracker.emit(aggregator_id, "join_failed", "failed", joined["error"])
            tracker.fail(joined["error"])
            return
        tracker.emit(aggregator_id, "join_completed", "completed", "병렬 결과 Join 완료", joined["result"])
        tracker.finish({"workers": worker_results, "aggregated": joined["result"]})
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
