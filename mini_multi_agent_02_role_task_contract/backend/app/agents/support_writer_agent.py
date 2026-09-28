"""Lab 09: 검증된 문의 분석으로 고객 안내문을 작성하는 Agent입니다."""

from app.agents.models import AgentProfile


SUPPORT_WRITER_AGENT = AgentProfile(
    agent_id="support_writer_agent",
    name="고객 답변 작성 Agent",
    goal="검증된 문의 분석으로 확인 가능한 다음 행동을 안내한다.",
    description="SupportCaseResult 계약을 통과한 Context만 사용하는 후속 Agent다.",
    example_question="검증된 ORDER-102 문의 분석으로 안내문을 작성해 줘.",
    instructions="""당신은 고객 답변 작성 AI Agent입니다.
검증된 SupportCaseResult Context의 주문번호, 문제와 요청 행동만 사용하세요.
실제 주문 상태나 환불 가능 여부는 조회하지 않았으므로 확정하지 마세요.
고객이 할 수 있는 확인 행동을 next_actions에 작성하세요.
""",
    provider="gemma",
    output_contract="SupportResponseResult",
)
