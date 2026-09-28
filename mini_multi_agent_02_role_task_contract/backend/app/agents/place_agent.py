"""시나리오: 여행 장소 카탈로그를 PlaceResult 계약으로 반환한다."""
from app.agents.models import AgentProfile

PLACE_AGENT = AgentProfile(
    agent_id="place_agent",
    name="장소 Agent",
    goal="사용자 조건에 맞는 장소 후보와 선택 근거를 정리한다.",
    description="MCP 장소 조회 결과를 PlaceResult 계약으로 변환한다.",
    example_question="부산에서 대중교통으로 방문할 장소를 추천해 줘.",
    instructions="""당신은 여행 장소 전문 AI Agent입니다.
search_places Tool Result에 있는 장소만 places에 포함하세요.
검증된 이전 Context의 indoor_only가 true이면 Tool Result 중 indoor가 true인 실내 장소만 선택하세요.
선택 근거를 설명하고 날씨, 예산, 전체 일정은 결정하지 마세요.
""",
    provider="ollama",
    output_contract="PlaceResult",
    allowed_tools=frozenset({"search_places"}),
)
