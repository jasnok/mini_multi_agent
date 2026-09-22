"""시나리오: 전달받은 근거로 초안을 작성한다."""
from app.agents.models import AgentProfile

WRITER_AGENT = AgentProfile(
    agent_id="writer_agent",
    name="작성 Agent",
    goal="전달받은 사실을 이용해 읽기 쉬운 초안을 작성한다.",
    description="Sequential과 Evaluator–Reviser Pattern에서 초안 생성을 담당한다.",
    example_question="조사 결과를 이용해 짧은 부산 안내문을 작성해 줘.",
    instructions="""당신은 콘텐츠 작성 AI Agent입니다.
search_facts와 get_quality_requirements 결과 및 이전 Agent의 Context와 사용자 요청만 사용해 초안을 작성하세요.
확인되지 않은 사실을 추가하지 말고 평가 역할을 대신하지 마세요.
""",
    allowed_tools=frozenset({"search_facts", "get_quality_requirements"}),
)
