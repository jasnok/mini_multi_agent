"""04의 실행 계획, 병렬 실행과 결과 합치기를 단계별로 보여 주는 Streamlit 화면입니다."""

import json
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
MESSAGE = "부산 2박 3일, 1명, 대중교통 여행을 계획해 주세요."
EVENT_MESSAGE = "신입 개발자 30명을 위한 2시간 온라인 기술 행사를 준비해 주세요."

LAB_GUIDES = {
    "01": ("Agent를 어떤 순서로 실행할까요?", "backend/app/schemas/contracts.py · ExecutionPlan"),
    "02": ("앞 Agent의 결과를 다음 Agent에게 어떻게 전달할까요?", "backend/app/orchestration/engine.py · sequential()"),
    "03": ("서로 독립적인 Agent를 동시에 실행할 수 있을까요?", "backend/app/orchestration/engine.py · parallel()"),
    "04": ("필요한 결과가 준비되었는지 어떻게 확인할까요?", "backend/app/orchestration/engine.py · join()"),
    "05": ("일부 Agent가 실패해도 계속할 수 있을까요?", "backend/app/orchestration/engine.py · partial_policy()"),
    "06": ("질문에 따라 Handoff 경로가 어떻게 달라질까요?", "backend/app/orchestration/engine.py · handoff()"),
    "07": ("병렬 실행과 Join의 진행 상황을 어떻게 볼까요?", "backend/app/orchestration/engine.py · distributed_tracked()"),
    "08": ("여행이 아닌 업무에도 같은 구조를 사용할 수 있을까요?", "backend/app/orchestration/event_flow.py · event_collaboration()"),
    "09": ("날씨부터 여행 가이드까지 결과를 순서대로 어떻게 전달할까요?", "backend/app/orchestration/langgraph_flow.py · build_travel_graph()"),
    "10": ("날씨 결과를 장소 선택과 예산 계산에 어떻게 연결할까요?", "backend/app/orchestration/weather_place_budget_graph.py · build_weather_place_budget_graph()"),
    "11": ("재고·결제 결과를 확인한 뒤에만 주문 안내를 만들까요?", "backend/app/orchestration/order_flow.py · order_collaboration()"),
}


LAB_API_CALLS = {
    "01": [
        ("GET", "/api/execution-plan", "화면 진입 시 실행 계획 조회 · plan()"),
        ("POST", "/api/plans/validate", "검증 버튼 · JSON: plan · validate_plan()"),
    ],
    "02": [("POST", "/api/runs/sequential", "실행 버튼 · JSON: message · sequential()")],
    "03": [("POST", "/api/runs/parallel", "실행 버튼 · JSON: message · parallel()")],
    "04": [("POST", "/api/runs/join", "실행 버튼 · JSON: message, fail_agent · join()")],
    "05": [("POST", "/api/runs/partial-failure", "실행 버튼 · JSON: message, fail_agent, policy=required_optional · parallel() → partial_policy()")],
    "06": [("POST", "/api/runs/handoff", "실행 버튼 · JSON: message · handoff()")],
    "07": [
        ("POST", "/api/stream-runs/distributed", "실행 버튼 · JSON: message · distributed_tracked() 예약"),
        ("GET", "/api/stream-runs/{run_id}/events", "실행 중 SSE trace 수신"),
        ("GET", "/api/stream-runs/{run_id}/snapshot", "실행 중 진행 상태와 최종 결과 조회"),
    ],
    "08": [("POST", "/api/runs/event-collaboration", "실행 버튼 · JSON: message · event_collaboration()")],
    "09": [("POST", "/api/runs/langgraph", "실행 버튼 · JSON: message · run_langgraph_travel()")],
    "10": [("POST", "/api/runs/weather-place-budget", "실행 버튼 · JSON: message, budget_limit, rain_threshold, rain_probability_override · run_weather_place_budget()")],
    "11": [("POST", "/api/runs/order-confirmation", "모의 재고·결제·쿠폰 병렬 실행 → Python Join Guard → 주문 안내")],
}


def api_get(path: str) -> dict:
    response = requests.get(f"{API}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict, params: dict | None = None) -> dict:
    response = requests.post(f"{API}{path}", json=payload, params=params, timeout=900)
    response.raise_for_status()
    return response.json()


def show_lab_header(lab_id: str, lab: dict) -> None:
    question, code_path = LAB_GUIDES[lab_id]
    st.title(f"{lab_id} · {lab['title']}")
    st.caption("이 화면의 Backend 요청")
    for method, endpoint, action in LAB_API_CALLS[lab_id]:
        st.code(f"{method} {API}{endpoint}", language="text")
        st.caption(action)
    st.info(f"생각할 질문 · {lab['question']}")
    st.success(f"핵심 답변 · {lab['answer_summary']}")
    with st.expander("상세 답변 보기"):
        for detail in lab["answer_details"]:
            st.write(f"- {detail}")
    with st.expander("실행 후 먼저 읽을 코드"):
        st.code(code_path, language="text")


def show_result(result: dict) -> None:
    status = result.get("status", "completed")
    if status == "completed":
        st.success("실행이 완료되었습니다.")
    elif status == "partial_failure":
        st.warning("일부 Agent가 실패했습니다.")
    elif status == "over_budget":
        st.warning("선택한 장소를 포함한 예상 비용이 예산 한도를 넘었습니다.")
    else:
        st.error(f"실행 상태: {status}")
    if result.get("error"):
        st.error(f"오류 원인: {result['error']}")

    summary = {
        "실행 ID": result.get("run_id"),
        "완료된 Agent": result.get("completed_agents", []),
        "실패한 Agent": result.get("failed_agents", []),
        "종료 이유": result.get("reason"),
    }
    st.subheader("실행 요약")
    st.json(summary)

    if result.get("results"):
        st.subheader("Agent 결과")
        st.json(result["results"])
    if result.get("trace"):
        st.subheader("실행 순서")
        simple_trace = [
            {
                "순서": event.get("step"),
                "Agent": event.get("actor"),
                "행동": event.get("action"),
                "상태": event.get("status"),
            }
            for event in result["trace"]
        ]
        st.dataframe(simple_trace, use_container_width=True)
    with st.expander("전체 실행 결과 보기"):
        st.json(result)
    if result.get("run_id"):
        st.session_state["last_run"] = result


def run_button(label: str, path: str, payload: dict, params: dict | None = None) -> None:
    if st.button(label, type="primary", use_container_width=True):
        with st.spinner("실제 Agent와 MCP Tool을 실행하고 있습니다..."):
            try:
                st.session_state[path] = api_post(path, payload, params)
            except requests.RequestException as error:
                st.error(f"API 오류: {error}")
    if path in st.session_state:
        show_result(st.session_state[path])


def run_sse_workflow(message: str) -> dict:
    """실시간 Event를 화면에 표시하고 마지막 Snapshot을 반환합니다."""
    created = api_post("/api/stream-runs/distributed", {"message": message})
    run_id = created["run_id"]
    st.caption(f"실행 ID: {run_id}")
    progress = st.progress(0)
    status_area = st.empty()
    event_area = st.empty()
    events = []

    with requests.get(
        f"{API}/api/stream-runs/{run_id}/events",
        headers={"Accept": "text/event-stream"},
        stream=True,
        timeout=(10, 900),
    ) as response:
        response.raise_for_status()
        event_name = "message"
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or raw_line.startswith(":"):
                continue
            if raw_line.startswith("event:"):
                event_name = raw_line.removeprefix("event:").strip()
                continue
            if not raw_line.startswith("data:"):
                continue
            payload = json.loads(raw_line.removeprefix("data:").strip())
            if event_name == "trace":
                events.append(payload)
                event_area.dataframe(events, use_container_width=True)
                snapshot = api_get(f"/api/stream-runs/{run_id}/snapshot")
                progress.progress(snapshot["progress_percent"])
                status_area.info(snapshot["message"])
            elif event_name == "finished":
                progress.progress(payload["progress_percent"])
                return payload
    return api_get(f"/api/stream-runs/{run_id}/snapshot")


st.set_page_config(page_title="Mini Multi-Agent 04", page_icon="🤝", layout="wide")
st.sidebar.title("🤝 Mini Multi-Agent 04")
MENUS = [
    "과정 안내", "실행 환경 점검", "01 · Execution Plan", "02 · Sequential Workflow",
    "03 · Parallel Workers", "04 · Join Results", "05 · Partial Failure",
    "06 · Handoff Workflow", "07 · Distributed Workflow",
    "08 · 다른 업무에 Parallel + Join 적용", "09 · LangGraph 여행 Workflow",
    "10 · 날씨에 따른 장소와 예산",
    "11 · 온라인 주문 Join Guard",
    "Agent Registry · YAML",
    "Shared State", "Trace Explorer", "MCP Tool", "Provider 상태",
]
menu = st.sidebar.radio("학습 메뉴", MENUS)

try:
    labs = api_get("/api/labs")
except requests.RequestException as error:
    st.error(f"Backend 연결 실패: {error}")
    st.stop()

if menu == "과정 안내":
    st.title("여러 Agent를 계획대로 실행하고 결과 합치기")
    st.write("01에서 실행 Pattern을 보고, 02에서 계약을 만들고, 03에서 Agent를 선택했습니다. 04에서는 여러 Agent를 순서대로 또는 동시에 실행하고 결과를 하나로 합칩니다.")
    st.info("Execution Plan은 실행 순서, Shared State는 현재 결과, Join은 여러 결과를 합치는 단계입니다.")
    for lab_id, lab in labs.items():
        with st.expander(f"{lab_id} · {lab['title']} — {lab['question']}"):
            st.success(lab["answer_summary"])
            for detail in lab["answer_details"]:
                st.write(f"- {detail}")
            st.caption(f"예상 LLM 호출: {lab['expected_calls']}")
elif menu in {"실행 환경 점검", "Provider 상태"}:
    st.title(menu)
    providers = api_get("/api/providers")
    st.dataframe([{"provider": name, **value} for name, value in providers.items()], use_container_width=True)
elif menu == "MCP Tool":
    st.title("MCP Tool")
    st.json(api_get("/api/mcp-status"))
elif menu == "Agent Registry · YAML":
    st.title("Agent Registry · YAML 설정은 어디에서 쓰일까요?")
    st.code(f"GET {API}/api/registry", language="text")
    st.write(
        "`workers.yaml`은 Worker의 이름·목표·지시문·Provider·허용 Tool을 정의합니다. "
        "`teams.yaml`은 병렬 Worker, 필수·선택 Worker, 결과 통합 Agent를 정의합니다. "
        "Backend 시작 시 두 파일을 Registry로 읽고 Team 참조를 검사합니다."
    )
    st.table([
        {"화면": "01", "사용": "실행 계획 예시", "설명": "Agent ID를 계획에 적지만 Registry를 조회해 실행하지는 않습니다."},
        {"화면": "02~06", "사용": "workers.yaml", "설명": "각 Agent 호출 시 Registry의 Provider·지시문·허용 Tool을 사용합니다. 실행 순서와 실패 정책은 Python 코드에 있습니다."},
        {"화면": "07", "사용": "workers.yaml + teams.yaml", "설명": "travel_collaboration_team에서 병렬 Worker·필수 Worker·통합 Agent를 읽습니다."},
        {"화면": "08", "사용": "workers.yaml + teams.yaml", "설명": "event_collaboration_team 설정으로 온라인 행사 Worker를 실행합니다."},
        {"화면": "09", "사용": "workers.yaml + teams.yaml", "설명": "travel_collaboration_team을 LangGraph 노드 구성에 사용합니다."},
        {"화면": "10", "사용": "workers.yaml", "설명": "Weather·Place·Budget Agent 설정을 사용하며 조건 분기는 LangGraph 코드에 있습니다."},
    ])
    st.caption(
        "Coordinator와 Itinerary Agent는 Python 파일에 정의됩니다. "
        "YAML은 Agent 자체를 실행하지 않으며, 실제 호출과 Guard는 Orchestration 코드가 담당합니다."
    )
    st.subheader("현재 Backend에 등록된 Agent와 Team")
    st.json(api_get("/api/registry"))
elif menu == "Shared State":
    st.title("Shared State · 마지막 실행 결과")
    st.caption("현재 화면 세션에서 마지막으로 실행한 Workflow의 전체 결과를 보여줍니다. 새 실행을 하면 이 값이 바뀝니다.")
    result = st.session_state.get("last_run")
    st.json(result or {"안내": "먼저 Workflow를 실행하세요."})
elif menu == "Trace Explorer":
    st.title("Trace Explorer · 마지막 실행의 Agent 순서")
    st.caption("현재 화면 세션에서 마지막으로 실행한 Workflow의 trace만 보여줍니다. 새 실행을 하면 표시할 순서도 바뀝니다.")
    result = st.session_state.get("last_run", {})
    events = result.get("trace", [])
    actors = sorted({event["actor"] for event in events})
    selected = st.multiselect("확인할 Agent", actors, default=actors)
    st.dataframe([event for event in events if event["actor"] in selected], use_container_width=True)
elif menu.startswith("01"):
    show_lab_header("01", labs["01"])
    execution_plan = api_get("/api/execution-plan")
    st.json(execution_plan)
    edited = st.text_area("검증할 Plan JSON", json.dumps(execution_plan, ensure_ascii=False, indent=2), height=300)
    if st.button("계획 검증", type="primary"):
        try:
            st.json(api_post("/api/plans/validate", {"plan": json.loads(edited)}))
        except json.JSONDecodeError as error:
            st.error(str(error))
elif menu.startswith("02"):
    show_lab_header("02", labs["02"])
    st.code('START → Research Agent → Writer Agent → Reviewer Agent → END', language="text")
    message = st.text_area("요청", MESSAGE, key="seq")
    run_button("Research → Writer → Reviewer 실행", "/api/runs/sequential", {"message": message})
elif menu.startswith("03"):
    show_lab_header("03", labs["03"])
    st.code('START ─┬→ Weather Agent ─┐\n       ├→ Place Agent ───┼→ 개별 결과 표시 → END\n       └→ Budget Agent ──┘', language="text")
    message = st.text_area("요청", MESSAGE, key="parallel")
    run_button("Weather·Place·Budget 동시 실행", "/api/runs/parallel", {"message": message})
elif menu.startswith("04"):
    show_lab_header("04", labs["04"])
    st.code('START ─┬→ Weather(필수) ─┐\n       ├→ Place(선택) ───┼→ 필수 결과 확인 ─┬→ Itinerary → END\n       └→ Budget(필수) ──┘                 └→ 누락 시 END', language="text")
    message = st.text_area("요청", MESSAGE, key="join")
    missing = st.selectbox("교육용으로 실패시킬 Agent", ["없음", "place_agent", "weather_agent", "budget_agent"])
    st.caption("Place는 선택 결과이고 Weather와 Budget은 필수 결과입니다.")
    run_button("병렬 실행 후 결과 합치기", "/api/runs/join", {"message": message, "fail_agent": None if missing == "없음" else missing})
elif menu.startswith("05"):
    show_lab_header("05", labs["05"])
    st.code('Weather(필수) · Place(선택) · Budget(필수) 병렬 실행\n                  ↓\n       required_optional 정책 확인\n          ├→ 필수 결과 모두 있음 → 계속\n          └→ 필수 결과 누락     → 중단', language="text")
    failure = st.radio("비교할 실패", ["선택 Agent(place) 실패", "필수 Agent(weather) 실패"])
    fail_agent = "place_agent" if failure.startswith("선택") else "weather_agent"
    run_button("필수·선택 결과 정책 확인", "/api/runs/partial-failure", {"message": MESSAGE, "fail_agent": fail_agent, "policy": "required_optional"})
    with st.expander("추가로 세 가지 실패 정책 비교"):
        st.write("fail_fast: 하나라도 실패하면 중단")
        st.write("best_effort: 성공 결과가 하나라도 있으면 진행")
        st.write("required_optional: 필수 결과가 있으면 진행")
elif menu.startswith("06"):
    show_lab_header("06", labs["06"])
    st.code('고객 문의 → Support Agent의 질문 분류\n             ├→ 환불 문의 → Handoff → Refund Agent\n             ├→ 배송 문의 → Handoff → Delivery Agent\n             └→ 일반 문의 → Support Agent 직접 답변', language="text")
    st.caption("질문에 따라 환불 인계·배송 인계·상담 Agent 직접 답변으로 갈라집니다.")
    example = st.selectbox("비교할 질문", ["환불 문의", "배송 문의", "일반 문의"])
    if st.session_state.get("last_handoff_example") != example:
        st.session_state.pop("dynamic_handoff_result", None)
        st.session_state["last_handoff_example"] = example
    examples = {
        "환불 문의": "ORDER-102 주문의 환불 조건을 알고 싶습니다.",
        "배송 문의": "ORDER-102 주문이 아직 도착하지 않았습니다. 배송 확인 방법을 알려주세요.",
        "일반 문의": "고객센터 운영시간은 어디서 확인하나요?",
    }
    message = st.text_area("고객 문의", examples[example], key=f"handoff_question_{example}")
    if st.button("질문에 따른 Handoff 실행", type="primary", use_container_width=True):
        st.session_state.pop("dynamic_handoff_result", None)
        with st.spinner("상담 Agent가 질문을 분류하고 있습니다..."):
            try:
                st.session_state["dynamic_handoff_result"] = api_post("/api/runs/handoff", {"message": message})
            except requests.RequestException as error:
                st.error(f"API 오류: {error}")
    if "dynamic_handoff_result" in st.session_state:
        result = st.session_state["dynamic_handoff_result"]
        route = result.get("selected_route", "분류 실패")
        st.write(f"**선택된 경로:** {route}")
        st.write(f"**현재 책임자:** {result.get('owner_agent', 'support_agent')}")
        if result.get("status") == "completed":
            st.success("실행이 완료되었습니다.")
        else:
            st.error(f"실행 상태: {result.get('status')}")
        if result.get("error"):
            st.error(result["error"])
        if result.get("decision"):
            with st.expander("1 · 상담 Agent의 판단", expanded=True):
                st.json(result["decision"])
        if result.get("handoff"):
            with st.expander("2 · 생성된 Handoff와 전달 Context", expanded=True):
                st.json(result["handoff"])
        if result.get("answer"):
            st.subheader("상담 Agent의 직접 답변")
            st.write(result["answer"])
        if result.get("target_result"):
            st.subheader("대상 Agent 결과")
            st.json(result["target_result"])
        with st.expander("전체 실행 결과 보기"):
            st.json(result)
elif menu.startswith("07"):
    show_lab_header("07", labs["07"])
    st.code('START ─┬→ Weather(필수) ─┐\n       ├→ Place(선택) ───┼→ 필수 결과 확인 → Itinerary → END\n       └→ Budget(필수) ──┘         └→ 누락 시 END\n       각 단계 완료·실패 Event → 실시간 화면', language="text")
    st.caption("실시간 화면은 내부적으로 Redis Event와 SSE를 사용하지만, 먼저 Agent 완료 순서와 Join 결과만 확인합니다.")
    message = st.text_area("요청", MESSAGE, key="distributed")
    if st.button("네 LLM 전체 Workflow 실시간 실행", type="primary", use_container_width=True):
        try:
            state = run_sse_workflow(message)
            st.session_state["sse-result"] = state
            if state.get("result"):
                st.session_state["last_run"] = state["result"]
        except requests.RequestException as error:
            st.error(f"SSE 또는 Snapshot API 오류: {error}")
    if "sse-result" in st.session_state:
        st.subheader("최종 실행 상태")
        st.json(st.session_state["sse-result"])
elif menu.startswith("08"):
    show_lab_header("08", labs["08"])
    st.code('START ─┬→ 행사 콘텐츠(필수) ─┐\n       ├→ 행사 운영(필수) ───┼→ 필수 결과 확인 → 행사안 통합 → END\n       └→ 행사 홍보(선택) ───┘         └→ 누락 시 END', language="text")
    st.caption("콘텐츠·홍보·운영을 동시에 실행한 뒤 Gemma 3 1B가 하나의 행사안으로 합칩니다.")
    message = st.text_area("온라인 행사 요청", EVENT_MESSAGE, key="event-collaboration")
    run_button("온라인 행사 Parallel + Join 실행", "/api/runs/event-collaboration", {"message": message})
elif menu.startswith("09"):
    show_lab_header("09", labs["09"])
    st.code("START → Weather → Place → Lodging → Budget → Guide → END\n          각 단계 실패 → END", language="text")
    st.caption("앞 Agent의 검증된 결과를 다음 Agent의 Context로 전달합니다. 어느 단계든 실패하면 뒤 단계는 실행하지 않습니다.")
    message = st.text_area("요청", MESSAGE, key="langgraph-travel")
    run_button("LangGraph 여행 Workflow 실행", "/api/runs/langgraph", {"message": message})
elif menu.startswith("10"):
    show_lab_header("10", labs["10"])
    st.code(
        "START → 실제 날씨 Agent 또는 입력 강수확률 → weather_guard\n"
        "                         ├─ rain → indoor_place ──┐\n"
        "                         ├─ dry  → outdoor_place ─┼→ budget_agent → END\n"
        "                         └─ error → END          │\n"
        "                       장소 조회 실패 → END ←──────┘",
        language="text",
    )
    with st.expander("LangGraph가 이 화면에서 하는 일", expanded=True):
        st.markdown(
            "**State**는 여행 요청, 날씨 Tool 결과, 선택 장소, 예산 계산 결과를 "
            "다음 단계에 전달하는 공유 데이터입니다. 각 Node는 필요한 값을 읽고 새 결과를 State에 기록합니다."
        )
        st.markdown(
            "- **날씨 입력 → weather_guard:** 실제 날씨 모드에서는 Open-Meteo의 향후 3일 강수확률 중 최대값을 사용합니다. "
            "교육용 입력 모드에서는 화면에서 지정한 값을 사용하며, 출처를 `user_input`으로 표시합니다.\n"
            "- **조건 Edge:** 기준 이상이면 `indoor_place`, 미만이면 `outdoor_place`로 이동합니다. "
            "날씨를 확인할 수 없으면 종료합니다.\n"
            "- **장소 Node → budget_agent:** DB에서 해당 실내·실외 후보를 고른 뒤 "
            "도시별 여행 기준액에 장소의 1인 예상 비용 × 인원을 더합니다."
        )
        st.caption(
            "09번은 정해진 순서로 누적 Context를 전달합니다. 10번은 날씨 결과에 따라 "
            "다음 Node가 달라지는 조건 분기를 보여줍니다. 분기와 금액 계산은 Python 코드가 판정합니다."
        )
    message = st.text_area("여행 요청", MESSAGE, key="weather-place-budget")
    budget_limit = st.number_input("총예산 한도 (원)", min_value=0, value=650_000, step=10_000)
    rain_threshold = st.slider("실내 장소로 전환할 강수확률 (%)", min_value=0, max_value=100, value=50)
    weather_mode = st.radio("날씨 입력 방식", ["실제 날씨 Tool", "교육용 강수확률 직접 입력"], horizontal=True)
    override = None
    if weather_mode == "교육용 강수확률 직접 입력":
        override = st.slider("입력할 강수확률 (%)", min_value=0, max_value=100, value=70)
        st.caption("이 값은 실제 예보가 아닙니다. LangGraph의 실내·실외 분기를 확인하기 위한 입력입니다.")
    path = "/api/runs/weather-place-budget"
    run_button("날씨 → 장소 → 예산 실행", path, {
        "message": message, "budget_limit": budget_limit, "rain_threshold": rain_threshold,
        "rain_probability_override": override,
    })
    if path in st.session_state:
        result = st.session_state[path]
        st.subheader("날씨에 따른 선택")
        probability = result.get("precipitation_probability")
        if probability is not None:
            route = "실내" if result.get("weather_risk") == "rain" else "실외"
            st.info(f"강수확률 최대 {probability}% / 실행 기준 {result.get('rain_threshold')}% → {route} 장소 경로")
        st.caption("실제로 실행된 Node는 위 실행 순서(trace)의 actor 열에서 확인할 수 있습니다.")
        st.json({
            "날씨 출처": result.get("weather_source"),
            "최대 강수확률": result.get("precipitation_probability"),
            "날씨 경로": result.get("weather_risk"),
            "선택 장소": result.get("selected_place"),
            "예산 계산": result.get("budget"),
        })

elif menu.startswith("11"):
    show_lab_header("11", labs["11"])
    st.info("교육용 모의 확인입니다. 실제 재고 확보·결제·주문 확정은 실행하지 않습니다.")
    st.code("""재고 확인(필수) ─┐
결제 확인(필수) ─┼→ Python Join Guard → 주문 안내
쿠폰 안내(선택) ─┘""", language="text")
    message = st.text_area("모의 주문 요청", "ORDER-102 상품 1개 주문 확인을 도와주세요.", key="order-confirmation")
    failure = st.selectbox("비교할 결과", ["모두 성공", "재고 확인 실패", "결제 확인 실패", "쿠폰 안내 실패"])
    fail_agent = {
        "모두 성공": None,
        "재고 확인 실패": "inventory_check_agent",
        "결제 확인 실패": "payment_check_agent",
        "쿠폰 안내 실패": "coupon_guide_agent",
    }[failure]
    path = "/api/runs/order-confirmation"
    run_button("Join Guard 실행", path, {"message": message, "fail_agent": fail_agent})
    if path in st.session_state:
        result = st.session_state[path]
        guard = result.get("join_guard", {})
        if guard.get("passed"):
            st.success("Join Guard 통과: 재고와 결제 결과가 모두 있습니다.")
        else:
            st.error(f"Join Guard 차단: 필수 결과 누락 {guard.get('missing_required', [])}")
        if guard.get("optional_failed"):
            st.info(f"선택 결과 누락은 허용: {guard['optional_failed']}")
