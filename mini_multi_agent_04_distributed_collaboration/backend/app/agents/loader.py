from pathlib import Path
import yaml
from app.agents.models import AgentProfile

DEFINITIONS = Path(__file__).resolve().parent / "definitions"

def load_workers() -> dict[str, AgentProfile]:
    document = yaml.safe_load((DEFINITIONS / "workers.yaml").read_text(encoding="utf-8"))
    workers = {}
    for agent_id, config in document["workers"].items():
        workers[agent_id] = AgentProfile(
            agent_id=agent_id, name=config["name"], goal=config["goal"],
            instructions=config["instructions"], provider=config["provider"],
            output_contract=config["output_contract"],
            allowed_tools=frozenset(config.get("allowed_tools", [])),
        )
    return workers

def load_teams() -> dict[str, dict]:
    document = yaml.safe_load((DEFINITIONS / "teams.yaml").read_text(encoding="utf-8"))
    return document["teams"]
