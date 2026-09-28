from app.schemas.contracts import AgentTask


CHOOSE_LODGING = AgentTask(
    task_id="choose_lodging",
    agent_id="lodging_agent",
    required_input=["destination", "days", "people", "place_result"],
    expected_output=["selected_option", "nightly_cost", "nights", "total_cost", "availability_confirmed"],
    completion_condition="숙소 비용 기준이 확인되고 숙박 총액이 1박 비용과 숙박일수의 곱과 일치함",
)
