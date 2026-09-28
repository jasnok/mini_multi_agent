"""02 Role, Task and Contract 강의를 왼쪽 메뉴로 진행하는 Streamlit 화면입니다."""

import json
import os
import time
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LAB_REQUEST_EXAMPLES = {
    "01": ["부산 여행을 계획할 Agent들의 역할과 하지 말아야 할 일을 정의해 줘."],
    "02": ["부산 여행 요청을 날씨·장소·예산·안전·일정 Task로 나눠 줘."],
    "03": ["부산 3일 여행, 총예산 60만원 입력 계약을 확인해 줘."],
    "04": ["WeatherResult와 BudgetResult의 역할별 출력 계약을 비교해 줘."],
    "06": ["완료·정보 부족·실행 실패 상태의 차이를 보여 줘."],
    "07": ["부산 2박 3일 여행, 1명, 대중교통, 예산 60만원을 역할별로 처리해 줘.", "부산 2박 3일 여행, 1명, 예산 60만원, 해산물 알레르기를 역할별로 처리해 줘.", "부산 2박 3일 여행, 3명, 예산 80만원 요청에서 예산 부족을 확인해 줘."],
    "08": ["부산 2박 3일 여행, 1명, 예산 60만원의 검증된 예산만 일정 Agent에게 전달해 줘.", "부산 1박 2일 여행, 2명, 예산 80만원을 계약 검증 후 일정으로 만들어 줘.", "부산 2박 3일 여행, 3명, 예산 80만원에서 예산 검증 실패 시 다음 Agent를 중단해 줘."],
    "09": ["ORDER-102 상품이 아직 도착하지 않았습니다. 현재 상태와 제가 해야 할 일을 알려 주세요.", "ORDER-205 배송이 지연되고 있습니다. 확인 방법을 안내해 주세요.", "상품이 아직 도착하지 않았습니다. 제가 무엇을 확인해야 하나요?"],
}

LAB_BACKEND_ENDPOINTS = {
    "01": [("GET", "/api/role-cards")],
    "02": [("GET", "/api/tasks")],
    "03": [("POST", "/api/contracts/validate")],
    "04": [("GET", "/api/contracts")],
    "05": [("GET", "/api/validation-cases"), ("POST", "/api/contracts/validate")],
    "06": [("GET", "/api/incomplete-states")],
    "07": [("POST", "/api/async-runs/multi-llm"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "08": [("POST", "/api/async-runs/verified-flow"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "09": [("POST", "/api/async-runs/support-flow"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "10": [("GET", "/api/tasks"), ("POST", "/api/tasks/execute")],
    "11": [("POST", "/api/tasks/execute-multi-from-message")],
}

LAB_SCREEN_DESCRIPTIONS = {
    "01": "Agent 이름이 아니라 Goal·Responsibilities·Non-goals로 역할 경계를 정의합니다. Backend Role Card를 수정해 보면서 Agent가 해야 할 일과 하지 말아야 할 일을 동시에 명시해야 책임 충돌을 줄일 수 있음을 확인합니다.",
    "02": "하나의 여행 요청을 Agent가 실행 가능한 작은 Task로 나눕니다. 각 Task의 담당 Agent, 필수 입력, 기대 출력, 완료 조건을 확인하여 단순한 역할 이름이 실제 실행 단위가 되기 위해 필요한 정보를 학습합니다.",
    "03": "Budget Agent에 전달될 destination·days·total_budget의 입력 경계를 확인합니다. 필수값 누락, 허용 범위를 벗어난 일수, 음수 예산을 다음 Agent나 LLM 호출 전에 차단하는 이유를 보여 줍니다.",
    "04": "WeatherResult와 BudgetResult처럼 역할에 따라 서로 다른 출력 계약을 사용합니다. 모든 Agent가 공통 summary만 반환할 때 잃게 되는 전문 필드와, 후속 단계가 안정적으로 소비할 수 있는 구조화 계약을 비교합니다.",
    "05": "Pydantic 계약이 필수 필드·역할 ID·음수 금액·예산 합계 불변식을 실제로 차단하는지 검증합니다. 타입만 맞는 JSON이 아니라 업무 의미까지 유효해야 다음 Agent에게 전달할 수 있음을 확인합니다.",
    "06": "정상 완료, 사용자 정보 부족, Provider 실행 오류를 서로 다른 상태로 표현합니다. completed=false 하나로 모든 문제를 뭉치지 않고 추가 질문·Retry·종료 중 올바른 다음 행동을 선택하는 방법을 학습합니다.",
    "07": "Gemini Weather, Llama Place, GPT Budget, Gemma Safety Agent가 실제 MCP 데이터와 서로 다른 출력 계약으로 실행됩니다. Redis Snapshot을 1초마다 조회하여 현재 Agent, 진행률, Tool 출처, 계약 검증 Trace를 실시간으로 확인합니다.",
    "08": "GPT Budget Agent의 PostgreSQL 비용 기준 결과가 BudgetResult 계약을 통과한 경우에만 Gemma Itinerary Agent가 실행됩니다. 검증되지 않은 출력의 전달을 차단하고 Redis Trace에서 Context 검증과 후속 실행 여부를 확인합니다.",
    "09": "여행이 아닌 고객지원 업무에 같은 구조를 적용합니다. OpenAI가 문의를 SupportCaseResult로 정리하고, 계약을 통과한 경우에만 Gemma가 고객 안내문을 작성합니다.",
    "10": "AgentTask 명세의 필수 입력·담당 Agent·기대 출력·완료 조건을 실제 예산 Task 실행에 연결합니다.",
    "11": "날씨를 검증해 비 예보면 실내 장소를 고르고, 숙소 유형과 전체 비용까지 차례로 검증합니다.",
}

LAB_CODE_PATHS = {
    "01": ["backend/app/services/catalog.py"],
    "02": ["backend/app/tasks/registry.py"],
    "03": ["backend/app/schemas/contracts.py"],
    "04": ["backend/app/schemas/contracts.py"],
    "05": ["backend/app/services/contract_service.py"],
    "06": ["backend/app/services/catalog.py"],
    "07": ["backend/app/agents/runtime.py"],
    "08": ["backend/app/orchestration/verified_flow.py"],
    "09": ["backend/app/orchestration/support_flow.py"],
    "10": ["backend/app/tasks/budget_task.py", "backend/app/orchestration/task_execution.py"],
    "11": ["backend/app/tasks/registry.py", "backend/app/orchestration/weather_place_lodging_budget.py"],
}


def api_get(path: str):
    response = requests.get(f"{API}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict, timeout: int = 10):
    response = requests.post(f"{API}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def run_with_polling(flow_name: str, payload: dict, max_wait_seconds: int = 900) -> dict | None:
    """Run ID를 받은 뒤 Redis Snapshot을 1초 간격으로 조회합니다."""
    created = api_post(f"/api/async-runs/{flow_name}", payload)
    run_id = created["run_id"]
    st.code(f"run_id: {run_id}")
    progress = st.progress(0, text="실행 요청을 등록했습니다.")
    state_area = st.empty()
    trace_area = st.empty()
    started = time.monotonic()

    while time.monotonic() - started < max_wait_seconds:
        snapshot = api_get(f"/api/async-runs/{run_id}/snapshot")
        state = snapshot["state"]
        progress.progress(state["progress_percent"], text=state["message"])
        state_area.info(f"상태: {state['status']} · Agent: {state.get('current_agent') or '-'} · 단계: {state['current_stage']}")
        trace_area.dataframe(snapshot["events"], use_container_width=True)
        if state["status"] in {"completed", "failed"}:
            return state
        time.sleep(1)

    st.error("화면의 최대 대기 시간을 초과했습니다. Run ID로 상태를 다시 조회할 수 있습니다.")
    return None


def show_header(lab_id: str, labs: dict) -> str:
    lab = labs[lab_id]
    st.title(f"Lab {lab_id} · {lab['title']}")
    endpoints = LAB_BACKEND_ENDPOINTS[lab_id]
    if endpoints:
        st.code("\n".join(f"{method} {API}{path}" for method, path in endpoints), language="http")
        st.caption("Backend 호출: 이 Lab에서 조회하거나 실행하는 실제 API입니다.")
    else:
        st.code("Backend 실행 API 호출 없음", language="text")
        st.caption("Frontend에서 입력 계약을 즉시 확인하는 개념 실습입니다.")
    st.markdown("**이 화면에서 확인할 내용**")
    st.write(LAB_SCREEN_DESCRIPTIONS[lab_id])
    with st.expander("실행 후 함께 읽을 코드"):
        for path in LAB_CODE_PATHS[lab_id]:
            st.code(path, language="text")
    st.info(f"생각할 질문 · {lab['question']}")
    st.success(f"핵심 답변 · {lab['answer_summary']}")
    with st.expander("상세 답변 보기"):
        for detail in lab["answer_details"]:
            st.write(f"- {detail}")
    left, right = st.columns(2)
    left.metric("실제 LLM", "사용" if lab["real_llm"] else "미사용")
    right.metric("예상 호출", lab["expected_calls"])
    if lab_id in {"05", "10", "11"}:
        return ""
    if lab_id in {"01", "02", "03", "04", "06"}:
        example = LAB_REQUEST_EXAMPLES[lab_id][0]
        st.info(f"사용자 요청 예시 · {example}")
        return example
    return st.selectbox("사용자 요청 예시", LAB_REQUEST_EXAMPLES[lab_id], key=f"request-example-{lab_id}")


def show_role_lab(role_cards: list[dict]) -> None:
    options = {card["agent_id"]: card for card in role_cards}
    selected = st.selectbox("기본 Role Card", list(options))
    sample = options[selected]
    goal = st.text_input("Goal", sample["goal"])
    responsibilities = st.text_area("Responsibilities · 한 줄에 하나", "\n".join(sample["responsibilities"]))
    non_goals = st.text_area("Non-goals · 한 줄에 하나", "\n".join(sample["non_goals"]))
    preview = {
        "agent_id": selected,
        "goal": goal,
        "responsibilities": [item for item in responsibilities.splitlines() if item.strip()],
        "non_goals": [item for item in non_goals.splitlines() if item.strip()],
    }
    st.subheader("Role Card Preview")
    st.json(preview)
    st.caption("해야 할 일뿐 아니라 하지 말아야 할 일도 역할 경계입니다.")


def show_task_lab(tasks: list[dict]) -> None:
    st.write("하나의 여행 요청을 책임과 완료 조건이 분명한 Task로 나눕니다.")
    for index, task in enumerate(tasks, start=1):
        with st.expander(f"{index}. {task['task_id']} → {task['agent_id']}", expanded=True):
            st.write("필요 입력:", task["required_input"])
            st.write("기대 출력:", task["expected_output"])
            st.success(f"완료 조건: {task['completion_condition']}")


def show_io_contract_lab() -> None:
    destination = st.text_input("destination", "부산")
    days = st.number_input("days", min_value=0, max_value=40, value=3)
    budget = st.number_input("total_budget", min_value=-100000, value=600000, step=10000)
    payload = {"destination": destination, "days": days, "total_budget": budget}
    st.subheader("BudgetAgentInput")
    st.json(payload)
    if st.button("Backend 입력 계약 검증", type="primary", use_container_width=True):
        result = api_post("/api/contracts/validate", {"contract_name": "BudgetAgentInput", "payload": payload})
        if result["valid"]:
            st.success("입력 계약 통과 · 이 구조를 전문 Agent의 입력으로 사용할 수 있습니다.")
            st.json(result["result"])
        else:
            st.error("입력 계약 위반 · LLM과 MCP Tool 호출 전에 차단합니다.")
            st.json(result["errors"])


def show_role_contract_lab(contracts: dict) -> None:
    left, right = st.columns(2)
    with left:
        st.subheader("WeatherResult")
        st.json(contracts["WeatherResult"])
    with right:
        st.subheader("BudgetResult")
        st.json(contracts["BudgetResult"])
    st.caption("공통 summary가 아니라 역할이 실제로 필요로 하는 필드를 계약으로 만듭니다.")


def show_validation_lab(cases: dict) -> None:
    st.write("Agent가 반환했다고 가정한 JSON을 선택하거나 수정한 뒤 출력 계약으로 검증합니다.")
    case_name = st.selectbox("검증 사례", list(cases))
    selected = cases[case_name]
    payload_text = st.text_area("검증할 JSON", json.dumps(selected["payload"], ensure_ascii=False, indent=2), height=220, key=f"validation-payload-{case_name}")
    if st.button("계약 검증", type="primary", use_container_width=True):
        try:
            payload = json.loads(payload_text)
            result = api_post("/api/contracts/validate", {"contract_name": selected["contract_name"], "payload": payload})
            if result["valid"]:
                st.success("계약 통과")
                st.json(result["result"])
            else:
                st.error("계약 경계에서 차단")
                st.json(result["errors"])
        except json.JSONDecodeError as error:
            st.error(f"JSON 문법 오류: {error}")
        except requests.RequestException as error:
            st.error(f"API 오류: {error}")


def show_incomplete_lab(states: dict) -> None:
    labels = {"completed": "완료", "missing_information": "정보 부족", "execution_error": "실행 실패"}
    selected = st.radio("Agent 상태", list(labels), format_func=labels.get, horizontal=True)
    st.json(states[selected])
    actions = {"completed": "다음 Agent 실행", "missing_information": "사용자에게 추가 정보 요청", "execution_error": "실패 정책에 따라 Retry 또는 종료"}
    st.info(f"다음 행동: {actions[selected]}")


def show_multi_llm_lab(selected_example: str) -> None:
    st.write("Gemini Weather, Llama Place, GPT Budget, Gemma Safety Agent를 순서대로 실행합니다.")
    selected_index = LAB_REQUEST_EXAMPLES["07"].index(selected_example)
    message = st.text_area("사용자 요청", selected_example, height=100, key=f"multi-message-{selected_index}")
    if st.button("네 실제 LLM 실행", type="primary", use_container_width=True):
        with st.spinner("네 Agent가 역할별 계약으로 응답하고 있습니다..."):
            try:
                state = run_with_polling("multi-llm", {"message": message})
                st.session_state["multi-result"] = state.get("result") if state else None
            except requests.RequestException as error:
                st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("multi-result")
    if result:
        st.metric("계약 성공", f"{result['success_count']}/{result['total_count']}")
        for item in result["results"]:
            icon = "✅" if item["status"] == "completed" else "❌"
            with st.expander(f"{icon} {item['agent_id']} · {item['provider_requested']} · {item['model']}", expanded=True):
                st.json(item)


def show_verified_flow_lab(selected_example: str) -> None:
    st.write("GPT Budget Agent의 계약이 통과한 경우에만 Gemma Itinerary Agent를 실행합니다.")
    selected_index = LAB_REQUEST_EXAMPLES["08"].index(selected_example)
    message = st.text_area("사용자 요청", selected_example, height=100, key=f"flow-message-{selected_index}")
    if st.button("검증 결과 전달 실행", type="primary", use_container_width=True):
        with st.spinner("Budget 계약을 검증하고 다음 Agent 전달 여부를 결정합니다..."):
            try:
                state = run_with_polling("verified-flow", {"message": message})
                st.session_state["flow-result"] = state.get("result") if state else None
            except requests.RequestException as error:
                st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("flow-result")
    if result:
        if result["status"] == "completed":
            st.success("검증된 Budget가 Itinerary Agent에 전달되었습니다.")
        else:
            st.error("계약 또는 Provider 오류로 흐름이 중단되었습니다.")
        st.subheader("실행 Trace")
        st.dataframe(result["trace"], use_container_width=True)
        st.subheader("Agent 결과")
        st.json({"budget": result["budget"], "itinerary": result["itinerary"]})


def show_support_flow_lab(selected_example: str) -> None:
    st.write("고객 문의 분석 계약이 통과한 경우에만 답변 작성 Agent를 실행합니다.")
    selected_index = LAB_REQUEST_EXAMPLES["09"].index(selected_example)
    message = st.text_area("고객 문의", selected_example, height=110, key=f"support-message-{selected_index}")
    if st.button("고객지원 계약 흐름 실행", type="primary", use_container_width=True):
        try:
            state = run_with_polling("support-flow", {"message": message})
            st.session_state["support-result"] = state.get("result") if state else None
        except requests.RequestException as error:
            st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("support-result")
    if result:
        if result["status"] == "completed":
            st.success("검증된 문의 분석이 답변 작성 Agent에 전달되었습니다.")
        elif result["status"] == "needs_information":
            st.warning(f"추가 정보가 필요합니다: {result.get('missing_information', [])}")
        else:
            st.error("계약 또는 Provider 오류로 실행이 중단되었습니다.")
        st.subheader("실행 Trace")
        st.dataframe(result["trace"], use_container_width=True)
        st.subheader("Agent 결과")
        st.json({"analysis": result["analysis"], "response": result["response"]})


def show_task_execution_lab(tasks: list[dict]) -> None:
    task = next(task for task in tasks if task["task_id"] == "allocate_budget")
    st.write("AgentTask 명세를 실제 예산 Agent 실행에 연결합니다. 필수 입력이 빠지면 Agent를 호출하지 않습니다.")
    st.markdown("**기존 방식과 무엇이 다른가요?**")
    st.write("07~09는 실행할 Agent와 순서를 코드에 직접 적었습니다. 10은 AgentTask에 적힌 담당자·필수 입력·기대 출력을 실행 코드가 읽습니다.")
    st.markdown("**좋은 점** · 필요한 입력을 한곳에서 확인하고, 값이 빠지면 Agent 호출 전에 멈출 수 있습니다.")
    st.markdown("**주의할 점** · 완료 조건의 설명 문장만으로 검증되지는 않습니다. 예산 합계와 요청 한도는 별도 Python 코드가 확인하며, Task 명세와 검증 코드를 함께 맞춰야 합니다.")
    st.subheader("실행할 AgentTask")
    st.json(task)
    default_inputs = {"destination": "부산", "days": 3, "people": 1, "total_budget": 600000}
    input_text = st.text_area("Task 입력 JSON", json.dumps(default_inputs, ensure_ascii=False, indent=2), height=180)
    if st.button("AgentTask 실행", type="primary", use_container_width=True):
        try:
            inputs = json.loads(input_text)
            if not isinstance(inputs, dict):
                st.error("Task 입력은 JSON 객체여야 합니다.")
                return
            with st.spinner("입력을 확인하고 Budget Agent를 실행합니다..."):
                result = api_post("/api/tasks/execute", {"task_id": task["task_id"], "inputs": inputs}, timeout=180)
            status = result["status"]
            if status == "completed":
                st.success("Task 완료: 입력·출력 계약과 완료 조건을 통과했습니다.")
            elif status == "needs_information":
                st.warning(f"필수 입력이 부족합니다: {result['missing_information']}")
            elif status == "invalid_input":
                st.error("입력 계약을 통과하지 못했습니다.")
            else:
                st.error("Agent 실행 또는 출력·완료 조건 검증에 실패했습니다.")
            st.subheader("Task 실행 Trace")
            st.dataframe(result["trace"], use_container_width=True)
            st.subheader("실행 결과")
            st.json(result)
        except json.JSONDecodeError as error:
            st.error(f"JSON 문법 오류: {error}")
        except requests.RequestException as error:
            st.error(f"API 실행 실패: {error}")


def show_task_message_lab() -> None:
    st.write("사용자 요청의 필수 입력을 모읍니다. 값이 모이면 날씨 → 장소 → 숙소 유형 → 예산 순서로 검증된 결과를 전달합니다.")
    st.caption("완전한 예시: 부산 2박 3일 여행, 1명, 대중교통, 예산 60만 원, 제약 없음")
    collected = st.session_state.setdefault("lab11_collected_inputs", {})
    message = st.text_area(
        "사용자 요청 또는 부족한 정보에 대한 답변",
        "부산 2박 3일 여행, 1명, 대중교통, 예산 60만 원, 제약 없음",
        height=100,
    )
    if st.button("요청 확인 및 여행 흐름 실행", type="primary", use_container_width=True):
        try:
            with st.spinner("필수 입력을 확인하고 Agent를 실행합니다..."):
                result = api_post(
                    "/api/tasks/execute-multi-from-message",
                    {"message": message, "known_inputs": collected},
                    timeout=360,
                )
            st.session_state["lab11_collected_inputs"] = result["collected_inputs"]
            st.session_state["lab11_result"] = result
        except requests.RequestException as error:
            st.error(f"API 실행 실패: {error}")
    if st.button("입력 초기화"):
        st.session_state["lab11_collected_inputs"] = {}
        st.session_state.pop("lab11_result", None)
        st.rerun()
    result = st.session_state.get("lab11_result")
    if result:
        st.subheader("현재까지 확인한 입력")
        st.json(result["collected_inputs"])
        if result["status"] == "needs_information":
            for question in result["questions"]:
                st.warning(question)
        elif result["status"] == "completed":
            st.success("날씨·장소·숙소·예산 검증을 통과했습니다.")
        elif result["status"] == "invalid_input":
            st.error(f"입력 계약 위반: {result['error']}")
        else:
            st.error("선행 Task가 실패해 후속 Task가 중단됐습니다. 아래 결과에서 원인을 확인하세요.")
        st.subheader("Task 실행 Trace")
        st.dataframe(result["trace"], use_container_width=True)
        for item in result["results"]:
            icon = "✅" if item["status"] == "completed" else "❌"
            with st.expander(f"{icon} {item['task']['task_id']} → {item['task']['agent_id']}", expanded=True):
                st.json(item)


st.set_page_config(page_title="Mini Multi-Agent 02", page_icon="🧩", layout="wide")
st.sidebar.title("🧩 Mini Multi-Agent 02")
MENU = [
    "과정 안내", "실행 환경 점검", "01 · Agent Role 정의", "02 · Task 분할",
    "03 · 입출력 계약", "04 · 역할별 계약", "05 · 계약 검증", "06 · 불완전 결과",
    "07 · 네 LLM 계약 실행", "08 · 검증 결과 전달", "09 · 다른 업무에 계약 적용",
    "10 · AgentTask 실제 실행", "11 · 날씨 → 장소 → 숙소 → 예산",
    "Contract Explorer", "Provider 상태", "MCP Tool",
]
menu = st.sidebar.radio("학습 메뉴", MENU)

try:
    labs = api_get("/api/labs")
except requests.RequestException as error:
    st.error(f"Backend에 연결할 수 없습니다: {error}")
    st.stop()

if menu == "과정 안내":
    st.title("Role → Task → Contract → 검증된 전달")
    st.write("왼쪽 메뉴를 위에서 아래로 진행하며 Agent 책임과 계약 경계를 학습합니다.")
    for lab_id, lab in labs.items():
        with st.expander(f"{lab_id} · {lab['title']} — {lab['question']}"):
            st.success(lab["answer_summary"])
            for detail in lab["answer_details"]:
                st.write(f"- {detail}")
            st.caption(f"예상 LLM 호출: {lab['expected_calls']}")
elif menu in {"실행 환경 점검", "Provider 상태"}:
    st.title(menu)
    try:
        providers = api_get("/api/providers")
        st.dataframe([{"provider": name, **status} for name, status in providers.items()], use_container_width=True)
        st.caption("Llama와 Gemma는 같은 aidevs-ollama Server에서 서로 다른 Model을 사용합니다.")
        sources = api_get("/api/data-sources")
        st.subheader("MCP Data Source")
        st.dataframe([{"Tool 영역": "날씨", "현재 Source": sources["weather"]}, {"Tool 영역": "장소·비용", "현재 Source": sources["travel"]}], use_container_width=True)
    except requests.RequestException as error:
        st.error(f"Provider 상태 확인 실패: {error}")
elif menu == "MCP Tool":
    st.title("MCP Tool과 실제 Data Source")
    try:
        status = api_get("/api/mcp-status")
        sources = api_get("/api/data-sources")
        st.success(f"MCP 연결됨 · Tool {status['tool_count']}개")
        st.dataframe(status["tools"], use_container_width=True)
        st.json(sources)
        st.caption("Tool Result의 source 필드에서 open-meteo와 postgresql 실제 출처를 확인합니다. Mock fallback은 없습니다.")
    except requests.RequestException as error:
        st.error(f"MCP 연결 실패: {error}")
elif menu == "Contract Explorer":
    st.title("Contract Explorer")
    contracts = api_get("/api/contracts")
    selected = st.selectbox("Pydantic 계약", list(contracts))
    st.json(contracts[selected])
else:
    lab_id = menu[:2]
    selected_example = show_header(lab_id, labs)
    if lab_id == "01":
        show_role_lab(api_get("/api/role-cards"))
    elif lab_id == "02":
        show_task_lab(api_get("/api/tasks"))
    elif lab_id == "03":
        show_io_contract_lab()
    elif lab_id == "04":
        show_role_contract_lab(api_get("/api/contracts"))
    elif lab_id == "05":
        show_validation_lab(api_get("/api/validation-cases"))
    elif lab_id == "06":
        show_incomplete_lab(api_get("/api/incomplete-states"))
    elif lab_id == "07":
        show_multi_llm_lab(selected_example)
    elif lab_id == "08":
        show_verified_flow_lab(selected_example)
    elif lab_id == "09":
        show_support_flow_lab(selected_example)
    elif lab_id == "10":
        show_task_execution_lab(api_get("/api/tasks"))
    else:
        show_task_message_lab()
