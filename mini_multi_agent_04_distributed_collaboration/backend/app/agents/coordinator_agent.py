from app.agents.models import AgentProfile

COORDINATOR_AGENT = AgentProfile(
    agent_id="coordinator_agent",
    name="Distributed Collaboration Coordinator",
    goal="실행 계획에 따라 병렬 Worker 그룹과 Join 단계를 조정한다.",
    instructions="Worker 결과를 만들지 말고 실행 정책과 상태 전이만 통제하세요.",
    provider="openai",
    output_contract="ExecutionPlan",
)
