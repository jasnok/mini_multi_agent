"""Python Agent와 YAML Worker를 하나의 Registry로 결합한다."""

from app.agents.loader import load_worker_agents
from app.agents.internal_router_agent import INTERNAL_ROUTER_AGENT
from app.agents.router_agent import ROUTER_AGENT
from app.agents.supervisor_agent import SUPERVISOR_AGENT
from app.agents.incident_supervisor_agent import INCIDENT_SUPERVISOR_AGENT
from app.agents.moving_supervisor_agent import MOVING_SUPERVISOR_AGENT
from app.agents.loader import DEFINITION_FILE

AGENTS = {
    ROUTER_AGENT.agent_id: ROUTER_AGENT,
    INTERNAL_ROUTER_AGENT.agent_id: INTERNAL_ROUTER_AGENT,
    SUPERVISOR_AGENT.agent_id: SUPERVISOR_AGENT,
    INCIDENT_SUPERVISOR_AGENT.agent_id: INCIDENT_SUPERVISOR_AGENT,
    **load_worker_agents(),
    MOVING_SUPERVISOR_AGENT.agent_id: MOVING_SUPERVISOR_AGENT,
    **load_worker_agents(DEFINITION_FILE.with_name("moving_workers.yaml")),
    # **load_team1_agents(),
}


def get_agent(agent_id: str):
    if agent_id not in AGENTS:
        raise ValueError(f"등록되지 않은 Agent입니다: {agent_id}")
    return AGENTS[agent_id]
