from app.agents.models import AgentProfile

REFUND_AGENT = AgentProfile(
    agent_id="refund_agent",
    name="환불 담당 Agent",
    goal="전달받은 환불 문의의 다음 확인 절차를 안내한다.",
    description="검증된 Handoff Context로 환불 문의를 이어서 처리합니다.",
    instructions="주문번호와 문의 내용을 바탕으로 다음 확인 절차를 간단히 안내하세요. 실제 환불을 실행하거나 완료했다고 말하지 마세요.",
    provider="gemma",
    output_contract="RefundHandoffResult",
)
