"""Weather → Place → Lodging → Budget 검증 결과 전달 흐름."""

from pydantic import ValidationError

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.orchestration.multi_task_message import extract_task_inputs
from app.schemas.contracts import BudgetResult, BudgetTaskInput, LodgingResult, MultiTaskMessageRequest, PlaceResult, WeatherResult
from app.tasks.registry import TASK_BY_ID


TASK_IDS = ("check_weather", "find_places", "choose_lodging", "allocate_budget")
CONTRACTS = {
    "check_weather": WeatherResult,
    "find_places": PlaceResult,
    "choose_lodging": LodgingResult,
    "allocate_budget": BudgetResult,
}
QUESTIONS = {
    "destination": "여행지는 어디인가요? 예: 부산 여행",
    "days": "며칠 여행인가요? 예: 2박 3일",
    "people": "여행 인원은 몇 명인가요? 예: 1명",
    "transport": "이동수단은 무엇인가요? 예: 대중교통",
    "constraints": "제약이 있나요? 없다면 '제약 없음'이라고 적어 주세요.",
    "total_budget": "총예산은 얼마인가요? 예: 예산 60만 원",
}


def rain_expected(weather_tool: dict) -> bool:
    current = weather_tool.get("current") or {}
    daily = weather_tool.get("daily") or {}
    if (current.get("precipitation") or 0) > 0:
        return True
    return any((chance or 0) >= 40 for chance in daily.get("precipitation_probability_max") or [])


def verify_result(task_id: str, agent: dict, inputs: BudgetTaskInput, indoor_only: bool, lodging: LodgingResult | None):
    payload = agent.get("result")
    if payload is None:
        return None, agent.get("error") or "Agent 결과가 없습니다."
    task = TASK_BY_ID[task_id]
    absent = [name for name in task.expected_output if name not in payload]
    if absent:
        return None, f"기대 출력 누락: {absent}"
    try:
        verified = CONTRACTS[task_id].model_validate(payload)
    except ValidationError as error:
        return None, str(error)

    if task_id == "check_weather":
        source = agent.get("tool_results", {}).get("get_weather", {})
        if not source.get("success") or not verified.source_confirmed:
            return None, "날씨 Tool 근거가 확인되지 않았습니다."
    elif task_id == "find_places":
        items = agent.get("tool_results", {}).get("search_places", {}).get("items") or []
        by_name = {item["name"]: item for item in items}
        if any(name not in by_name for name in verified.places):
            return None, "Place 결과에 DB 후보가 아닌 장소가 있습니다."
        if indoor_only and any(by_name[name].get("indoor") is not True for name in verified.places):
            return None, "비 예보가 있어 indoor=true인 실내 장소만 선택해야 합니다."
    elif task_id == "choose_lodging":
        source = agent.get("tool_results", {}).get("get_lodging_reference", {})
        if not source.get("success") or any((verified.selected_option != source.get("option"), verified.nightly_cost != source.get("nightly_cost"), verified.nights != source.get("nights"), verified.total_cost != source.get("total_cost"))):
            return None, "숙소 비용 기준 또는 총액이 맞지 않습니다."
        if verified.availability_confirmed:
            return None, "실제 예약 가능 여부는 확인하지 않았습니다."
    elif task_id == "allocate_budget":
        if verified.total != inputs.total_budget:
            return None, "예산 합계가 사용자 한도와 다릅니다."
        if lodging is None or verified.breakdown.lodging != lodging.total_cost:
            return None, "예산의 숙박비가 앞서 선택한 숙소 비용과 다릅니다."
    return verified, None


async def execute_weather_place_lodging_budget(request: MultiTaskMessageRequest) -> dict[str, object]:
    required = list(dict.fromkeys(name for task_id in TASK_IDS for name in TASK_BY_ID[task_id].required_input if name != "place_result"))
    known = {name: value for name, value in request.known_inputs.items() if name in required}
    collected = {**known, **extract_task_inputs(request.message)}
    missing = [name for name in required if name not in collected or collected[name] is None]
    trace = [{"actor": "orchestrator", "action": "message_parsed"}]
    if missing:
        trace.append({"actor": "orchestrator", "action": "required_input_missing"})
        return {"status": "needs_information", "collected_inputs": collected,
                "missing_information": missing, "questions": [QUESTIONS[name] for name in missing],
                "results": [], "trace": trace}
    try:
        inputs = BudgetTaskInput.model_validate(collected)
        if inputs.days < 2:
            raise ValueError("숙소 선택을 위해 여행 기간은 2일 이상이어야 합니다.")
        if not isinstance(collected["transport"], str) or not collected["transport"].strip():
            raise ValueError("이동수단은 비어 있지 않은 문자열이어야 합니다.")
        if not isinstance(collected["constraints"], list) or not all(isinstance(item, str) for item in collected["constraints"]):
            raise ValueError("제약은 문자열 목록이어야 합니다.")
    except (ValidationError, ValueError) as error:
        trace.append({"actor": "orchestrator", "action": "input_contract_rejected"})
        return {"status": "invalid_input", "collected_inputs": collected, "error": str(error), "results": [], "trace": trace}

    message = (
        f"{inputs.destination} {inputs.days - 1}박 {inputs.days}일 여행, {inputs.people}명, "
        f"{collected['transport']} 이용, 총예산 {inputs.total_budget}원, "
        f"제약: {', '.join(collected['constraints']) if collected['constraints'] else '없음'}"
    )
    results = []
    context = None
    indoor_only = False
    lodging = None
    for task_id in TASK_IDS:
        task = TASK_BY_ID[task_id]
        trace.append({"actor": task.agent_id, "action": "started"})
        agent = await run_agent(get_agent(task.agent_id), message, context=context)
        verified, error = verify_result(task_id, agent, inputs, indoor_only, lodging)
        status = "completed" if verified is not None else "failed"
        trace.append({"actor": task.agent_id, "action": "task_completed" if verified is not None else "task_failed"})
        results.append({"task": task.model_dump(), "status": status, "agent": agent, "error": error})
        if verified is None:
            for skipped_id in TASK_IDS[TASK_IDS.index(task_id) + 1:]:
                skipped = TASK_BY_ID[skipped_id]
                trace.append({"actor": skipped.agent_id, "action": "skipped"})
                results.append({"task": skipped.model_dump(), "status": "skipped", "agent": None, "error": "선행 Task 검증 실패"})
            return {"status": "failed", "collected_inputs": collected, "results": results, "trace": trace}
        if task_id == "check_weather":
            indoor_only = rain_expected(agent["tool_results"]["get_weather"])
            trace.append({"actor": "orchestrator", "action": "indoor_places_required" if indoor_only else "general_places_allowed"})
            context = {"weather_result": verified.model_dump(), "indoor_only": indoor_only,
                       "place_instruction": "비 예보가 있어 DB의 indoor=true 장소만 선택" if indoor_only else "일반 장소 후보 선택"}
        elif task_id == "find_places":
            context = {"place_result": verified.model_dump(), "weather_indoor_only": indoor_only}
        elif task_id == "choose_lodging":
            lodging = verified
            context = {"lodging_result": verified.model_dump()}
    return {"status": "completed", "collected_inputs": collected, "results": results, "trace": trace}
