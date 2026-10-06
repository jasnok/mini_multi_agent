"""반복되는 Worker 선언을 YAML에서 AgentProfile로 변환한다."""

from pathlib import Path

import yaml

from app.agents.models import AgentProfile

DEFINITION_FILE = Path(__file__).resolve().parent / "definitions" / "workers.yaml"
TEAM1_FILE = Path(__file__).resolve().parent / "definitions" / "team1.yaml"


def load_worker_agents(definition_file: Path = DEFINITION_FILE) -> dict[str, AgentProfile]:
    document = yaml.safe_load(definition_file.read_text(encoding="utf-8"))
    agents = {}
    for agent_id, config in document["workers"].items():
        agents[agent_id] = AgentProfile(
            agent_id=agent_id,
            name=config["name"],
            goal=config["goal"],
            description=config["description"],
            example_question=config["example_question"],
            instructions=config["instructions"].strip(),
            provider=config["provider"],
            output_contract=config["output_contract"],
            allowed_tools=frozenset(config.get("allowed_tools", [])),
        )
    return agents

# def load_team1_agents() -> dict[str, AgentProfile]:
#     document = yaml.safe_load(TEAM1_FILE.read_text(encoding="utf-8"))
#     agents = {}
#     for agent_id, config in document["workers"].items():
#         agents[agent_id] = AgentProfile(
#             agent_id=agent_id,
#             name=config["name"],
#             goal=config["goal"],
#             description=config["description"],
#             example_question=config["example_question"],
#             instructions=config["instructions"].strip(),
#             provider=config["provider"],
#             output_contract=config["output_contract"],
#             allowed_tools=frozenset(config.get("allowed_tools", [])),
#         )
#     return agents
