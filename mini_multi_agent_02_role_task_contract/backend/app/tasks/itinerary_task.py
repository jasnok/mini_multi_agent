from app.schemas.contracts import AgentTask


BUILD_ITINERARY = AgentTask(
    task_id="build_itinerary",
    agent_id="itinerary_agent",
    required_input=['weather_result', 'place_result', 'budget_result', 'safety_result'],
    expected_output=['day_plans', 'applied_constraints'],
    completion_condition="네 전문 결과의 계약이 검증되고 일정에 제약이 반영됨",
)
