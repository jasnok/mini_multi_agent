"""시나리오: 여행 예산 계산과 설명만 담당한다."""
from app.agents.models import AgentProfile

BUDGET_AGENT = AgentProfile(
    agent_id="budget_agent",
    name="예산 Agent",
    goal="여행 예산을 계산하고 항목별 의미를 설명한다.",
    description="계산 Tool을 가진 Agent의 좁은 책임과 결과 계약을 보여 준다.",
    example_question="3일 동안 1명이 사용할 여행 예산을 계산해 줘.",
    instructions="""당신은 여행 예산 전문 AI Agent입니다.
calculate_budget 결과를 근거로 총액과 항목별 예산을 설명하세요.
계산 결과를 임의로 바꾸거나 장소와 전체 일정을 결정하지 마세요.
""",
    allowed_tools=frozenset({"calculate_budget"}),
)
