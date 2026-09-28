"""Lab 10: AgentTask 명세를 실제 Budget Agent 실행에 연결한다."""

import re
from decimal import Decimal

from pydantic import ValidationError

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.schemas.contracts import BudgetResult, BudgetTaskInput, TaskExecutionRequest, TaskMessageRequest
from app.tasks.registry import TASK_BY_ID


def extract_budget_inputs(message: str) -> dict[str, object]:
    """자유 문장에서 명시된 값만 추출한다. 없는 값은 추측하지 않는다."""
    values: dict[str, object] = {}
    city = (
        re.search(r"(?:여행지|목적지)(?:는|은|:)?\s*([가-힣A-Za-z]+)", message)
        or re.search(r"([가-힣A-Za-z]+)(?:으로|로)\s*여행", message)
        or re.search(r"([가-힣A-Za-z]+)(?:\s+\d+\s*박\s*\d+\s*일)?\s*여행", message)
    )
    if city:
        values["destination"] = city.group(1)

    days = re.search(r"\d+\s*박\s*(\d+)\s*일", message) or re.search(r"(\d+)\s*일(?:간)?\s*여행", message)
    if days:
        values["days"] = int(days.group(1))

    people = re.search(r"(\d+)\s*(?:명|인)(?![가-힣A-Za-z])", message)
    if people:
        values["people"] = int(people.group(1))

    budget = (
        re.search(r"(?:총\s*)?예산(?:은|이|을|:)?\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(만\s*원|원)", message)
        or re.search(r"((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(만\s*원|원)\s*예산", message)
    )
    if budget:
        amount = Decimal(budget.group(1).replace(",", ""))
        values["total_budget"] = int(amount * (10_000 if "만" in budget.group(2) else 1))
    return values


MISSING_QUESTIONS = {
    "destination": "여행지는 어디인가요? 예: 부산 여행",
    "days": "며칠 여행인가요? 예: 2박 3일",
    "people": "여행 인원은 몇 명인가요? 예: 2명",
    "total_budget": "총예산은 얼마인가요? 예: 예산 60만 원",
}


async def execute_task_from_message(request: TaskMessageRequest) -> dict[str, object]:
    task = TASK_BY_ID[request.task_id]
    known = {name: value for name, value in request.known_inputs.items() if name in task.required_input}
    collected = {**known, **extract_budget_inputs(request.message)}
    result = await execute_task(TaskExecutionRequest(task_id=request.task_id, inputs=collected))
    result["collected_inputs"] = collected
    result["trace"].insert(0, {"task_id": task.task_id, "action": "message_parsed"})
    result["question"] = " ".join(MISSING_QUESTIONS[name] for name in result.get("missing_information", [])) or None
    return result


async def execute_task(request: TaskExecutionRequest) -> dict[str, object]:
    task = TASK_BY_ID[request.task_id]
    trace = [{"task_id": task.task_id, "action": "task_selected"}]

    missing = [name for name in task.required_input if name not in request.inputs or request.inputs[name] is None]
    if missing:
        trace.append({"task_id": task.task_id, "action": "required_input_missing"})
        return {"status": "needs_information", "task": task.model_dump(), "missing_information": missing, "agent": None, "trace": trace}

    try:
        inputs = BudgetTaskInput.model_validate(request.inputs)
    except ValidationError as error:
        trace.append({"task_id": task.task_id, "action": "input_contract_rejected"})
        return {"status": "invalid_input", "task": task.model_dump(), "errors": error.errors(include_context=False), "agent": None, "trace": trace}

    trace.append({"task_id": task.task_id, "action": "input_verified"})
    message = (
        f"{inputs.destination} {max(inputs.days - 1, 0)}박 {inputs.days}일 여행, "
        f"{inputs.people}명, 총예산 {inputs.total_budget}원"
    )
    agent = await run_agent(get_agent(task.agent_id), message)
    if agent["result"] is None:
        trace.append({"task_id": task.task_id, "action": "agent_failed"})
        return {"status": "failed", "task": task.model_dump(), "agent": agent, "trace": trace}

    payload = agent["result"]
    missing_output = [name for name in task.expected_output if name not in payload]
    if missing_output:
        trace.append({"task_id": task.task_id, "action": "expected_output_missing"})
        return {"status": "failed", "task": task.model_dump(), "missing_output": missing_output, "agent": agent, "trace": trace}

    try:
        result = BudgetResult.model_validate(payload)
    except ValidationError as error:
        trace.append({"task_id": task.task_id, "action": "output_contract_rejected"})
        return {"status": "failed", "task": task.model_dump(), "errors": error.errors(include_context=False), "agent": agent, "trace": trace}

    # completion_condition 문자열은 설명이다. 실제 판정은 이 명시적인 규칙으로 한다.
    if result.total != inputs.total_budget:
        trace.append({"task_id": task.task_id, "action": "completion_condition_failed"})
        return {"status": "failed", "task": task.model_dump(), "agent": agent, "trace": trace}

    trace.append({"task_id": task.task_id, "action": "task_completed"})
    return {"status": "completed", "task": task.model_dump(), "agent": agent, "trace": trace}
