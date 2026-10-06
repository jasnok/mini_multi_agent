from app.agents.aggregator_agent import AGGREGATOR_AGENT
from app.agents.coordinator_agent import COORDINATOR_AGENT
from app.agents.loader import load_teams, load_workers
from app.providers.registry import SUPPORTED_PROVIDERS

AGENTS = {COORDINATOR_AGENT.agent_id: COORDINATOR_AGENT, **load_workers()}
AGENTS[AGGREGATOR_AGENT.agent_id] = AGGREGATOR_AGENT
TEAMS = load_teams()


def validate_registry() -> None:
    """시작 시점에 Team이 존재하지 않는 Agent를 참조하는지 확인합니다."""
    for agent_id, profile in AGENTS.items():
        if profile.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"{agent_id}의 Provider가 지원 목록에 없습니다: {profile.provider}")
    for team_id, team in TEAMS.items():
        referenced = {
            *team["parallel_workers"],
            *team["required_workers"],
            *team["optional_workers"],
            team["aggregator"],
        }
        unknown = referenced - set(AGENTS)
        if unknown:
            raise ValueError(f"{team_id}가 등록되지 않은 Agent를 참조합니다: {sorted(unknown)}")
        if not set(team["required_workers"]).issubset(team["parallel_workers"]):
            raise ValueError(f"{team_id}의 필수 Worker가 병렬 실행 목록에 없습니다.")
        if not set(team["optional_workers"]).issubset(team["parallel_workers"]):
            raise ValueError(f"{team_id}의 선택 Worker가 병렬 실행 목록에 없습니다.")
        overlap = set(team["required_workers"]) & set(team["optional_workers"])
        if overlap:
            raise ValueError(f"{team_id}의 필수·선택 Worker가 중복됩니다: {sorted(overlap)}")
        if team["aggregator"] in team["parallel_workers"]:
            raise ValueError(f"{team_id}의 Aggregator는 병렬 Worker와 분리해야 합니다.")


validate_registry()

def get_agent(agent_id: str):
    if agent_id not in AGENTS:
        raise ValueError(f"등록되지 않은 Agent입니다: {agent_id}")
    return AGENTS[agent_id]

def get_team(team_id: str):
    if team_id not in TEAMS:
        raise ValueError(f"등록되지 않은 Team입니다: {team_id}")
    return TEAMS[team_id]
