from __future__ import annotations

import json
import re

from app.agents.models import AgentProfile
from app.mcp.client import call_tool
from app.providers.registry import generate_structured
from app.schemas.runs import AgentOutput


def _travel_arguments(message: str) -> dict[str, dict[str, object] | None]:
    """Lab 01 입력에서 실제 Tool 호출에 필요한 최소 인수를 추출한다."""
    city_match = re.search(
        r"([가-힣A-Za-z]+)(?:\s+\d+\s*박\s*\d+\s*일)?\s*여행|([가-힣A-Za-z]+)\s*(?:으로|에서)",
        message,
    )
    city = next((group for group in city_match.groups() if group), None) if city_match else None

    stay_match = re.search(r"(\d+)\s*박\s*(\d+)\s*일", message)
    days = int(stay_match.group(2)) if stay_match else None

    people_match = re.search(
        r"(\d+)\s*(?:명|인)(?=$|[\s,.;!?]|(?:이|가|은|는|을|를|과|와)(?:\b|\s))",
        message,
    )
    people = int(people_match.group(1)) if people_match else None

    budget_match = re.search(r"([\d,.]+)\s*(만원|원)", message)
    total_budget = None
    if budget_match:
        amount = int(float(budget_match.group(1).replace(",", "")))
        total_budget = amount * 10_000 if budget_match.group(2) == "만원" else amount

    return {
        "get_weather": {"city": city} if city else None,
        "search_places": {"city": city} if city else None,
        "search_transit": {"city": city} if city else None,
        "get_allergy_guidance": {"city": city} if city else None,
        "calculate_budget": {"days": days, "total_budget": total_budget, "people": people}
        if days and total_budget else None,
    }


def tool_arguments(profile: AgentProfile, tool_name: str, message: str, context: object | None) -> dict[str, object] | None:
    if tool_name in {"get_weather", "search_places", "search_transit", "get_allergy_guidance", "calculate_budget"}:
        return _travel_arguments(message).get(tool_name, {})
    if tool_name == "get_order_status":
        order_match = re.search(r"ORDER-\d+", message.upper())
        return {"order_id": order_match.group(0)} if order_match else None
    if tool_name == "search_help_article":
        if "결제" in message:
            return {"topic": "결제"}
        if "로그인" in message:
            return {"topic": "로그인"}
        return None
    if tool_name == "search_facts":
        return {"topic": "부산"} if "부산" in message or context else None
    if tool_name == "get_quality_requirements":
        scenario = "code" if profile.agent_id in {"analyst_agent", "developer_agent"} or any(word in message for word in ("코드", "구현", "검증 기능")) else "content"
        return {"scenario": scenario}
    if tool_name == "check_required_terms":
        scenario = "code" if any(word in message for word in ("코드", "구현", "검증 기능")) else "content"
        return {"text": json.dumps(context, ensure_ascii=False, default=str), "scenario": scenario}
    if tool_name == "get_refund_policy":
        return {}
    return None


async def run_agent(profile: AgentProfile, message: str, provider: str, context: object | None = None) -> tuple[AgentOutput, dict[str, object]]:
    tool_results = {}
    invoked_tools = []
    skipped_tools = []
    for tool_name in profile.allowed_tools:
        arguments = tool_arguments(profile, tool_name, message, context)
        if arguments is None:
            tool_results[tool_name] = {
                "success": False,
                "reason": "사용자 요청에 Tool 필수 입력이 없습니다.",
                "source": "user-input-validation",
            }
            skipped_tools.append(tool_name)
            continue
        tool_results[tool_name] = await call_tool(tool_name, arguments, profile.allowed_tools)
        invoked_tools.append(tool_name)

    prompt = f"""당신은 {profile.agent_id}입니다.
Goal: {profile.goal}
Instructions: {profile.instructions}
사용자 요청: {message}
이전 Agent의 검증된 Context: {json.dumps(context, ensure_ascii=False, default=str)}
MCP Tool Result: {json.dumps(tool_results, ensure_ascii=False, default=str)}
MCP Tool Result만 사실 근거로 사용하세요. 결과에 없는 구체적 사실은 생성하지 말고 확인 필요로 표시하세요.
AgentOutput 계약으로 자신의 결과만 반환하세요. agent_id는 반드시 {profile.agent_id}입니다."""
    output, metadata = await generate_structured(provider, prompt, AgentOutput)
    if output.agent_id != profile.agent_id:
        raise ValueError(f"Agent 역할 불일치: expected={profile.agent_id}, actual={output.agent_id}")
    return output, {
        **metadata,
        "tools": sorted(invoked_tools),
        "skipped_tools": sorted(skipped_tools),
        "tool_results": tool_results,
    }
