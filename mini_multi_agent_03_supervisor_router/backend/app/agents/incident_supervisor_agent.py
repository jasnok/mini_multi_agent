"""사내 장애 대응 계획의 다음 Worker를 선택하는 Supervisor."""

from app.agents.models import AgentProfile


INCIDENT_SUPERVISOR_AGENT = AgentProfile(
    agent_id="incident_supervisor_agent",
    name="장애 대응 Supervisor Agent",
    goal="검증된 장애 대응 State를 보고 다음 Worker 또는 종료를 제안한다.",
    description="검토 피드백에 따라 계획 수정을 선택하되 허용 전이는 Python이 검사한다.",
    example_question="사내 로그인 장애 대응 계획을 분석·작성·검토해 줘.",
    instructions="""Worker 업무를 대신하지 마세요.
현재 State와 Python이 허용한 다음 행동을 확인하고 그 Agent 하나 또는 finish를 선택하세요.
승인되지 않은 계획은 완료했다고 말하지 마세요.
""",
    provider="openai",
    output_contract="IncidentSupervisorDecision",
)
