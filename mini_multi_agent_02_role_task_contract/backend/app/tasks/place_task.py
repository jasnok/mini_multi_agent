from app.schemas.contracts import AgentTask


FIND_PLACES = AgentTask(
    task_id="find_places",
    agent_id="place_agent",
    required_input=['destination', 'people', 'transport', 'constraints'],
    expected_output=['places', 'selection_reason'],
    completion_condition="사용자 조건에 맞는 장소 후보와 선택 근거가 준비됨",
)
