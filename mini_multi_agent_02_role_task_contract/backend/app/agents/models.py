from dataclasses import dataclass


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    name: str
    goal: str
    description: str
    example_question: str
    instructions: str
    provider: str
    output_contract: str
    allowed_tools: frozenset[str] = frozenset()
