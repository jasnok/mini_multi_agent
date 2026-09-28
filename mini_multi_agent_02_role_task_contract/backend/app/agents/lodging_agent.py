"""교육용 비용 기준으로 잠정 숙소 유형을 정하는 Agent."""

from app.agents.models import AgentProfile


LODGING_AGENT = AgentProfile(
    agent_id="lodging_agent",
    name="숙소 Agent",
    goal="조회된 비용 기준 안에서 숙소 유형 후보를 정리한다.",
    description="MCP의 교육용 숙박 비용 기준으로 잠정 숙소 유형을 선택한다.",
    example_question="부산 2박 여행의 숙소 유형과 비용을 알려 줘.",
    instructions="""당신은 여행 숙소 전문 AI Agent입니다.
get_lodging_reference Tool Result에 있는 잠정 숙소 유형만 사용하세요.
선택 이유를 설명하고 실제 호텔 이름·예약 가능 여부·실시간 요금을 확정하지 마세요.
availability_confirmed는 반드시 false입니다.
""",
    provider="openai",
    output_contract="LodgingResult",
    allowed_tools=frozenset({"get_lodging_reference"}),
)
