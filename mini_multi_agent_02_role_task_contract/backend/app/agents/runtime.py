"""Agent 한 명의 Tool 조회, Prompt 생성, 계약 검증만 담당한다."""
import json
import re
from time import perf_counter
from app.agents.models import AgentProfile
from app.mcp.client import call_tool
from app.providers.registry import ProviderExecutionError, generate_structured, model_for
from app.schemas.contracts import CONTRACTS, LLM_RESPONSE_CONTRACTS

def tool_arguments(tool_name: str, message: str) -> dict[str, object] | None:
    city_match = re.search(r"([가-힣A-Za-z]+)(?:\s+\d+\s*박\s*\d+\s*일)?\s*여행|([가-힣A-Za-z]+)\s*(?:으로|에서)", message)
    city = next((group for group in city_match.groups() if group), None) if city_match else None
    if tool_name in {"get_weather", "search_places"}:
        return {"city": city} if city else None
    if tool_name == "get_lodging_reference":
        stay = re.search(r"(\d+)\s*박\s*(\d+)\s*일", message)
        return {"city": city, "days": int(stay.group(2))} if city and stay else None
    if tool_name == "get_budget_reference":
        stay = re.search(r"(\d+)\s*박\s*(\d+)\s*일", message)
        people_match = re.search(r"(\d+)\s*(?:명|인)(?:\b|\s|,)", message)
        budget_match = re.search(r"([\d,.]+)\s*(만\s*원|원)", message)
        if not (city and stay and people_match and budget_match):
            return None
        amount = int(float(budget_match.group(1).replace(",", "")))
        total_budget = amount * 10_000 if "만" in budget_match.group(2) else amount
        return {"city": city, "days": int(stay.group(2)), "people": int(people_match.group(1)), "total_budget": total_budget}
    return None

async def run_agent(profile: AgentProfile, message: str, context: object | None = None, tracker=None) -> dict[str, object]:
    started = perf_counter()
    tool_results = {}
    try:
        if tracker:
            tracker.waiting(profile.agent_id, "agent_started", f"{profile.name}가 작업을 시작했습니다.", provider=profile.provider)
        for tool_name in profile.allowed_tools:
            arguments = tool_arguments(tool_name, message)
            if arguments is None:
                raise ValueError(f"{tool_name} 호출에 필요한 도시·기간·인원·예산 정보가 사용자 요청에 없습니다.")
            if tracker:
                tracker.waiting(profile.agent_id, "tool_call", f"{tool_name} Tool을 호출하고 있습니다.", tool=tool_name)
            tool_results[tool_name] = await call_tool(tool_name, arguments, profile.allowed_tools)
            if tracker:
                tracker.advance(profile.agent_id, "tool_completed", f"{tool_name} Tool 호출이 완료되었습니다.", tool=tool_name, source=tool_results[tool_name].get("source"))
        response_schema = LLM_RESPONSE_CONTRACTS[profile.output_contract]
        prompt = f"""당신은 {profile.agent_id}입니다.
Goal: {profile.goal}
Instructions: {profile.instructions}
사용자 요청: {message}
검증된 이전 Context: {json.dumps(context, ensure_ascii=False, default=str)}
MCP Tool Result: {json.dumps(tool_results, ensure_ascii=False, default=str)}
{profile.output_contract} JSON 계약으로 반환하세요."""
        if tracker:
            tracker.waiting(profile.agent_id, "llm_call", f"{profile.provider} LLM 응답을 기다리고 있습니다.", provider=profile.provider)
        draft, metadata = await generate_structured(profile.provider, prompt, response_schema)

        # Budget Agent의 산술은 LLM 초안을 신뢰하지 않고 MCP Tool 계산값으로 고정합니다.
        # 그 다음 최종 BudgetResult 계약이 네 항목 합계와 total의 일치를 검증합니다.
        result_payload = draft.model_dump()
        if profile.output_contract == "LodgingResult":
            lodging_tool = tool_results["get_lodging_reference"]
            if not lodging_tool.get("success"):
                raise ValueError("숙소 비용 기준을 찾지 못했습니다.")
            result_payload.update({
                "selected_option": lodging_tool["option"],
                "nightly_cost": lodging_tool["nightly_cost"],
                "nights": lodging_tool["nights"],
                "total_cost": lodging_tool["total_cost"],
                "availability_confirmed": False,
            })
        if profile.output_contract == "BudgetResult":
            budget_tool = tool_results["get_budget_reference"]
            if not budget_tool.get("budget_feasible"):
                raise ValueError(
                    "총예산이 교통·숙박·식비 기준 금액보다 부족합니다. "
                    f"필요 금액: {budget_tool.get('required_budget')}원"
                )
            result_payload["breakdown"] = budget_tool["recommended_breakdown"]
            result_payload["total"] = budget_tool["total_budget"]

        result = CONTRACTS[profile.output_contract].model_validate(result_payload)
        if tracker:
            tracker.advance(profile.agent_id, "llm_completed", f"{profile.name}의 LLM 응답이 완료되었습니다.", provider=profile.provider, model=metadata["model"])
            tracker.advance(profile.agent_id, "contract_verified", f"{profile.output_contract} 계약 검증을 통과했습니다.", contract=profile.output_contract)
        return {"status": "completed", "agent_id": profile.agent_id, **metadata, "tools": sorted(profile.allowed_tools), "tool_results": tool_results, "result": result.model_dump(), "error": None}
    except Exception as error:
        error_code = error.code if isinstance(error, ProviderExecutionError) else "agent_error"
        retryable = error.retryable if isinstance(error, ProviderExecutionError) else False
        retry_after_seconds = error.retry_after_seconds if isinstance(error, ProviderExecutionError) else None
        if tracker:
            tracker.event(profile.agent_id, "agent_failed", "failed", str(error), provider=profile.provider, error_code=error_code, retryable=retryable, retry_after_seconds=retry_after_seconds)
        return {"status": "failed", "agent_id": profile.agent_id, "provider_requested": profile.provider, "provider_used": None, "model": model_for(profile.provider), "latency_ms": round((perf_counter() - started) * 1000, 2), "fallback_used": False, "tools": sorted(profile.allowed_tools), "tool_results": tool_results, "result": None, "error": str(error), "error_code": error_code, "retryable": retryable, "retry_after_seconds": retry_after_seconds}
