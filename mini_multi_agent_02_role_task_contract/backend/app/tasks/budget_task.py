from app.schemas.contracts import AgentTask


ALLOCATE_BUDGET = AgentTask(
    task_id="allocate_budget",
    agent_id="budget_agent",
    required_input=['destination', 'days', 'people', 'total_budget'],
    expected_output=['breakdown', 'total'],
    completion_condition="항목 합계가 총예산과 일치함",
)
