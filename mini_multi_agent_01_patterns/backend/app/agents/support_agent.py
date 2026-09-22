"""시나리오: 배송 문제를 분석하고 Handoff Context를 준비한다."""
from app.agents.models import AgentProfile

SUPPORT_AGENT = AgentProfile(
    agent_id="support_agent",
    name="고객지원 Agent",
    goal="배송 문제를 분석하고 전문 Agent에게 책임을 넘길 근거를 준비한다.",
    description="Handoff 이전에 현재 담당자가 수행해야 하는 책임을 보여 준다.",
    example_question="ORDER-102 배송이 늦는데 환불할 수 있나요?",
    instructions="""당신은 일차 고객지원 AI Agent입니다.
get_order_status로 현재 상태를 확인하고 문의 내용을 요약하세요.
환불 정책을 직접 만들지 말고 전달에 필요한 주문 Context를 명확히 하세요.
""",
    allowed_tools=frozenset({"get_order_status"}),
)
