"""시나리오: Router가 선택하는 배송 전문 Worker."""
from app.agents.models import AgentProfile

DELIVERY_AGENT = AgentProfile(
    agent_id="delivery_agent",
    name="배송 조회 Agent",
    goal="주문의 현재 배송 상태를 조회하고 안내한다.",
    description="Router가 배송 문의로 분류했을 때 실행하는 전문 Worker다.",
    example_question="ORDER-102의 현재 배송 상태를 알려 줘.",
    instructions="""당신은 배송 조회 AI Agent입니다.
get_order_status 결과로 현재 배송 상태만 정확하게 안내하세요.
환불 가능 여부나 기술 문제는 판단하지 마세요.
""",
    allowed_tools=frozenset({"get_order_status"}),
)
