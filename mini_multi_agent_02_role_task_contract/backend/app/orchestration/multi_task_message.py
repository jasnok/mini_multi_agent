"""Lab 11: 자유 문장을 세 AgentTask의 입력으로 연결한다."""

import re

from pydantic import ValidationError

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.orchestration.task_execution import extract_budget_inputs
from app.schemas.contracts import BudgetResult, BudgetTaskInput, MultiTaskMessageRequest, PlaceResult, WeatherResult
from app.tasks.registry import TASK_BY_ID


TASK_IDS = ("check_weather", "find_places", "allocate_budget")
CONTRACTS = {"check_weather": WeatherResult, "find_places": PlaceResult, "allocate_budget": BudgetResult}
QUESTIONS = {
    "destination": "여행지는 어디인가요? 예: 부산 여행",
    "days": "며칠 여행인가요? 예: 2박 3일",
    "people": "여행 인원은 몇 명인가요? 예: 2명",
    "transport": "이동수단은 무엇인가요? 예: 대중교통 이용",
    "constraints": "알레르기나 이동 제약이 있나요? 없다면 '제약 없음'이라고 적어 주세요.",
    "total_budget": "총예산은 얼마인가요? 예: 예산 60만 원",
}


def extract_task_inputs(message: str) -> dict[str, object]:
    values = extract_budget_inputs(message)
    if "대중교통" in message:
        values["transport"] = "대중교통"
    elif "렌터카" in message or "렌트카" in message:
        values["transport"] = "렌터카"
    elif "자차" in message or "자가용" in message:
        values["transport"] = "자가용"
    elif "도보" in message:
        values["transport"] = "도보"

    if re.search(r"제약\s*없|특별한\s*제약\s*없", message):
        values["constraints"] = []
    else:
        allergies = re.findall(r"([가-힣A-Za-z]+)\s*알레르기", message)
        if allergies:
            values["constraints"] = [f"{item} 알레르기" for item in allergies]
    return values


async def execute_multi_task_from_message(request: MultiTaskMessageRequest) -> dict[str, object]:
    required = list(dict.fromkeys(name for task_id in TASK_IDS for name in TASK_BY_ID[task_id].required_input))
    known = {name: value for name, value in request.known_inputs.items() if name in required}
    collected = {**known, **extract_task_inputs(request.message)}
    missing = [name for name in required if name not in collected or collected[name] is None]
    trace = [{"actor": "task_planner", "action": "message_parsed"}]
    if missing:
        trace.append({"actor": "task_planner", "action": "required_input_missing"})
        return {
            "status": "needs_information", "collected_inputs": collected,
            "missing_information": missing, "questions": [QUESTIONS[name] for name in missing],
            "results": [], "trace": trace,
        }

    try:
        inputs = BudgetTaskInput.model_validate(collected)
        if not isinstance(collected["transport"], str) or not collected["transport"].strip():
            raise ValueError("이동수단은 비어 있지 않은 문자열이어야 합니다.")
        if not isinstance(collected["constraints"], list) or not all(isinstance(item, str) for item in collected["constraints"]):
            raise ValueError("제약 조건은 문자열 목록이어야 합니다.")
    except (ValidationError, ValueError) as error:
        trace.append({"actor": "task_planner", "action": "input_contract_rejected"})
        return {"status": "invalid_input", "collected_inputs": collected, "error": str(error), "results": [], "trace": trace}

    message = (
        f"{inputs.destination} {inputs.days - 1}박 {inputs.days}일 여행, {inputs.people}명, "
        f"{collected['transport']} 이용, 총예산 {inputs.total_budget}원, "
        f"제약: {', '.join(collected['constraints']) if collected['constraints'] else '없음'}"
    )
    results = []
    for task_id in TASK_IDS:
        task = TASK_BY_ID[task_id]
        trace.append({"actor": task.agent_id, "action": "started"})
        agent = await run_agent(get_agent(task.agent_id), message)
        payload = agent.get("result")
        status, error = "completed", None
        if payload is None:
            status, error = "failed", agent.get("error") or "Agent 결과가 없습니다."
        else:
            absent = [name for name in task.expected_output if name not in payload]
            if absent:
                status, error = "failed", f"기대 출력 누락: {absent}"
            else:
                try:
                    verified = CONTRACTS[task_id].model_validate(payload)
                    if task_id == "allocate_budget" and verified.total != inputs.total_budget:
                        status, error = "failed", "예산 합계가 사용자 한도와 다릅니다."
                except ValidationError as exc:
                    status, error = "failed", str(exc)
        trace.append({"actor": task.agent_id, "action": "task_completed" if status == "completed" else "task_failed"})
        results.append({"task": task.model_dump(), "status": status, "agent": agent, "error": error})
    return {
        "status": "completed" if all(item["status"] == "completed" for item in results) else "partial_failure",
        "collected_inputs": collected, "missing_information": [], "questions": [],
        "results": results, "trace": trace,
    }
