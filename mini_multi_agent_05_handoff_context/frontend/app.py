"""05 Handoff and Context를 왼쪽 메뉴로 학습하는 Streamlit 화면입니다."""

import json
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

LAB_GUIDES = {
    "01": ("backend/app/orchestration/engine.py · minimum_context_demo()", "제거된 Key가 다음 Agent의 업무에 정말 필요한가요?"),
    "02": ("backend/app/schemas/contracts.py · HandoffEnvelope", "책임과 실행을 추적하는 필드는 무엇인가요?"),
    "03": ("backend/app/orchestration/guards.py · validate_handoff()", "YAML 정책과 Python 검사는 각각 무엇을 담당하나요?"),
    "04": ("backend/app/schemas/contracts.py · HandoffState", "대상 Agent가 성공하기 전에 책임자가 바뀌지 않나요?"),
    "05": ("backend/app/orchestration/guards.py", "차단된 요청에서 대상 Agent가 실행되지 않나요?"),
    "06": ("backend/app/orchestration/engine.py · execute_handoff()", "Event에서 제안→검증→책임 이전 순서를 찾을 수 있나요?"),
    "07": ("backend/app/orchestration/internal_flow.py · run_internal_handoff()", "여행 Handoff와 같은 네 단계로 실행되나요?"),
    "08": ("backend/app/orchestration/routed_handoff.py · run_routed_handoff()", "선택된 경로에 따라 필수 Context가 어떻게 달라지나요?"),
    "09": ("backend/app/orchestration/refund_handoff.py · run_refund_handoff()", "상담 결과의 어떤 정보가 Handoff로 전달되나요?"),
}


LAB_API_CALLS = {
    "01": [("GET", "/api/minimum-context", "화면 진입 시 minimum_context_demo() 실행 · 전체 State에서 전달할 최소 Context 선택")],
    "02": [],
    "03": [("GET", "/api/registry", "화면 진입 시 등록 Agent와 YAML Handoff 경로·허용 Context 조회")],
    "04": [],
    "05": [("GET", "/api/guard-cases", "화면 진입 시 guard_cases_demo() 실행 · Guard 차단 사례 조회")],
    "06": [
        ("POST", "/api/runs/handoff", "실행 버튼 · JSON: destination, days, transport, user_id · execute_handoff()를 Background Task로 시작"),
        ("GET", "/api/runs/{run_id}/events", "실행 중 SSE로 Handoff Event 수신"),
        ("GET", "/api/runs/{run_id}/snapshot", "Event 수신 시 현재 책임자·상태 조회, SSE 종료 시 최종 상태 조회"),
    ],
    "07": [("POST", "/api/runs/internal-handoff", "실행 버튼 · JSON: employee_id, system_name, issue · run_internal_handoff() 실행")],
    "08": [
        ("GET", "/api/routed-handoff/routes", "화면 진입 시 세 경로의 필수·선택 Context 조회"),
        ("POST", "/api/runs/routed-handoff", "라우터 판단 → 경로별 Envelope 생성 → Guard 검증 → 대상 Agent 실행"),
    ],
    "09": [("POST", "/api/runs/refund-handoff", "상담 결과 → Envelope 생성 → Guard 검증 → 환불 Agent 결과")],
}

LAB_LOCAL_CONTENT = {
    "02": "이 화면에는 별도 실행 URL이 없습니다. Python의 HandoffEnvelope 계약에 필요한 필드를 화면에 예시로 표시합니다.",
    "04": "이 화면에는 별도 실행 URL이 없습니다. HandoffState의 책임 이전 순서를 화면에서 설명합니다. 실제 책임 이전은 06·07 실행에서 확인할 수 있습니다.",
}


def api_get(path: str):
    response = requests.get(f"{API}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict, *, read_timeout: int = 10):
    response = requests.post(f"{API}{path}", json=payload, timeout=(10, read_timeout))
    response.raise_for_status()
    return response.json()


def show_lab_header(lab_id: str, labs: dict) -> None:
    lab = labs[lab_id]
    code_path, analysis_question = LAB_GUIDES[lab_id]
    st.title(f"{lab_id} · {lab['title']}")
    st.caption("이 화면의 Backend 요청")
    if LAB_API_CALLS[lab_id]:
        for method, endpoint, action in LAB_API_CALLS[lab_id]:
            st.code(f"{method} {API}{endpoint}", language="text")
            st.caption(action)
    else:
        st.info(LAB_LOCAL_CONTENT[lab_id])
    st.info(f"생각할 질문 · {lab['question']}")
    st.success(f"핵심 답변 · {lab['answer_summary']}")
    with st.expander("상세 답변 보기"):
        for detail in lab["answer_details"]:
            st.write(f"- {detail}")
    left, right = st.columns(2)
    left.metric("실제 LLM", "사용" if lab["real_llm"] else "미사용")
    right.metric("예상 호출", lab["expected_calls"])
    with st.expander("실행 후 먼저 읽을 코드"):
        st.code(code_path, language="text")
    with st.expander("실행 결과 분석 질문"):
        st.write(f"- {analysis_question}")


def show_handoff_details(state: dict):
    st.subheader("Handoff 전달 내용과 점검 과정")
    st.caption("Weather → Itinerary 인계 1건의 실제 기록입니다. 각 단계의 데이터와 당시 책임자를 확인하세요.")
    trace = state.get("trace", [])
    if not trace:
        st.info("이 실행에는 상세 인계 기록이 없습니다. 변경된 Backend에서 다시 실행하면 표시됩니다.")
    for step in trace:
        with st.expander(f"{step['title']} · {step['status']}", expanded=True):
            st.write(step["message"])
            st.caption(f"이 단계의 책임자: {step['owner_agent']}")
            if step.get("data") is not None:
                st.json(step["data"])
    if state.get("error"):
        st.error(state["error"])
    result = state.get("result")
    if result:
        st.subheader(f"최종 여행 일정 · {result.get('destination', '')}")
        for index, plan in enumerate(result.get("day_plans", []), 1):
            st.write(f"**{index}일차**")
            st.write(plan)
        if result.get("applied_constraints"):
            st.write("**일정에 반영한 조건**")
            for constraint in result["applied_constraints"]:
                st.write(f"- {constraint}")


def show_internal_handoff_details(result: dict, *, flow_label: str = "사내 IT 접수 → 계정 지원"):
    st.subheader("Handoff 전달 내용과 점검 과정")
    st.caption(f"{flow_label} 인계 1건의 실제 기록입니다.")
    trace = result.get("trace", [])
    if trace and "title" in trace[0]:
        for step in trace:
            with st.expander(f"{step['title']} · {step['status']}", expanded=True):
                st.write(step["message"])
                st.caption(f"이 단계의 책임자: {step['owner_agent']}")
                if step.get("data") is not None:
                    st.json(step["data"])
    else:
        st.info("이 실행에는 상세 인계 기록이 없습니다. 변경된 Backend에서 다시 실행하면 표시됩니다.")
    if result.get("error"):
        st.error(result["error"])
    support = result.get("result")
    if support:
        st.subheader("계정 지원 Agent의 답변")
        st.write(support.get("summary", ""))
        for index, next_step in enumerate(support.get("next_steps", []), 1):
            st.write(f"{index}. {next_step}")


def run_handoff_sse(payload: dict):
    created = api_post("/api/runs/handoff", payload)
    run_id = created["run_id"]
    st.caption(f"run_id: {run_id}")
    progress = st.progress(0)
    status_area = st.empty()
    event_area = st.empty()
    events = []

    with requests.get(
        f"{API}/api/runs/{run_id}/events",
        headers={"Accept": "text/event-stream"},
        stream=True,
        timeout=(10, 600),
    ) as response:
        response.raise_for_status()
        event_name = "message"
        for line in response.iter_lines(decode_unicode=True):
            if not line or line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
                continue
            if not line.startswith("data:"):
                continue
            data = json.loads(line.removeprefix("data:").strip())
            if event_name == "handoff":
                events.append(data)
                event_area.dataframe(events, use_container_width=True)
                state = api_get(f"/api/runs/{run_id}/snapshot")
                completed = len([event for event in events if event["status"] in {"completed", "failed", "rejected"}])
                progress.progress(min(completed * 20, 95))
                status_area.info(f"현재 책임자: {state['owner_agent']} · Handoff: {state['handoff_status']}")
            elif event_name == "finished":
                progress.progress(100)
                return data
    return api_get(f"/api/runs/{run_id}/snapshot")


st.set_page_config(page_title="Mini Multi-Agent 05", page_icon="🤝", layout="wide")
st.sidebar.title("🤝 Mini Multi-Agent 05")
MENU = [
    "과정 안내", "실행 환경 점검", "01 · Minimum Context", "02 · Handoff Envelope",
    "03 · YAML Policy + Guard", "04 · Ownership Transition", "05 · Rejection and Failure",
    "06 · Real Agent Handoff", "07 · 다른 업무에 Handoff 적용",
    "08 · 라우터의 세 가지 Handoff",
    "09 · 간단한 환불 문의 Handoff",
    "Agent Registry · YAML", "MCP Tool", "Provider 상태",
]
menu = st.sidebar.radio("학습 메뉴", MENU)

try:
    labs = api_get("/api/labs")
except requests.RequestException as error:
    st.error(f"Backend 연결 실패: {error}")
    st.stop()

if menu == "과정 안내":
    st.title("최소 Context에서 안전한 책임 이전까지")
    st.code("제안 → 검증 → 수락 → 책임 이전 → 완료 또는 실패")
    st.info("Handoff는 단순 호출이 아니라 책임과 필요한 Context를 함께 넘기는 과정입니다.")
    for lab_id, lab in labs.items():
        with st.expander(f"{lab_id} · {lab['title']} — {lab['question']}"):
            st.success(lab["answer_summary"])
            for detail in lab["answer_details"]:
                st.write(f"- {detail}")
            st.caption(f"예상 LLM 호출: {lab['expected_calls']}")
elif menu in {"실행 환경 점검", "Provider 상태"}:
    st.title(menu)
    st.dataframe([{"provider": name, **value} for name, value in api_get("/api/providers").items()], use_container_width=True)
elif menu == "01 · Minimum Context":
    show_lab_header("01", labs)
    result = api_get("/api/minimum-context")
    left, right = st.columns(2)
    left.write("전체 State Key"); left.json(result["full_keys"])
    right.write("전달할 최소 Context"); right.json(result["selected_context"])
    st.warning(f"제거된 Key: {result['removed_keys']}")
elif menu == "02 · Handoff Envelope":
    show_lab_header("02", labs)
    st.write("책임과 최소 Context뿐 아니라 중복 방지와 추적을 위한 ID가 필요합니다.")
    st.json({
        "handoff_id": "handoff-001", "task_id": "travel-001", "trace_id": "trace-001",
        "from_agent": "weather_agent", "to_agent": "itinerary_agent",
        "responsibility": "날씨를 반영한 일정 작성",
        "context": {"destination": "부산", "days": 3, "weather_summary": "날씨 확인 필요"},
        "context_version": 1, "user_id": "user-101", "hop_count": 1,
        "status": "proposed",
    })
    st.caption("설명용 Handoff Envelope 예시입니다. 실제 실행 결과는 06번 화면에서 확인할 수 있습니다.")
    st.subheader("필드별 의미")
    st.table([
        {"필드": "handoff_id", "의미": "이 책임 이전 요청의 고유 ID. 같은 Handoff를 두 번 처리하지 않도록 검사합니다."},
        {"필드": "task_id", "의미": "어느 사용자 작업에 속한 Handoff인지 나타냅니다."},
        {"필드": "trace_id", "의미": "실행 과정의 Event와 로그를 하나의 흐름으로 연결하는 ID입니다."},
        {"필드": "from_agent", "의미": "현재 책임을 가진 Agent입니다."},
        {"필드": "to_agent", "의미": "책임을 받을 대상 Agent입니다. 자기 자신에게 넘기는 것은 계약이 차단합니다."},
        {"필드": "responsibility", "의미": "대상 Agent가 넘겨받아 수행할 업무입니다."},
        {"필드": "context", "의미": "다음 Agent에게 필요한 최소 정보입니다. Guard가 허용·필수 항목을 확인합니다."},
        {"필드": "context_version", "의미": "전달 정보 형식의 버전입니다. 기본값은 1입니다."},
        {"필드": "user_id", "의미": "요청 소유자입니다. 다른 사용자의 Handoff가 아닌지 검사합니다."},
        {"필드": "hop_count", "의미": "지금까지의 Handoff 횟수입니다. 경로별 최대 횟수를 넘으면 차단합니다."},
        {"필드": "status", "의미": "현재 단계입니다. proposed는 아직 제안만 된 상태로, 책임이 이전되지는 않았습니다."},
    ])
elif menu == "03 · YAML Policy + Guard":
    show_lab_header("03", labs)
    st.write(
        "아래 `handoff_routes`는 한 Agent가 다음 Agent에게 책임과 데이터를 넘길 때 적용할 정책입니다. "
        "YAML은 허용 경로와 전달할 Context 항목을 정의하고, Python Guard가 실제 Handoff를 검사합니다."
    )
    st.table([
        {"YAML 항목": "from_agent → to_agent", "Guard가 확인하는 내용": "이 Agent 사이의 책임 이전이 허용되는 경로인가?"},
        {"YAML 항목": "required_context", "Guard가 확인하는 내용": "다음 Agent에게 꼭 필요한 데이터가 있고 값이 비어 있지 않은가?"},
        {"YAML 항목": "optional_context", "Guard가 확인하는 내용": "추가로 넘길 수 있는 데이터인가? 목록 밖의 항목은 차단합니다."},
        {"YAML 항목": "max_hops", "Guard가 확인하는 내용": "책임 이전 횟수가 경로별 한도를 넘지 않았는가?"},
    ])
    st.caption(
        "예: Weather → Itinerary에서는 destination, days, weather_summary가 필수입니다. "
        "Guard는 사용자 ID·현재 책임자·중복 handoff_id와 민감 정보도 별도로 검사합니다. "
        "여기서 보는 것은 정책 조회이며, 실제 검증은 06·07 실행에서 일어납니다."
    )
    st.json(api_get("/api/registry"))
elif menu == "Agent Registry · YAML":
    st.title(menu)
    st.write("허용 경로와 Context 목록은 YAML, 최종 검증은 Python Guard가 담당합니다.")
    st.json(api_get("/api/registry"))
elif menu == "04 · Ownership Transition":
    show_lab_header("04", labs)
    st.code("proposed → validated → accepted → transferred → completed\n                         └→ rejected / failed")
    st.info("validated만으로 owner_agent를 변경하지 않습니다. 대상 Agent가 유효한 결과를 반환한 뒤 변경합니다.")
elif menu == "05 · Rejection and Failure":
    show_lab_header("05", labs)
    st.dataframe(api_get("/api/guard-cases"), use_container_width=True)
    st.warning("수락 전 실패하면 Weather Agent가 책임을 유지합니다.")
elif menu == "MCP Tool":
    st.title(menu); st.json(api_get("/api/mcp-status"))
elif menu.startswith("06"):
    show_lab_header("06", labs)
    st.subheader("실시간 Handoff Event")
    destination = st.text_input("목적지", "부산")
    days = st.slider("여행 일수", 1, 7, 3)
    transport = st.text_input("이동 수단", "대중교통")
    if st.button("OpenAI → Gemma 실제 Handoff 실행", type="primary", use_container_width=True):
        st.session_state.pop("handoff-result", None)
        try:
            st.session_state["handoff-result"] = run_handoff_sse({"destination": destination, "days": days, "transport": transport, "user_id": "user-101"})
        except requests.RequestException as error:
            st.error(f"실행 오류: {error}")
    if "handoff-result" in st.session_state:
        state = st.session_state["handoff-result"]
        if state["status"] == "completed":
            st.success(f"최종 상태: {state['status']} · 최종 책임자: {state['owner_agent']}")
        else:
            st.error(f"최종 상태: {state['status']} · 최종 책임자: {state['owner_agent']}")
        show_handoff_details(state)
        with st.expander("전체 실행 데이터 보기"):
            st.json(state)
elif menu.startswith("07"):
    show_lab_header("07", labs)
    employee_id = st.text_input("직원 ID", "EMP-101")
    system_name = st.text_input("시스템 이름", "사내 포털")
    issue = st.text_area("문제 내용", "로그인할 수 없습니다.")
    if st.button("IT 접수 → 계정 지원 Handoff 실행", type="primary", use_container_width=True):
        st.session_state.pop("internal-handoff-result", None)
        try:
            st.session_state["internal-handoff-result"] = api_post(
                "/api/runs/internal-handoff",
                {"employee_id": employee_id, "system_name": system_name, "issue": issue},
                read_timeout=300,
            )
        except requests.RequestException as error:
            st.error(f"실행 오류: {error}")
    if "internal-handoff-result" in st.session_state:
        result = st.session_state["internal-handoff-result"]
        if result["status"] == "completed":
            st.success(f"최종 책임자: {result['owner_agent']}")
        else:
            st.warning(f"최종 상태: {result['status']}")
        show_internal_handoff_details(result)
        with st.expander("전체 실행 데이터 보기"):
            st.json(result)

elif menu.startswith("08"):
    show_lab_header("08", labs)
    st.write("라우터가 계정·기기·접근 권한 중 한 Agent를 선택합니다. 아래는 각 경로에서 실제로 적용되는 Context 정책입니다.")
    routes = api_get("/api/routed-handoff/routes")
    st.table([{
        "대상 Agent": route["target_agent"],
        "필수 Context": ", ".join(route["required_context"]),
        "선택 Context": ", ".join(route["optional_context"]),
        "대상 Output Contract": route["output_contract"],
    } for route in routes])
    scenario = st.selectbox("실습 예시", ["계정 로그인", "기기 고장", "접근 권한 요청"])
    examples = {
        "계정 로그인": ("사내 포털", "로그인할 수 없습니다. 계정 잠금 여부를 확인하고 싶습니다."),
        "기기 고장": ("업무 기기", "업무용 노트북이 켜지지 않아 업무를 진행할 수 없습니다."),
        "접근 권한 요청": ("사내 포털", "프로젝트 자료에 접근할 권한이 필요합니다."),
    }
    system_default, issue_default = examples[scenario]
    employee_id = st.text_input("직원 ID", "EMP-101", key="route_employee")
    system_name = st.text_input("시스템 이름", system_default, key=f"route_system_{scenario}")
    issue = st.text_area("요청 내용", issue_default, key=f"route_issue_{scenario}")
    if st.button("라우터 판단과 Handoff 실행", type="primary", use_container_width=True):
        st.session_state.pop("routed-handoff-result", None)
        try:
            st.session_state["routed-handoff-result"] = api_post("/api/runs/routed-handoff", {
                "employee_id": employee_id, "system_name": system_name, "issue": issue,
            }, read_timeout=300)
        except requests.RequestException as error:
            st.error(f"실행 오류: {error}")
    if "routed-handoff-result" in st.session_state:
        result = st.session_state["routed-handoff-result"]
        if result["status"] == "completed":
            st.success(f"최종 상태: completed · 최종 책임자: {result['owner_agent']}")
        else:
            st.warning(f"최종 상태: {result['status']} · 현재 책임자: {result['owner_agent']}")
        show_internal_handoff_details(result, flow_label=f"지원 라우터 → {result.get('owner_agent') if result['status'] == 'completed' else (result.get('decision') or {}).get('target_agent', '대상 Agent')}")
        with st.expander("전체 실행 데이터 보기"):
            st.json(result)

else:
    show_lab_header("09", labs)
    st.info("상담 결과에서 필요한 정보만 Handoff로 전달합니다. 실제 환불금 지급은 실행하지 않습니다.")
    order_id = st.text_input("주문번호", "ORDER-102")
    issue = st.text_area("고객 문의", "주문을 취소하고 환불받고 싶습니다.")
    if st.button("상담 → 환불 Handoff 실행", type="primary", use_container_width=True):
        st.session_state.pop("refund-handoff-result", None)
        try:
            st.session_state["refund-handoff-result"] = api_post(
                "/api/runs/refund-handoff",
                {"user_id": "customer-101", "order_id": order_id, "issue": issue},
                read_timeout=300,
            )
        except requests.RequestException as error:
            st.error(f"실행 오류: {error}")
    if "refund-handoff-result" in st.session_state:
        result = st.session_state["refund-handoff-result"]
        if result["status"] == "completed":
            st.success(f"환불 문의 인수 완료 · 최종 책임자: {result['owner_agent']}")
        else:
            st.error(f"인계 실패 · 현재 책임자: {result['owner_agent']}")
        st.subheader("Contract → Handoff → 환불 Agent 결과")
        for step in result.get("trace", []):
            with st.expander(f"{step['title']} · {step['status']}", expanded=True):
                st.write(step["message"])
                st.caption(f"이 단계의 책임자: {step['owner_agent']}")
                if step.get("data") is not None:
                    st.json(step["data"])
        if result.get("error"):
            st.error(result["error"])
        with st.expander("전체 실행 데이터 보기"):
            st.json(result)
