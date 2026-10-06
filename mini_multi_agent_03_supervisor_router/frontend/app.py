"""03 Supervisor와 Router 강의를 왼쪽 메뉴로 진행하는 Streamlit 화면입니다."""

import json
import os
import time
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

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
    "10": ["backend/app/orchestration/moving_supervisor.py", "backend/app/schemas/moving.py", "backend/app/agents/definitions/moving_workers.yaml", "mcp_server/tools/moving_tools.py"],
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
    "10": [("POST", "/api/runs/moving-checklist"), ("POST", "/api/async-runs/moving-checklist"), ("GET", "/api/async-runs/{run_id}/snapshot")],
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
    "10": ("moving-checklist", "create_moving_run() → execute_moving_tracked() → moving_checklist_flow()"),
    "05": ("supervisor-loop", "create_async_run() → execute_tracked() → supervisor_loop()"),
    "07": ("supervisor-team", "create_async_run() → execute_tracked() → supervisor_loop()"),
    "08": ("internal-router", "create_async_run() → execute_internal_tracked() → run_internal_router_flow()"),
    "09": ("incident-plan", "create_async_run() → execute_incident_tracked() → incident_plan_flow()"),
}

LAB_ANALYSIS_QUESTIONS = {
    "10": ["이사 종류를 바꾸면 어떤 준비 항목이 달라지나요?", "Mock Tool의 항목이 빠지면 다음 Worker가 실행되나요?", "희망일이 임박하면 권장 준비일이 어떻게 표시되나요?"],
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
            if flow_name == "moving-checklist":
                with st.expander("실시간 실행 이력", expanded=False):
                    st.dataframe(snapshot["events"], use_container_width=True)
            else:
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


def show_trace(result: dict, *, nested: bool = False) -> None:
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
            title = f"{event.get('step', '?')}. {actor} · {action}"
            # Streamlit 1.41에서도 바깥 expander 안에 실행 기록을 표시할 수 있게 한다.
            panel = st.container(border=True) if nested else st.expander(title, expanded=True)
            with panel:
                if nested:
                    st.write(title)
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


def show_moving_checklist() -> None:
    from secrets import token_urlsafe
    session_key = st.session_state.setdefault("moving-session-key", token_urlsafe(32))
    updated_notes = st.session_state.pop("moving-updated-notes", None)
    if updated_notes is not None:
        st.session_state["moving-notes-input"] = updated_notes
    restore = st.session_state.pop("moving-restore-progress", None)
    if restore:
        for item in (st.session_state.get("moving-result") or {}).get("checklist", {}).get("items", []):
            base = f"{restore['prefix']}-{item['item_id']}"
            complete = item["item_id"] in restore["ids"]
            st.session_state[base] = complete
            value = "완료" if complete else "준비 전"
            st.session_state[base + "-status"] = value
            for location in ("priority", "all"):
                st.session_state[f"{base}-status-{location}"] = value
                st.session_state[f"{base}-status-check-{location}"] = complete
    st.write("출발지·도착지·희망일·이사 종류를 선택하면 이사 전·당일·후 체크리스트를 만듭니다.")
    st.caption("상황을 적으면 필요한 준비만 골라서 보여드립니다. 모르는 내용은 확인할 일로 남깁니다.")
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    labels = {"general": "일반이사", "semi_packing": "반포장이사", "full_packing": "포장이사"}
    with st.form("moving-form"):
        left, right = st.columns(2)
        origin = left.text_input("출발지", "서울 관악구 관악푸르지오 2차 아파트")
        destination = right.text_input("도착지", "서울 강북구 수유동 벽산아파트")
        moving_date = st.date_input("이사 희망일", max(date(2026, 10, 9), today), min_value=today)
        moving_type = st.radio("이사 종류", list(labels), index=0, format_func=lambda value: labels[value], horizontal=True)
        st.caption("일반이사: 직접 포장 범위 확인 · 반포장이사: 사용자·업체 분담 확인 · 포장이사: 업체 포장·정리 범위 확인. 실제 범위는 업체와 협의해야 합니다.")
        additional_notes = st.text_area(
            "내 이사 상황 (선택)",
            value="가져갈 큰 물건은 퀸사이즈 침대, 2000×600 사이즈 책상, 32인치 스탠바이미 모니터, 화장대입니다. 냉장고와 세탁기는 판매할 예정입니다. 가스레인지는 가스 전출 신청 후 전문 작업자의 가스 연결 분리·안전 조치가 완료되면 판매할 예정입니다. 에어컨은 전문 작업자에게 철거를 맡긴 뒤 폐기할 예정이고 인터넷은 새집으로 이전하려고 합니다. 양쪽 아파트의 엘리베이터 사용 시간과 이사 차량 주차 공간은 아직 확인하지 못했습니다. 자녀와 반려동물은 없습니다. 가스 전출·전입 준비와 폐기물 처리를 먼저 확인하고 싶습니다.",
            max_chars=2000, height=110,
            key="moving-notes-input",
            help="예시를 본인 상황에 맞게 수정하거나 지워도 됩니다. 보유 가전, 처분할 물건, 직접 할 일, 아직 확인하지 못한 사항을 적어 주세요. 비밀번호·계좌번호 등 민감한 정보는 입력하지 마세요.",
        )
        submitted = st.form_submit_button("이사 체크리스트 만들기", type="primary", use_container_width=True)
    answer_labels = {"building_access": "엘리베이터·주차", "internet": "인터넷", "gas": "가스", "waste_booking": "폐기", "school": "자녀", "care": "돌봄"}
    if submitted:
        st.session_state.pop("moving-result", None)
        if len(origin.strip()) < 2 or len(destination.strip()) < 2:
            st.error("출발지와 도착지를 입력하세요.")
        else:
            with st.spinner("참고사항 정리와 업무별 담당 에이전트가 체크리스트를 만들고 있습니다..."):
                try:
                    state = run_with_polling("moving-checklist", {"origin": origin, "destination": destination,
                                            "moving_date": moving_date.isoformat(), "moving_type": moving_type,
                                            "additional_notes": additional_notes.strip(), "session_key": session_key})
                    st.session_state["moving-result"] = state.get("result")
                    if state.get("result") is None:
                        st.error(state.get("error") or "실행에 실패했습니다.")
                    else:
                        st.rerun()
                except requests.HTTPError as error:
                    st.error(f"API 실행 실패: {error}")
                    if error.response is not None:
                        with st.expander("입력·서버 오류 내용"):
                            st.write(error.response.text)
                except (requests.RequestException, TimeoutError) as error:
                    st.error(f"API 실행 실패: {error}")
    result = st.session_state.get("moving-result")
    if not result:
        return
    reuse = result.get("state", {}).get("reuse", {})
    if reuse.get("reused_agents"):
        st.caption(f"검증된 담당 결과 {len(reuse['reused_agents'])}개 재사용 · 결과 버전 {reuse['result_version']}")
    if result["status"] == "completed":
        checklist = result["checklist"]
        conditions = checklist["conditions"]
        def regenerate_notes(text):
            if len(text) > 2000:
                st.error("수정 내용과 답변의 합계는 2,000자 이내로 입력하세요.")
                return
            payload = {**conditions, "additional_notes": text, "item_plans": [], "session_key": session_key}
            try:
                with st.spinner("수정한 내용을 AI가 다시 확인하고 있습니다..."):
                    refreshed = run_with_polling("moving-checklist", payload)
                if refreshed.get("result"):
                    st.session_state["moving-result"] = refreshed["result"]
                    st.session_state["moving-updated-notes"] = text
                    st.rerun()
                else:
                    st.error(refreshed.get("error") or "수정 내용을 반영하지 못했습니다.")
            except (requests.RequestException, TimeoutError) as error:
                st.error(f"수정 내용 전달 실패: {error}")
        st.success(f"{conditions['moving_date']} · {labels[conditions['moving_type']]} 체크리스트 생성 완료")
        st.write(f"{conditions['origin']} → {conditions['destination']}")
        elapsed = result.get("state", {}).get("metrics", {}).get("elapsed_ms")
        if elapsed is not None:
            st.caption(f"생성 처리시간 {elapsed / 1000:.1f}초 · {'독립 업무 병렬 설정' if conditions.get('parallel_workers') else '순차 실행 설정'}")
        if checklist.get("notes_summary"):
            with st.expander("자세히 보기 · 내 상황 요약", expanded=False):
                notes = checklist["notes_summary"]
                categories = {"keep": "가져갈 물품", "sell": "판매", "dispose": "폐기", "service": "서비스 작업", "constraint": "제약·미확인", "household": "가족 상황", "priority": "우선 확인 희망", "other": "기타"}
                rows = [{"분류": categories[fact["category"]], "사용자 상황": fact["detail"]}
                        for fact in notes["facts"]]
                with st.form(f"moving-summary-edit-{result['run_id']}"):
                    import pandas as pd
                    frame = pd.DataFrame(rows, columns=["분류", "사용자 상황"])
                    edited = st.data_editor(frame, num_rows="dynamic", hide_index=True, use_container_width=True,
                        column_config={"분류": st.column_config.SelectboxColumn(options=list(categories.values())),
                                       "사용자 상황": st.column_config.TextColumn(required=True)})
                    st.caption("행을 수정·추가·삭제한 뒤 반영하세요. 수정한 표를 새로운 사용자 상황으로 보내 전체 준비 목록을 다시 검증합니다.")
                    apply_summary = st.form_submit_button("수정한 상황 반영하기")
                if apply_summary:
                    text = "\n".join(str(row.get("사용자 상황") or "").strip() for row in edited.fillna("").to_dict("records") if str(row.get("사용자 상황") or "").strip())
                    regenerate_notes(text)
        responsibility = {"user": "사용자", "provider": "업체", "confirm_with_provider": "업체와 확인"}
        visible_items = [item for item in checklist["items"] if item.get("applicability") != "not_applicable"]
        hidden_count = len(checklist["items"]) - len(visible_items)
        checklist_key = f"moving-check-{reuse.get('input_hash', result['run_id'])}"
        def status_key(item):
            return f"{checklist_key}-{item['item_id']}-status"
        def sync_status(widget, item):
            checked = bool(st.session_state[widget])
            st.session_state[status_key(item)] = "완료" if checked else "준비 전"
            st.session_state[f"{checklist_key}-{item['item_id']}"] = checked
            for location in ("priority", "all"):
                st.session_state[f"{status_key(item)}-check-{location}"] = checked
        def checklist_sentence(item):
            import re
            parts = re.split(r"(?<=[.!?])\s+|\n+", item["action"].strip())
            return "; ".join(part.rstrip(".!? ") for part in parts if part.strip()) + "."
        def status_control(item, location):
            key = f"{status_key(item)}-check-{location}"
            if key not in st.session_state:
                st.session_state[key] = bool(st.session_state.get(f"{checklist_key}-{item['item_id']}", False))
            st.checkbox(checklist_sentence(item), key=key,
                         on_change=sync_status, args=(key, item))
        done = sum(bool(st.session_state.get(f"{checklist_key}-{item['item_id']}", False))
                   for item in visible_items)
        st.subheader("전체 준비 목록")
        st.caption(f"완료 {done} / {len(visible_items)}개 · 해당 없는 항목 {hidden_count}개 제외")
        st.progress(done / len(visible_items) if visible_items else 1.0)
        st.caption("체크 표시는 같은 입력의 현재 브라우저 세션에서 유지됩니다. 입력을 바꾸면 새 목록의 완료 표시를 다시 확인하세요. 예약·신청 완료를 외부 시스템에서 확인하지 않습니다.")
        st.caption("재사용 결과는 브라우저별 임시 키로 구분해 서버 Redis에 최대 1시간 보관합니다. 로그인 기반 저장 서비스는 아닙니다.")
        if checklist.get("unresolved_questions"):
            with st.expander("추가로 확인할 사항", expanded=False):
                with st.form(f"moving-question-replies-{result['run_id']}"):
                    replies = []
                    for index, question in enumerate(checklist["unresolved_questions"]):
                        label = question.split(":", 1)[-1].strip()
                        answer = st.text_input(label, max_chars=500, key=f"moving-reply-{result['run_id']}-{index}")
                        if answer.strip(): replies.append(f"확인 사항: {label}\n사용자 답변: {answer.strip()}")
                    send_replies = st.form_submit_button("답변을 AI에 보내고 목록 갱신")
                if send_replies:
                    if not replies:
                        st.warning("확인한 답변을 하나 이상 입력하세요.")
                    else:
                        regenerate_notes(conditions.get("additional_notes", "") + "\n" + "\n".join(replies))
        with st.expander("공식 안내 바로가기", expanded=False):
            st.caption("개인 주소·참고사항을 외부에 전송하지 않습니다. 접속 확인은 내용의 최신성이나 신청 완료를 보장하지 않습니다.")
            if st.button("공식 안내 사이트 접속 확인"):
                try:
                    response = requests.get(f"{API}/api/moving-references/check", timeout=10)
                    response.raise_for_status()
                    st.session_state["moving-reference-status"] = {item["source_id"]: item for item in response.json()}
                except requests.RequestException:
                    st.warning("공식 안내 접속 확인에 실패했습니다. 링크에서 직접 확인하세요.")
            for source in checklist.get("official_references", []):
                st.link_button(source["title"], source["url"])
                st.caption(source["description"])
                checked = st.session_state.get("moving-reference-status", {}).get(source["source_id"])
                if checked:
                    st.caption(f"{'접속 응답 확인' if checked['status'] == 'reachable' else '자동 접속 확인 불가 · 직접 확인 필요'} · 조회 시각 {checked['checked_at']}")
        item_titles = {item["item_id"]: item["title"] for item in checklist["items"]}
        for phase, title in [("before", "이사 전"), ("moving_day", "이사 당일"), ("after", "이사 후")]:
            phase_items = [item for item in visible_items if item["phase"] == phase]
            if not phase_items:
                continue
            phase_done = sum(bool(st.session_state.get(f"{checklist_key}-{item['item_id']}", False)) for item in phase_items)
            with st.expander(f"{title} · 완료 {phase_done}/{len(phase_items)}개", expanded=False):
                for item in phase_items:
                    normal_key = f"{checklist_key}-{item['item_id']}"
                    with st.container(border=True):
                        status_control(item, "all")
                        offset = item["days_offset"]
                        day_label = f"D{offset}" if offset < 0 else ("D-DAY" if offset == 0 else f"D+{offset}")
                        color = "blue" if offset < 0 else ("orange" if offset == 0 else "green")
                        st.markdown(f":{color}-background[**{day_label}**] · {item['recommended_date']} · 담당: {responsibility[item['responsibility']]}")
                        if item.get("depends_on"):
                            st.caption("먼저 준비·완료할 일: " + " · ".join(item_titles[key] for key in item["depends_on"]))
                        if item.get("applicability", "needs_confirmation") == "needs_confirmation":
                            st.caption(f"해당 여부 확인: {item['condition']}")
                        if item["item_id"] in answer_labels:
                            with st.form(f"moving-card-answer-{item['item_id']}"):
                                answer = st.text_input("확인한 내용", value=conditions.get("clarifications", {}).get(item["item_id"], ""), max_chars=500)
                                update = st.form_submit_button("이 내용으로 준비 목록 갱신")
                            if update:
                                payload = dict(conditions)
                                payload["session_key"] = session_key
                                payload["clarifications"] = dict(conditions.get("clarifications", {}))
                                if answer.strip(): payload["clarifications"][item["item_id"]] = answer.strip()
                                else: payload["clarifications"].pop(item["item_id"], None)
                                try:
                                    refreshed = run_with_polling("moving-checklist", payload)
                                    if refreshed.get("result"):
                                        st.session_state["moving-result"] = refreshed["result"]
                                        st.rerun()
                                except (requests.RequestException, TimeoutError) as error:
                                    st.error(f"목록 갱신 실패: {error}")
        exported_graph = [{**task, "status": "user_done" if st.session_state.get(f"{checklist_key}-{task['task_id']}") else
                           ("in_progress" if st.session_state.get(f"{checklist_key}-{task['task_id']}-status") == "진행 중" else task["status"])}
                          for task in checklist.get("task_graph", [])]
        left, right = st.columns(2)
        with left:
            if st.button("완료 표시 임시 저장"):
                try:
                    api_post("/api/moving-session/progress", {"session_key": session_key, "input_hash": reuse["input_hash"],
                             "completed_ids": [item["item_id"] for item in visible_items if st.session_state.get(f"{checklist_key}-{item['item_id']}")]})
                    st.success("완료 표시를 최대 1시간 임시 저장했습니다.")
                except requests.RequestException:
                    st.warning("임시 저장에 실패했습니다. 저장 기간이 지났다면 다시 생성하세요.")
        with right:
            if st.button("저장한 완료 표시 불러오기"):
                try:
                    saved = api_post("/api/moving-session/progress/read", {"session_key": session_key})
                    if saved.get("input_hash") != reuse["input_hash"]:
                        st.warning("현재 입력과 일치하는 저장 기록이 없습니다.")
                    else:
                        st.session_state["moving-restore-progress"] = {"prefix": checklist_key, "ids": saved["completed_ids"]}
                        st.rerun()
                except requests.RequestException:
                    st.warning("완료 표시를 불러오지 못했습니다.")
        if st.button("내 임시 결과·실행 기록 삭제"):
            try:
                api_post("/api/moving-session/delete", {"session_key": session_key})
                for key in list(st.session_state):
                    if key.startswith("moving-"):
                        del st.session_state[key]
                st.rerun()
            except requests.RequestException:
                st.error("서버 삭제에 실패했습니다. 다시 시도하세요.")
        st.download_button("체크리스트 데이터 다운로드", json.dumps({**checklist, "items": visible_items, "task_graph": exported_graph}, ensure_ascii=False, indent=2),
                           file_name="moving_checklist.json", mime="application/json")
    elif result["status"] == "needs_information":
        st.warning(result["reason_message"])
        st.write(result["questions"])
    else:
        st.error(f"생성 중단: {result.get('reason_message', result['reason'])}")
        if result.get("error"):
            st.write(result["error"])
    with st.expander("자세히 보기 · 학습용 실행 기록과 출력 계약", expanded=False):
        st.caption(f"실행 번호: {result['run_id']} · 이번 실행 모델 호출: {result['llm_calls']}회")
        show_trace(result, nested=True)
        st.json(result["state"])


st.set_page_config(page_title="Mini Multi-Agent 03", page_icon="🧭", layout="wide")
st.sidebar.title("🧭 Mini Multi-Agent 03")
MENU = [
    "과정 안내", "실행 환경 점검", "01 · Rule Router", "02 · LLM Router",
    "03 · Routing 계약", "04 · Supervisor 결정", "05 · Supervisor–Worker Loop",
    "06 · Router vs Supervisor", "07 · Supervisor와 세 Worker 협업",
    "08 · 다른 업무에 Router 적용", "09 · 검토 피드백으로 계획 수정",
    "10 · 이사 체크리스트",
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
    for lab_id, lab in sorted(labs.items()):
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
    elif lab_id == "10":
        show_moving_checklist()
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
