"""03 Supervisor와 Router 강의를 왼쪽 메뉴로 진행하는 Streamlit 화면입니다."""

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
SUPPORT_EXAMPLES = [
    "ORDER-102 배송 상태를 알려 주세요.",
    "환불 정책을 알려 주세요.",
    "로그인이 되지 않습니다.",
    "ORDER-102 배송이 늦어서 환불하고 싶습니다.",
]
INTERNAL_EXAMPLES = [
    "사내 시스템 접근 권한이 필요합니다.",
    "노트북 화면이 켜지지 않습니다.",
    "3층 회의실 에어컨이 작동하지 않습니다.",
    "도움이 필요합니다.",
]
CODE_MESSAGE = "사용자 입력 길이를 검사하는 기능을 분석하고 구현한 뒤 검토해 주세요."
INCIDENT_MESSAGE = "3층 회의실 프로젝터에 화면이 나오지 않습니다. 안전한 점검 안내문을 만들고 검토해 주세요."

LAB_CODE_PATHS = {
    "01": ["backend/app/orchestration/engine.py · rule_router_agent()"],
    "02": ["backend/app/orchestration/engine.py · llm_router_flow()"],
    "03": ["backend/app/schemas/workflow.py · SupportRouteDecision"],
    "04": ["backend/app/orchestration/engine.py · supervisor_decision()"],
    "05": ["backend/app/orchestration/engine.py · supervisor_loop()"],
    "06": ["backend/app/services/catalog.py"],
    "07": ["backend/app/agents/definitions/workers.yaml"],
    "08": ["backend/app/orchestration/internal_flow.py", "backend/app/schemas/workflow.py · InternalRouteDecision"],
    "09": ["backend/app/orchestration/incident_plan.py", "backend/app/schemas/workflow.py · IncidentReviewResult", "backend/app/agents/definitions/workers.yaml"],
}

LAB_BACKEND_ENDPOINTS = {
    "01": [("GET", "/api/rule-router")],
    "02": [("POST", "/api/async-runs/router"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "03": [("GET", "/api/routing-validation-cases"), ("POST", "/api/routing/validate")],
    "04": [("POST", "/api/runs/supervisor-decision")],
    "05": [("POST", "/api/async-runs/supervisor-loop"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "06": [("GET", "/api/architecture-cases")],
    "07": [("POST", "/api/async-runs/supervisor-team"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "08": [("POST", "/api/async-runs/internal-router"), ("GET", "/api/async-runs/{run_id}/snapshot")],
    "09": [("POST", "/api/async-runs/incident-plan"), ("GET", "/api/async-runs/{run_id}/snapshot")],
}

LAB_FLOW_DISPATCH = {
    "05": ("supervisor-loop", "create_async_run() → execute_tracked() → supervisor_loop()"),
    "07": ("supervisor-team", "create_async_run() → execute_tracked() → supervisor_loop()"),
    "08": ("internal-router", "create_async_run() → execute_internal_tracked() → run_internal_router_flow()"),
    "09": ("incident-plan", "create_async_run() → execute_incident_tracked() → incident_plan_flow()"),
}

LAB_ANALYSIS_QUESTIONS = {
    "01": ["어떤 단어를 보고 담당 Agent를 선택했나요?"],
    "02": ["Router가 선택한 Worker 하나만 실행되었나요?"],
    "03": ["목록에 없는 Agent 이름은 왜 차단되나요?"],
    "04": ["완료된 작업이 달라지면 다음 Agent도 달라지나요?"],
    "05": ["모든 Worker가 끝나면 누가 실행을 종료하나요?"],
    "06": ["한 번 선택하면 Router, 반복 선택하면 Supervisor라고 설명할 수 있나요?"],
    "07": ["Provider가 달라도 Agent 실행 순서는 같나요?"],
    "08": ["고객지원 Router와 실행 순서가 같은가요?", "정보가 부족할 때 Worker가 실행되지 않나요?"],
    "09": ["첫 검토가 거절되면 어떤 feedback이 계획 수정에 전달되나요?", "두 번째 검토도 거절되면 왜 멈추나요?"],
}


def api_get(path: str, timeout: int = 10):
    response = requests.get(f"{API}{path}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict, timeout: int = 10):
    response = requests.post(f"{API}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def run_with_polling(flow_name: str, payload: dict, max_wait_seconds: int = 900):
    """비동기 실행을 시작하고 Redis 상태를 1초마다 조회합니다."""
    created = api_post(f"/api/async-runs/{flow_name}", payload)
    run_id = created["run_id"]
    st.caption(f"실행 ID: {run_id}")
    progress = st.progress(0)
    status_area = st.empty()
    event_area = st.empty()
    started_at = time.monotonic()
    consecutive_timeouts = 0

    while time.monotonic() - started_at < max_wait_seconds:
        try:
            snapshot = api_get(f"/api/async-runs/{run_id}/snapshot", timeout=30)
            consecutive_timeouts = 0
        except requests.Timeout:
            consecutive_timeouts += 1
            status_area.warning(
                f"상태 조회 응답이 늦습니다 ({consecutive_timeouts}/3). "
                f"실행 ID {run_id}의 작업은 계속 진행될 수 있어 다시 조회합니다."
            )
            if consecutive_timeouts >= 3:
                raise TimeoutError(f"상태 조회가 세 번 지연되었습니다. 실행 ID: {run_id}")
            continue
        state = snapshot["state"]
        progress.progress(state.get("progress_percent", 0))
        status_area.info(
            f"현재 Agent: {state.get('current_agent') or '-'} · "
            f"단계: {state.get('current_stage')} · {state.get('message')}"
        )
        with event_area.container():
            st.write("실시간 실행 이력")
            st.dataframe(snapshot["events"], use_container_width=True)
        if state["status"] in {"completed", "failed"}:
            return state
        time.sleep(1)
    raise TimeoutError("실행 상태 조회 시간이 초과되었습니다.")


def show_header(lab_id: str, labs: dict) -> None:
    lab = labs[lab_id]
    st.title(f"Lab {lab_id} · {lab['title']}")
    st.code(
        "\n".join(f"{method} {API}{endpoint}" for method, endpoint in LAB_BACKEND_ENDPOINTS[lab_id]),
        language="http",
    )
    st.caption("Backend 호출: 이 화면에서 조회하거나 실행하는 API입니다. {run_id}는 실행 때 받은 ID로 바뀝니다.")
    if lab_id in LAB_FLOW_DISPATCH:
        flow_name, dispatch = LAB_FLOW_DISPATCH[lab_id]
        st.write(f"**전달하는 `flow_name`:** `{flow_name}`")
        st.caption(f"Backend 분기: {dispatch}")
    elif lab_id == "06":
        st.caption("이 화면은 GET /api/architecture-cases만 조회합니다. flow_name을 전달하거나 비동기 실행을 시작하지 않습니다.")
    st.info(f"생각할 질문 · {lab['question']}")
    st.success(f"핵심 답변 · {lab['answer_summary']}")
    with st.expander("상세 답변 보기"):
        for detail in lab["answer_details"]:
            st.write(f"- {detail}")
    left, right = st.columns(2)
    left.metric("실제 LLM", "사용" if lab["real_llm"] else "미사용")
    right.metric("예상 호출", lab["expected_calls"])
    with st.expander("실행 후 함께 읽을 코드"):
        for path in LAB_CODE_PATHS[lab_id]:
            st.code(path, language="text")
    with st.expander("실행 결과 분석 질문"):
        for question in LAB_ANALYSIS_QUESTIONS[lab_id]:
            st.write(f"- {question}")


def show_trace(result: dict) -> None:
    status = result.get("status", "unknown")
    if status == "completed":
        st.success(f"실행 상태: {status}")
    elif status == "needs_information":
        st.warning(f"실행 상태: {status}")
    else:
        st.error(f"실행 상태: {status} · 종료 이유: {result.get('reason', '-')}")
    if result.get("trace"):
        st.subheader("실행 Trace")
        for event in result["trace"]:
            actor = event.get("actor", "unknown")
            action = event.get("action", "event")
            with st.expander(f"{event.get('step', '?')}. {actor} · {action}", expanded=True):
                st.json(event)


def show_rule_router() -> None:
    results = api_get("/api/rule-router")
    st.dataframe([{"요청": item["message"], "예상": item["expected"], "선택": item["decision"]["selected_agent"], "일치": item["expected"] == item["decision"]["selected_agent"], "학습 포인트": item.get("learning_point", "단일 의도 분류")} for item in results], use_container_width=True)

    def result_label(index: int) -> str:
        return results[index]["message"]

    selected = st.selectbox("상세 결과", range(len(results)), format_func=result_label)
    st.json(results[selected]["decision"])


def show_llm_router() -> None:
    selected = st.selectbox("실행할 고객 문의", SUPPORT_EXAMPLES)
    selected_index = SUPPORT_EXAMPLES.index(selected)
    message = st.text_area("고객 문의", selected, height=110, key=f"support-message-{selected_index}")
    if st.button("실제 Router와 선택 Worker 실행", type="primary", use_container_width=True):
        with st.spinner("GPT Router가 담당 Worker를 선택하고 있습니다..."):
            try:
                state = run_with_polling("router", {"message": message})
                st.session_state["router-result"] = state.get("result")
            except (requests.RequestException, TimeoutError) as error:
                st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("router-result")
    if result:
        show_trace(result)
        st.subheader("Router 결정")
        st.json(result["route"])
        st.subheader("선택 Worker 결과")
        st.json(result["worker"])


def show_internal_router() -> None:
    selected = st.selectbox("실행할 사내 요청", INTERNAL_EXAMPLES)
    selected_index = INTERNAL_EXAMPLES.index(selected)
    message = st.text_area("사내 요청", selected, height=110, key=f"internal-message-{selected_index}")
    if st.button("사내 요청 Router와 선택 Worker 실행", type="primary", use_container_width=True):
        with st.spinner("GPT Router가 사내 요청 담당자를 선택하고 있습니다..."):
            try:
                state = run_with_polling("internal-router", {"message": message})
                st.session_state["internal-router-result"] = state.get("result")
            except (requests.RequestException, TimeoutError) as error:
                st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("internal-router-result")
    if result:
        show_trace(result)
        st.subheader("Router 결정")
        st.json(result["route"])
        if result["worker"] is None:
            st.info("정보가 부족하여 Worker를 실행하지 않았습니다.")
        else:
            st.subheader("선택 Worker 결과")
            st.json(result["worker"])


def show_router_contract() -> None:
    cases = api_get("/api/routing-validation-cases")
    name = st.selectbox("검증 사례", list(cases), format_func=lambda key: cases[key]["title"])
    case = cases[name]
    st.write(f"**고객 질문:** {case['request']}")
    st.caption("아래 JSON은 이 질문에 대해 Router가 반환했다고 가정한 결과입니다. 이 화면은 LLM을 호출하지 않고 출력 계약을 검증합니다.")
    st.info(f"확인할 문제: {case['issue']}")
    payload_text = st.text_area(
        "Router 결과 JSON (수정 가능)",
        json.dumps(case["payload"], ensure_ascii=False, indent=2),
        height=200,
        key=f"routing-payload-{name}",
    )
    if st.button("Routing 계약 검증", type="primary", use_container_width=True):
        try:
            result = api_post("/api/routing/validate", {"payload": json.loads(payload_text)})
            if result["valid"]:
                st.success("Routing 계약 통과")
                st.json(result["result"])
                if result["result"]["selected_agent"] == "request_information":
                    questions = result["result"]["missing_information"]
                    st.warning("사용자에게 추가로 물어볼 정보: " + ", ".join(questions))
                    st.caption("추가 정보를 받은 뒤 Router를 다시 실행합니다. 지금은 Worker를 실행하지 않습니다.")
                else:
                    st.info(f"다음 단계: {result['result']['selected_agent']} 실행")
            else:
                st.error("Routing 계약에서 차단")
                st.json(result["errors"])
                st.info("이 오류는 Router 출력 계약의 문제입니다. 사용자에게 입력을 요구하기 전에 Router 결과를 고치거나 다시 생성해야 합니다.")
                if name == "missing_information_list":
                    st.write("예: `missing_information`에 `배송·환불·로그인 중 어떤 도움이 필요한지`를 넣으면, 통과 후 그 항목을 사용자에게 질문할 수 있습니다.")
                elif name == "contradictory_state":
                    st.write("예: 주문 번호가 꼭 필요하다면 `selected_agent`를 `request_information`으로 바꾸고, `missing_information`에 `주문 번호`를 남깁니다.")
            if result["valid"] == case["expected_valid"]:
                st.caption("선택한 기본 사례의 예상 검증 결과와 일치합니다. JSON을 수정했다면 예상 결과도 달라질 수 있습니다.")
        except json.JSONDecodeError as error:
            st.error(f"JSON 문법 오류: {error}")


def show_supervisor_decision() -> None:
    completed_count = st.select_slider("지금까지 완료된 작업 수", options=[0, 1, 2, 3], value=1)
    plan = ["analyst_agent", "developer_agent", "reviewer_agent"]
    completed = plan[:completed_count]
    outputs = {agent_id: f"{agent_id}의 검증된 결과" for agent_id in completed}
    st.caption("State는 지금까지 완료된 Agent와 그 결과를 모아 둔 현재 상태입니다.")
    st.json({"완료된 Agent": completed, "완료된 결과": outputs})
    if st.button("실제 GPT Supervisor 결정", type="primary", use_container_width=True):
        with st.spinner("Supervisor가 현재 State를 읽고 있습니다..."):
            try:
                st.session_state["decision-result"] = api_post("/api/runs/supervisor-decision", {"message": CODE_MESSAGE, "completed_agents": completed, "outputs": outputs}, timeout=180)
            except requests.RequestException as error:
                st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("decision-result")
    if result:
        st.metric("Python이 예상한 다음 Agent", result["expected_next"])
        st.metric("Supervisor 선택이 순서와 일치함", result["transition_valid"])
        with st.expander("Supervisor 전체 응답 보기"):
            st.json(result["decision"])


def run_supervisor(flow_name: str, state_key: str, button_label: str) -> None:
    message = st.text_area("개발 요청", CODE_MESSAGE, height=100, key=f"message-{state_key}")
    if st.button(button_label, type="primary", use_container_width=True):
        with st.spinner("Supervisor와 Worker가 State를 갱신하고 있습니다..."):
            try:
                state = run_with_polling(flow_name, {"message": message})
                st.session_state[state_key] = state.get("result")
            except (requests.RequestException, TimeoutError) as error:
                st.error(f"API 실행 실패: {error}")
    result = st.session_state.get(state_key)
    if result:
        show_trace(result)
        st.subheader("최종 State")
        st.json(result["state"])


st.set_page_config(page_title="Mini Multi-Agent 03", page_icon="🧭", layout="wide")
st.sidebar.title("🧭 Mini Multi-Agent 03")
MENU = [
    "과정 안내", "실행 환경 점검", "01 · Rule Router", "02 · LLM Router",
    "03 · Routing 계약", "04 · Supervisor 결정", "05 · Supervisor–Worker Loop",
    "06 · Router vs Supervisor", "07 · Supervisor와 세 Worker 협업",
    "08 · 다른 업무에 Router 적용", "09 · 검토 피드백으로 계획 수정",
    "Agent Registry · YAML", "MCP Tool", "Provider 상태",
]
menu = st.sidebar.radio("학습 메뉴", MENU)

try:
    labs = api_get("/api/labs")
except requests.RequestException as error:
    st.error(f"Backend에 연결할 수 없습니다: {error}")
    st.stop()

if menu == "과정 안내":
    st.title("요청에 맞는 Agent를 선택하기")
    st.write("01에서 Router와 Supervisor를 실행했고, 02에서 Agent 결과를 계약으로 검증했습니다. 03에서는 두 내용을 연결해 누가 실행할지 선택합니다.")
    st.info("Router는 Worker를 한 번 선택합니다. Supervisor는 완료 결과를 보며 다음 Worker를 반복 선택합니다.")
    st.markdown("""
    **쉬운 학습 순서**

    1. Keyword로 담당 Agent를 선택합니다.
    2. LLM이 담당 Agent를 선택하게 합니다.
    3. 선택 결과가 계약을 지키는지 확인합니다.
    4. 완료된 작업을 보고 다음 Agent를 선택합니다.
    5. 선택을 반복하고 모든 작업이 끝나면 종료합니다.
    """)
    for lab_id, lab in labs.items():
        with st.expander(f"{lab_id} · {lab['title']} — {lab['question']}"):
            st.success(lab["answer_summary"])
            for detail in lab["answer_details"]:
                st.write(f"- {detail}")
            st.caption(f"예상 LLM 호출: {lab['expected_calls']}")
elif menu in {"실행 환경 점검", "Provider 상태"}:
    st.title(menu)
    providers = api_get("/api/providers")
    st.dataframe([{"provider": name, **status} for name, status in providers.items()], use_container_width=True)
    st.caption("Llama와 Gemma는 같은 aidevs-ollama Server에서 순차 실행합니다.")
elif menu == "Agent Registry · YAML":
    st.title("Python Core Agent와 YAML Worker Registry")
    st.write("Router·Supervisor는 Python, 반복되는 Worker 선언은 YAML로 관리합니다.")
    st.json(api_get("/api/agents"))
elif menu == "MCP Tool":
    st.title("PostgreSQL MCP Tool")
    st.write("Worker는 데이터베이스에 직접 연결하지 않고 허용된 MCP Tool만 호출합니다.")
    st.json(api_get("/api/mcp-status"))
else:
    lab_id = menu[:2]
    show_header(lab_id, labs)
    if lab_id == "01":
        show_rule_router()
    elif lab_id == "02":
        show_llm_router()
    elif lab_id == "03":
        show_router_contract()
    elif lab_id == "04":
        show_supervisor_decision()
    elif lab_id == "05":
        st.markdown("""
        **실제로 진행되는 순서**

        1. Supervisor가 `analyst_agent`를 선택합니다.
        2. Analyst가 요청을 분석하고 결과를 반환합니다.
        3. Supervisor가 Analyst의 완료 상태를 확인하고 `reviewer_agent`를 선택합니다.
        4. Reviewer가 분석 결과를 검토하고 결과를 반환합니다.
        5. Supervisor가 두 Worker의 완료 상태를 보고 `finish`를 선택합니다.

        Supervisor 3회와 Worker 2회를 합쳐 정상 완료 시 **LLM을 5회 호출**합니다.
        """)
        st.info(
            "여기서 반복은 같은 Worker의 재시도가 아닙니다. Python의 while 루프가 "
            "'다음 Worker 선택 → Worker 실행 → 결과를 State에 저장'을 되풀이합니다. "
            "Supervisor는 갱신된 State를 받아 다음 행동을 제안하고, Python은 정해진 순서인지 확인합니다."
        )
        st.markdown("""
        **재작업을 위한 반복은 어떻게 다를까요?**

        Reviewer가 요구사항 누락을 발견했을 때
        `Analyst → Developer → Reviewer → Developer 수정 → Reviewer 재검토 → finish`처럼
        이전 Worker로 돌아갈 수 있습니다. 이를 구현하려면 Reviewer 결과에 `approved`와
        `feedback` 같은 판정 필드를 두고, Supervisor가 그 결과를 읽어 다시 실행할
        Worker를 선택하도록 해야 합니다. **현재 05번은 `Analyst → Reviewer → finish`의
        고정 순서만 허용**하므로 피드백에 따른 재작업은 실행하지 않습니다.
        """)
        run_supervisor("supervisor-loop", "loop-result", "최대 5회 Supervisor Loop 실행")
    elif lab_id == "06":
        st.dataframe(api_get("/api/architecture-cases"), use_container_width=True)
        st.info("한 번 선택하면 Router, 중간 결과를 보고 반복 선택하면 Supervisor를 먼저 검토합니다.")
    elif lab_id == "07":
        run_supervisor("supervisor-team", "team-result", "Supervisor와 세 Worker 실행")
    elif lab_id == "08":
        show_internal_router()
    else:
        st.caption("작은 예제: 회의실 프로젝터 화면이 나오지 않을 때의 점검 안내문을 만듭니다. 장비 조작은 실행하지 않습니다.")
        st.subheader("검토 결과에 따른 실행 흐름")
        st.code("""분석 → 계획 → 검토
              ├─ approved=true  → finish
              └─ approved=false → 계획 수정 → 재검토
                                      ├─ approved=true  → finish
                                      └─ approved=false → needs_attention""", language="text")
        st.write(
            "처음의 **분석 → 계획 → 검토** 순서는 정해져 있습니다. 상황에 따라 달라지는 "
            "부분은 Reviewer의 검증된 `approved`와 `feedback`을 받은 이후입니다."
        )
        st.info(
            "Python 오케스트레이터가 검토 결과를 보고 다음에 허용되는 Agent와 최대 수정 횟수 "
            "(한 번)를 결정합니다. Supervisor의 선택이 그 결정과 일치하는지도 검사합니다. "
            "실제 시스템 조치는 실행하지 않습니다."
        )
        message = st.text_area("사내 장애 요청", INCIDENT_MESSAGE, height=110, key="incident-message")
        demonstrate_revision = st.checkbox(
            "첫 검토 거절 → 계획 수정 → 재검토 흐름 재현",
            value=True,
            help="교육용으로 첫 Reviewer가 영향 범위 확인 단계를 피드백하도록 합니다.",
        )
        if st.button("장애 대응 Supervisor 실행", type="primary", use_container_width=True):
            with st.spinner("분석·계획·검토와 필요 시 수정을 진행하고 있습니다..."):
                try:
                    state = run_with_polling(
                        "incident-plan",
                        {"message": message, "demonstrate_revision": demonstrate_revision},
                    )
                    st.session_state["incident-result"] = state.get("result")
                except (requests.RequestException, TimeoutError) as error:
                    st.error(f"API 실행 실패: {error}")
        result = st.session_state.get("incident-result")
        if result:
            show_trace(result)
            if result["status"] == "needs_attention":
                st.warning("한 번 수정한 계획도 승인되지 않았습니다. 검토 feedback을 사람이 확인해야 합니다.")
            st.subheader("최종 State")
            st.json(result["state"])
