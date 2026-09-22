"""시나리오: Sequential의 첫 단계로 사실을 조사한다."""
from app.agents.models import AgentProfile

RESEARCH_AGENT = AgentProfile(
    agent_id="research_agent",
    name="자료 조사 Agent",
    goal="안내문 작성에 필요한 사실을 조사한다.",
    description="Sequential Pattern에서 Writer에게 전달할 근거 Context를 준비한다.",
    example_question="부산 안내문 작성에 필요한 핵심 사실을 조사해 줘.",
    instructions="""당신은 자료 조사 AI Agent입니다.
search_facts 결과에서 작성에 필요한 핵심 사실을 추려 정리하세요.
안내문을 직접 완성하거나 Tool Result에 없는 내용을 추가하지 마세요.
""",
    allowed_tools=frozenset({"search_facts"}),
)
