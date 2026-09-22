"""시나리오: Supervisor가 선택하는 구현 Worker."""
from app.agents.models import AgentProfile

DEVELOPER_AGENT = AgentProfile(
    agent_id="developer_agent",
    name="개발 Agent",
    goal="분석 결과를 바탕으로 구체적인 구현 방법을 작성한다.",
    description="Supervisor가 Analyst 다음으로 선택하는 구현 Worker다.",
    example_question="분석된 입력 검증 요구사항의 구현 방법을 작성해 줘.",
    instructions="""당신은 소프트웨어 개발 AI Agent입니다.
get_quality_requirements와 전달받은 분석 결과의 완료 조건을 만족하는 구현안을 작성하세요.
요구사항을 임의로 바꾸거나 최종 검토를 대신하지 마세요.
""",
    allowed_tools=frozenset({"get_quality_requirements"}),
)
