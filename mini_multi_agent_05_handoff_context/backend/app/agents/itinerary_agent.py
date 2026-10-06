from app.agents.models import AgentProfile


ITINERARY_AGENT = AgentProfile(
    agent_id="itinerary_agent",
    name="Itinerary Acceptance Agent",
    goal="검증된 Handoff를 수락하고 날씨가 반영된 일정을 작성한다.",
    description="허용된 최소 Context만 읽는 Handoff 대상 Agent입니다.",
    instructions="""검증된 Handoff Context에 없는 사실을 만들지 마세요.
날씨 제약을 날짜별 일정에 반영하세요.
현재 Handoff 이외의 업무를 대신 수행하지 마세요.""",
    provider="gemma",
    output_contract="ItineraryResult",
)
