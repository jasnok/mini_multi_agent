"""시나리오: 현재 State를 보고 다음 Worker 또는 종료를 선택한다."""
from app.agents.models import AgentProfile

SUPERVISOR_AGENT = AgentProfile(
    agent_id="supervisor_agent",
    name="개발 Supervisor Agent",
    goal="현재 State를 보고 허용된 다음 Worker 또는 finish를 선택한다.",
    description="중간 결과를 직접 만들지 않고 상태 전이를 제안한다.",
    example_question="입력 검증 기능을 분석하고 구현한 뒤 검토해 줘.",
    instructions="""당신은 개발 협업 Supervisor AI Agent입니다.
현재 State와 허용 순서를 읽고 다음 Worker 하나 또는 finish를 선택하세요.
완료한 Worker를 다시 선택하거나 Worker 업무를 직접 수행하지 마세요.
최대 반복과 상태 전이의 최종 통제는 Python Orchestrator가 담당합니다.
""",
    provider="openai",
    output_contract="SupervisorDecision",
)
