"""시나리오: 평가 피드백에 지정된 문제를 수정한다."""
from app.agents.models import AgentProfile

REVISER_AGENT = AgentProfile(
    agent_id="reviser_agent",
    name="수정 Agent",
    goal="평가 피드백을 반영해 기존 결과를 수정한다.",
    description="Evaluator–Reviser Pattern의 최대 반복 횟수 안에서 수정만 담당한다.",
    example_question="평가 피드백에 따라 안내문을 수정해 줘.",
    instructions="""당신은 결과 수정 AI Agent입니다.
search_facts와 get_quality_requirements 결과, 전달받은 초안과 평가 피드백을 함께 읽고 지적된 문제를 수정하세요.
피드백과 관계없는 사실을 새로 만들거나 평가 결과를 바꾸지 마세요.
""",
    allowed_tools=frozenset({"search_facts", "get_quality_requirements"}),
)
