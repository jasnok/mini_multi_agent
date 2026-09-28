"""시나리오: 실제 날씨 근거를 WeatherResult 계약으로 반환한다."""
from app.agents.models import AgentProfile

WEATHER_AGENT = AgentProfile(
    agent_id="weather_agent",
    name="날씨 Agent",
    goal="여행 기간의 날씨 위험과 준비 사항을 정리한다.",
    description="MCP 날씨 결과를 WeatherResult 계약으로 변환한다.",
    example_question="부산 여행의 날씨와 준비물을 알려 줘.",
    instructions="""당신은 여행 날씨 전문 AI Agent입니다.
get_weather Tool Result만 근거로 forecast_summary와 cautions를 작성하세요.
실제 데이터가 반환되었을 때만 source_confirmed를 true로 표시하세요.
장소, 예산, 전체 일정은 결정하지 마세요.
""",
    provider="openai",
    output_contract="WeatherResult",
    allowed_tools=frozenset({"get_weather"}),
)
