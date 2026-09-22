"""개별 파일에 선언된 Agent를 등록하고 ID로 조회한다."""
from app.agents.models import AgentProfile

from app.agents.analyst_agent import ANALYST_AGENT
from app.agents.budget_agent import BUDGET_AGENT
from app.agents.delivery_agent import DELIVERY_AGENT
from app.agents.developer_agent import DEVELOPER_AGENT
from app.agents.evaluator_agent import EVALUATOR_AGENT
from app.agents.itinerary_agent import ITINERARY_AGENT
from app.agents.place_agent import PLACE_AGENT
from app.agents.refund_policy_agent import REFUND_POLICY_AGENT
from app.agents.research_agent import RESEARCH_AGENT
from app.agents.reviewer_agent import REVIEWER_AGENT
from app.agents.reviser_agent import REVISER_AGENT
from app.agents.safety_agent import SAFETY_AGENT
from app.agents.support_agent import SUPPORT_AGENT
from app.agents.technical_support_agent import TECHNICAL_SUPPORT_AGENT
from app.agents.travel_agent import TRAVEL_AGENT
from app.agents.weather_agent import WEATHER_AGENT
from app.agents.writer_agent import WRITER_AGENT

_PROFILES = (TRAVEL_AGENT, WEATHER_AGENT, PLACE_AGENT, BUDGET_AGENT, SAFETY_AGENT,
             ITINERARY_AGENT, RESEARCH_AGENT, WRITER_AGENT, REVIEWER_AGENT,
             DELIVERY_AGENT, SUPPORT_AGENT, REFUND_POLICY_AGENT,
             TECHNICAL_SUPPORT_AGENT, ANALYST_AGENT, DEVELOPER_AGENT,
             EVALUATOR_AGENT, REVISER_AGENT)
AGENTS = {agent.agent_id: agent for agent in _PROFILES}


def get_agent(agent_id: str) -> AgentProfile:
    if agent_id not in AGENTS:
        raise ValueError(f"등록되지 않은 Agent입니다: {agent_id}")
    return AGENTS[agent_id]
