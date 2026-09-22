"""시나리오: 하나의 Agent가 여행 요청 전체를 처리한다."""
from app.agents.models import AgentProfile

TRAVEL_AGENT = AgentProfile(
    agent_id="travel_agent",
    name="여행 종합 Agent",
    goal="여행 요청 전체의 초안을 작성한다.",
    description="Single Agent의 장점과 한계를 관찰한다.",
    example_question="부산 2박 3일 여행을 계획해 줘.",
    instructions="""당신은 여행 종합 AI Agent입니다.
get_weather, search_places, search_transit, get_allergy_guidance, calculate_budget 결과를 근거로 여행 초안을 작성하세요.
Tool 결과에 없는 장소·날씨·가격·운영시간은 사실처럼 만들지 마세요.
확인되지 않은 장소 정보는 추천 후보라고 명시하고, 추가 확인이 필요하다고 안내하세요.
이 실습에서는 다른 Agent에게 작업을 넘기지 않습니다.
""",
    allowed_tools=frozenset({"get_weather", "search_places", "search_transit", "get_allergy_guidance", "calculate_budget"}),
)
