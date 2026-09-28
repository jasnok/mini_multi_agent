from app.schemas.contracts import AgentTask


CHECK_WEATHER = AgentTask(
    task_id="check_weather",
    agent_id="weather_agent",
    required_input=['destination', 'days'],
    expected_output=['forecast_summary', 'cautions'],
    completion_condition="날씨와 주의사항이 정리됨",
)
