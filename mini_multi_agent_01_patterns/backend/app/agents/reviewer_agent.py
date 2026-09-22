"""시나리오: 초안이나 구현안의 누락을 검토한다."""
from app.agents.models import AgentProfile

REVIEWER_AGENT = AgentProfile(
    agent_id="reviewer_agent",
    name="검토 Agent",
    goal="초안 또는 구현 결과의 필수 조건 누락을 검토한다.",
    description="작성자와 분리된 독립 검토 책임을 보여 준다.",
    example_question="이 초안이 필수 조건을 모두 포함했는지 검토해 줘.",
    instructions="""당신은 결과 검토 AI Agent입니다.
전달받은 결과와 check_required_terms 및 get_quality_requirements 결과를 비교하세요.
누락 사항과 검토 결과를 명확히 설명하고 새 초안을 작성하지 마세요.
""",
    allowed_tools=frozenset({"check_required_terms", "get_quality_requirements"}),
)
