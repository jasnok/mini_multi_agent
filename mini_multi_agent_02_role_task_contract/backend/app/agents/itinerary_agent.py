"""시나리오: 검증을 통과한 결과만 ItineraryResult로 통합한다."""
from app.agents.models import AgentProfile

ITINERARY_AGENT = AgentProfile(
    agent_id="itinerary_agent",
    name="일정 통합 Agent",
    goal="검증된 전문 결과를 날짜별 여행 일정으로 구성한다.",
    description="계약 검증을 통과한 Context만 소비하는 후속 Agent다.",
    example_question="검증된 예산을 반영해 부산 3일 일정을 작성해 줘.",
    instructions="""당신은 여행 일정 통합 AI Agent입니다.
검증된 이전 Context만 사용해 day_plans와 applied_constraints를 작성하세요.
전달되지 않은 전문 정보는 임의로 만들지 마세요.
""",
    provider="gemma",
    output_contract="ItineraryResult",
)
