from app.agents.models import AgentProfile

CUSTOMER_SUPPORT_AGENT = AgentProfile(
    agent_id="customer_support_agent",
    name="고객 상담 Agent",
    goal="고객의 환불 문의에서 넘길 책임과 최소 Context를 정리한다.",
    description="환불 문의를 처음 받은 책임자입니다.",
    instructions=(
        "환불 문의를 refund_agent에게 넘길 이유와 책임을 정리하세요. "
        "요청에 실제로 있는 주문번호는 정확히 복사하고, 문의 내용을 handoff_context에 담으세요. "
        "주문번호가 없으면 만들지 마세요. 환불이 처리되었다고 말하지 마세요."
    ),
    provider="openai",
    output_contract="SupportRefundDecision",
)
