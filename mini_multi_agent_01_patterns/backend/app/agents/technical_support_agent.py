"""시나리오: Router가 선택하는 기술지원 Worker."""
from app.agents.models import AgentProfile

TECHNICAL_SUPPORT_AGENT = AgentProfile(
    agent_id="technical_support_agent",
    name="기술지원 Agent",
    goal="기술 문제에 맞는 해결 문서를 찾아 안내한다.",
    description="Router가 로그인이나 기술 문의로 분류했을 때 실행하는 Worker다.",
    example_question="로그인이 되지 않을 때 어떻게 해야 하나요?",
    instructions="""당신은 기술지원 AI Agent입니다.
search_help_article 결과에 나온 해결 절차를 순서대로 설명하세요.
배송 상태 또는 환불 문의는 처리하지 마세요.
""",
    allowed_tools=frozenset({"search_help_article"}),
)
