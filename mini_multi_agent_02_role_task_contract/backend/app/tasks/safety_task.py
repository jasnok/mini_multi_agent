from app.schemas.contracts import AgentTask


CHECK_SAFETY = AgentTask(
    task_id="check_safety",
    agent_id="safety_agent",
    required_input=['constraints'],
    expected_output=['risks', 'required_actions'],
    completion_condition="명시된 제약의 위험과 확인 행동이 정리됨",
)
