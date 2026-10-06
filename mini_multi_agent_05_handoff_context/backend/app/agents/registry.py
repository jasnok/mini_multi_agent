from pathlib import Path
import yaml
from app.agents.itinerary_agent import ITINERARY_AGENT
from app.agents.support_router import SUPPORT_ROUTER
from app.agents.device_support_agent import DEVICE_SUPPORT_AGENT
from app.agents.access_support_agent import ACCESS_SUPPORT_AGENT
from app.agents.it_triage_agent import IT_TRIAGE_AGENT
from app.agents.account_support_agent import ACCOUNT_SUPPORT_AGENT
from app.agents.weather_agent import WEATHER_AGENT
from app.agents.customer_support_agent import CUSTOMER_SUPPORT_AGENT
from app.agents.refund_agent import REFUND_AGENT
from app.providers.registry import SUPPORTED_PROVIDERS

AGENTS = {
    WEATHER_AGENT.agent_id: WEATHER_AGENT,
    CUSTOMER_SUPPORT_AGENT.agent_id: CUSTOMER_SUPPORT_AGENT,
    REFUND_AGENT.agent_id: REFUND_AGENT,
    SUPPORT_ROUTER.agent_id: SUPPORT_ROUTER,
    DEVICE_SUPPORT_AGENT.agent_id: DEVICE_SUPPORT_AGENT,
    ACCESS_SUPPORT_AGENT.agent_id: ACCESS_SUPPORT_AGENT,
    ITINERARY_AGENT.agent_id: ITINERARY_AGENT,
    IT_TRIAGE_AGENT.agent_id: IT_TRIAGE_AGENT,
    ACCOUNT_SUPPORT_AGENT.agent_id: ACCOUNT_SUPPORT_AGENT,
}
POLICY_FILE = Path(__file__).resolve().parent / "definitions" / "handoff_policies.yaml"
HANDOFF_ROUTES = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))["handoff_routes"]


def validate_registry() -> None:
    for agent_id, profile in AGENTS.items():
        if profile.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"{agent_id}의 Provider가 지원 목록에 없습니다: {profile.provider}")
    for route_id, route in HANDOFF_ROUTES.items():
        for key in ("from_agent", "to_agent", "required_context", "optional_context", "max_hops"):
            if key not in route:
                raise ValueError(f"{route_id}에 필수 설정이 없습니다: {key}")
        if route["from_agent"] not in AGENTS or route["to_agent"] not in AGENTS:
            raise ValueError(f"{route_id}가 등록되지 않은 Agent를 참조합니다.")
        overlap = set(route["required_context"]) & set(route["optional_context"])
        if overlap:
            raise ValueError(f"{route_id}의 필수·선택 Context가 중복됩니다: {sorted(overlap)}")
        if not isinstance(route["max_hops"], int) or route["max_hops"] < 1:
            raise ValueError(f"{route_id}의 max_hops는 1 이상의 정수여야 합니다.")


validate_registry()

def get_agent(agent_id: str):
    if agent_id not in AGENTS:
        raise ValueError(f"등록되지 않은 Agent입니다: {agent_id}")
    return AGENTS[agent_id]

def get_route(from_agent: str, to_agent: str):
    for route in HANDOFF_ROUTES.values():
        if route["from_agent"] == from_agent and route["to_agent"] == to_agent:
            return route
    raise PermissionError("허용되지 않은 Handoff 경로입니다.")
