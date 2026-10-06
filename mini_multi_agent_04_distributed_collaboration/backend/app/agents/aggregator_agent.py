from app.agents.models import AgentProfile

AGGREGATOR_AGENT = AgentProfile(
    agent_id="itinerary_agent",
    name="여행 가이드 Agent",
    goal="검증된 날씨·장소·숙소·예산 결과를 하나의 여행 가이드로 통합한다.",
    instructions="전달받은 Worker 결과만 사용하고 누락된 사실을 만들지 마세요.",
    provider="gemma",
    output_contract="AgentResult",
)
