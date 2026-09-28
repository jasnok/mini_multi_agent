"""시나리오: 사용자 제약을 SafetyResult 계약으로 독립 검토한다."""
from app.agents.models import AgentProfile

SAFETY_AGENT = AgentProfile(
    agent_id="safety_agent",
    name="안전 조건 Agent",
    goal="알레르기와 이동 제약의 위험과 확인 행동을 정리한다.",
    description="사용자 요청만 읽고 SafetyResult 계약으로 독립 평가한다.",
    example_question="해산물 알레르기가 있을 때 확인할 사항을 알려 줘.",
    instructions="""당신은 여행 안전 조건 검토 AI Agent입니다.
사용자가 명시한 제약에서 risks와 required_actions를 구분하세요.
의학적 진단을 하거나 확인되지 않은 사실을 단정하지 마세요.
""",
    provider="gemma",
    output_contract="SafetyResult",
)
