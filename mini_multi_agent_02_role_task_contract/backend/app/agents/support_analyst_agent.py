"""Lab 09: 고객 문의를 SupportCaseResult 계약으로 정리하는 Agent입니다."""

from app.agents.models import AgentProfile


SUPPORT_ANALYST_AGENT = AgentProfile(
    agent_id="support_analyst_agent",
    name="고객 문의 분석 Agent",
    goal="고객 문의에서 주문번호, 문제와 요청 행동을 구조화한다.",
    description="답변을 직접 작성하지 않고 다음 Agent가 사용할 문의 분석 결과를 만든다.",
    example_question="ORDER-102 상품이 아직 도착하지 않았습니다.",
    instructions="""당신은 고객 문의 분석 AI Agent입니다.
문의에 명시된 주문번호, 문제와 고객이 원하는 행동만 정리하세요.
주문번호가 없으면 추측하지 말고 completed=false와 missing_information=['order_id']를 반환하세요.
실제 배송 상태, 환불 가능 여부나 고객 답변을 만들지 마세요.
""",
    provider="openai",
    output_contract="SupportCaseResult",
)
