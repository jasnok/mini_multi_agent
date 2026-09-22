"""01 Single vs Multi Agent 강의를 좌측 메뉴로 진행하는 Streamlit 화면입니다."""

import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_PROVIDER_BY_ACTOR = {
    "travel_agent": "openai", "weather_agent": "gemini", "place_agent": "ollama",
    "budget_agent": "openai", "safety_agent": "gemma", "itinerary_agent": "gemma",
    "research_agent": "gemini", "writer_agent": "openai", "reviewer_agent": "gemma",
    "router": "openai", "delivery_agent": "gemini", "refund_policy_agent": "gemma",
    "technical_support_agent": "ollama", "supervisor": "openai", "analyst_agent": "gemini",
    "developer_agent": "ollama", "support_agent": "gemini", "evaluator_agent": "gemini",
    "reviser_agent": "openai",
}
PATTERN_ACTORS = {
    "single_agent": ["travel_agent"],
    "independent": ["weather_agent", "place_agent", "budget_agent", "safety_agent"],
    "orchestration_comparison": ["weather_agent", "budget_agent"],
    "sequential": ["research_agent", "writer_agent", "reviewer_agent"],
    "parallel_join": ["weather_agent", "place_agent", "budget_agent", "itinerary_agent"],
    "router": ["router", "delivery_agent", "refund_policy_agent", "technical_support_agent"],
    "supervisor_worker": ["supervisor", "analyst_agent", "developer_agent", "reviewer_agent"],
    "handoff": ["support_agent", "refund_policy_agent"],
    "evaluator_reviser": ["writer_agent", "evaluator_agent", "reviser_agent"],
    "provider_failover": ["writer_agent"],
}

LAB_REQUEST_EXAMPLES = {
    "01": ["부산 2박 3일 여행을 계획해 줘. 알레르기와 대중교통, 예산 60만원을 반영해 줘.", "부산 1박 2일 여행 초안을 만들어 줘. 비 예보와 실내 장소를 고려하고 예산은 40만원이야.", "부산 3박 4일 여행을 계획해 줘. 2명이 대중교통으로 이동하고 총예산은 100만원이야."],
    "02": ["부산 2박 3일 여행의 날씨, 장소, 알레르기 주의사항과 예산 60만원을 각각 조사해 줘.", "부산 1박 2일 여행의 장소와 대중교통, 예산 40만원을 역할별로 확인해 줘.", "부산 2박 3일 여행에서 날씨·안전 Agent의 결과와 예산 60만원 계산을 보여 줘."],
    "03": ["여행 계획 업무를 날씨·장소·예산·안전 Agent로 분리해야 하는지 판단해 줘.", "배송 조회와 환불 정책 안내를 하나의 Agent가 처리해도 되는지 판단해 줘.", "콘텐츠 조사·작성·검토 책임을 분리할 근거를 확인해 줘."],
    "04": ["여행 전문 Agent 4개를 사용할 때 Single Agent 대비 호출 비용과 실패 지점을 비교해 줘.", "분석·개발·검토 Agent 3개를 분리했을 때 추가 실행 비용을 계산해 줘.", "전문 Agent 2개와 통합 Agent를 사용할 때 아키텍처 비용을 비교해 줘."],
    "05": ["날씨 Agent에게 필요한 Context와 허용 Tool만 전달됐는지 확인해 줘.", "환불 정책 Agent가 주문번호 외의 민감정보를 받지 않는지 점검해 줘.", "장소 Agent와 예산 Agent의 Tool 권한이 분리되어 있는지 보여 줘."],
    "06": ["부산 2박 3일 여행에서 날씨와 예산 60만원의 독립 실행과 조정 실행을 비교해 줘.", "부산 1박 2일 여행의 날씨와 예산 40만원으로 Orchestration 차이를 보여 줘.", "부산 2박 3일, 예산 60만원 요청을 독립 Agent와 Orchestrator로 각각 처리해 줘."],
    "07": ["부산 안내문을 조사하고 작성한 뒤 출처 확인과 사용자 승인 문구를 검토해 줘.", "부산 대중교통 안내문을 사실 조사 → 작성 → 검토 순서로 만들어 줘.", "PostgreSQL의 사실만 사용해 부산 관광 소개문을 작성하고 필수 문구를 검토해 줘."],
    "08": ["부산 2박 3일 여행의 날씨·장소·교통과 예산 60만원을 병렬 조사해 하나의 일정으로 합쳐 줘.", "부산 1박 2일 여행 정보를 병렬 조회하고 예산 40만원 일정으로 Join해 줘.", "부산 2박 3일, 예산 60만원의 전문 Agent 데이터가 모인 뒤 최종 일정을 작성해 줘."],
    "09": ["ORDER-102의 현재 배송 상태를 알려 줘.", "배송 지연 주문에 적용되는 환불 정책을 알려 줘.", "로그인이 되지 않을 때 확인할 기술지원 문서를 찾아 줘."],
    "10": ["사용자 입력 검증 기능을 분석하고 구현 방법을 작성한 뒤 완료 조건을 검토해 줘.", "API 요청 검증의 요구사항, 오류 계약, 테스트 항목을 순서대로 정리해 줘.", "입력 검증을 위한 분석·개발·검토 Worker 실행 과정을 보여 줘."],
    "11": ["ORDER-102 배송이 늦습니다. 상태를 확인하고 환불 정책 Agent에게 넘겨 줘.", "ORDER-101의 배송 상태를 확인하고 필요하면 환불 Agent에게 전달해 줘.", "배송 지연 주문의 상태와 Handoff에 필요한 최소 Context를 보여 줘."],
    "12": ["부산 안내문을 작성하고 출처 확인과 사용자 승인 조건을 통과할 때까지 평가·수정해 줘.", "PostgreSQL의 부산 사실만 사용해 안내문을 만들고 누락된 필수 문구를 수정해 줘.", "부산 콘텐츠 초안을 독립 평가하고 최대 반복 횟수 안에서 개선해 줘."],
    "13": ["부산 안내문을 작성하되 Primary LLM이 실패하면 Secondary LLM으로 복구해 줘.", "PostgreSQL의 부산 사실로 콘텐츠를 만들고 Provider Failover 과정을 기록해 줘.", "필수 문구가 포함된 부산 안내문을 Failover 방식으로 작성해 줘."],
}

LAB_BACKEND_ENDPOINTS = {
    "01": ("POST", "/api/runs", "single_agent 실행"),
    "02": ("POST", "/api/runs", "independent 실행"),
    "03": (None, None, "Frontend 내부 체크 항목으로 판단하므로 실행 API 호출 없음"),
    "04": (None, None, "Frontend 내부에서 호출 수와 실패 지점을 계산하므로 실행 API 호출 없음"),
    "05": ("GET", "/api/agents", "Backend Agent Registry의 실제 Tool 권한 조회"),
    "06": ("POST", "/api/runs", "orchestration_comparison 실행"),
    "07": ("POST", "/api/runs", "sequential 실행"),
    "08": ("POST", "/api/runs", "parallel_join 실행"),
    "09": ("POST", "/api/runs", "router 실행"),
    "10": ("POST", "/api/runs", "supervisor_worker 실행"),
    "11": ("POST", "/api/runs", "handoff 실행"),
    "12": ("POST", "/api/runs", "evaluator_reviser 실행"),
    "13": ("POST", "/api/runs", "provider_failover 실행"),
}

LAB_SCREEN_DESCRIPTIONS = {
    "01": "하나의 Travel Agent가 날씨·장소·대중교통·알레르기·예산을 모두 처리합니다. Open-Meteo와 PostgreSQL Tool 결과가 한 Agent에 집중될 때의 장점과 역할 과부하를 확인합니다. Trace에서 5개 Tool의 실제 source와 최종 답변의 근거를 비교하세요.",
    "02": "Weather·Place·Budget·Safety Agent가 같은 여행 요청을 각자 독립적으로 처리합니다. 여러 Agent가 실행되더라도 결과를 합치는 Orchestrator가 없으면 하나의 완성된 일정이 되지 않는다는 점을 확인합니다. Agent별 Tool 권한과 분리된 결과를 비교하세요.",
    "03": "업무를 여러 Agent로 분리할 근거가 충분한지 판단하는 개념 실습입니다. 독립 Goal, Context·Tool 격리, 평가 기준, 병렬 실행·Handoff 필요 여부를 선택합니다. 두 가지 이상의 분리 근거가 있을 때 Multi-Agent 후보로 판단합니다.",
    "04": "Agent 분리에 따라 증가하는 LLM 호출 수와 실패 지점을 계산하는 개념 실습입니다. Specialist 수를 변경하면서 Single Agent와 Supervisor·Specialist·Join 구조의 비용 차이를 확인합니다. 역할 분리의 이점이 운영 복잡도보다 큰지 판단하는 화면입니다.",
    "05": "Backend Agent Registry에 실제 등록된 Agent의 Context 범위와 MCP Tool 권한을 확인합니다. Agent에게 업무 수행에 필요한 정보와 Tool만 제공하고 결제 토큰이나 전체 대화 같은 불필요한 정보는 전달하지 않는 최소 권한 원칙을 학습합니다.",
    "06": "동일한 Weather·Budget Agent를 독립 실행한 경우와 Orchestrator가 선택·수집·종료를 관리한 경우를 비교합니다. Agent 수가 같아도 조정 상태와 종료 책임의 유무에 따라 실행 구조가 달라지는 것을 Trace로 확인합니다.",
    "07": "Research → Writer → Reviewer 순서로 앞 Agent의 결과를 다음 Agent에 전달합니다. PostgreSQL의 출처 있는 부산 사실로 초안을 작성하고 콘텐츠 완료 조건을 검토합니다. 각 단계의 출력 계약이 다음 단계 품질에 어떤 영향을 주는지 확인하세요.",
    "08": "Weather·Place·Budget Agent를 병렬 실행한 뒤 Itinerary Agent가 결과를 하나의 일정으로 Join합니다. 서로 독립적인 조회만 병렬로 실행하고 모든 결과가 준비된 뒤 통합하는 구조입니다. 실제 데이터의 누락이나 충돌이 최종 일정에 숨겨지지 않는지 확인하세요.",
    "09": "Router가 요청 내용을 배송·환불·기술지원 중 하나로 분류하고 해당 전문 Agent 하나만 실행합니다. PostgreSQL 주문 상태, 환불 정책, 도움말 중 요청에 필요한 Tool만 호출되는지 확인합니다. Router의 선택 이유와 실제 Worker가 일치하는지도 Trace에서 검토하세요.",
    "10": "Supervisor가 Analyst → Developer → Reviewer 순서로 미완료 Worker를 선택합니다. PostgreSQL에 저장된 코드 품질 완료 조건을 기준으로 분석·구현안·검토 결과를 단계적으로 만듭니다. 완료 Worker의 중복 실행을 차단하고 제한된 단계 안에서 종료하는 과정을 확인합니다.",
    "11": "Support Agent가 주문 상태를 확인한 뒤 환불 정책 Agent에게 업무 책임과 최소 Context를 넘깁니다. 단순히 다음 Agent를 호출하는 것이 아니라 담당 책임, 주문번호, 현재 상태를 명시적으로 이전하는 Handoff를 보여 줍니다. PostgreSQL 주문·정책 데이터가 양쪽 Agent에 어떻게 사용되는지 확인하세요.",
    "12": "Writer가 PostgreSQL 사실과 완료 조건으로 초안을 만들고 Evaluator가 독립적으로 평가합니다. 기준을 통과하지 못하면 Reviser가 피드백 범위만 수정하며 최대 반복 횟수 안에서 종료합니다. 평가 회차, 누락 조건, 최종 종료 이유를 Trace에서 확인하세요.",
    "13": "Primary Provider 실행이 실패했을 때 실패 기록을 숨기지 않고 Secondary Provider를 실제 호출합니다. PostgreSQL의 동일한 콘텐츠 사실을 사용하면서 Provider만 전환됩니다. 실패 원인, Provider별 Model, Failover 사용 여부와 최종 종료 이유를 확인하세요.",
}

st.set_page_config(page_title="Mini Multi-Agent 01", page_icon="🧭", layout="wide")


def api_get(path: str):
    response = requests.get(f"{API}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API}{path}", json=payload, timeout=900)
    response.raise_for_status()
    return response.json()


def show_result(result: dict) -> None:
    status = result["status"]
    (st.success if status == "completed" else st.error)(f"실행 상태: {status} · 종료 이유: {result['termination_reason']}")
    if result.get("summary"):
        st.subheader("최종 요약")
        st.write(result["summary"])
    if result.get("error"):
        st.code(result["error"])
    st.subheader("Agent 결과")
    st.json(result["outputs"])
    st.subheader("실행 Trace")
    for event in result["trace"]:
        with st.expander(f"{event['step']}. {event['actor']} · {event['action']} · {event['status']}"):
            st.json(event)


def show_concept_lab(lab_id: str, agents: dict) -> None:
    if lab_id == "03":
        st.write("Agent 분리 근거를 선택하세요. 두 가지 이상이면 Multi-Agent 후보로 봅니다.")
        checks = [
            st.checkbox("독립적인 전문 Goal이 있다."),
            st.checkbox("Context 또는 Tool 권한을 격리해야 한다."),
            st.checkbox("Agent별 평가 기준이 다르다."),
            st.checkbox("병렬 실행 또는 Handoff가 필요하다."),
        ]
        reasons = sum(checks)
        st.metric("분리 근거", reasons)
        st.info("Multi-Agent 후보" if reasons >= 2 else "Single Agent로 시작")
    elif lab_id == "04":
        count = st.slider("Specialist Agent 수", 1, 8, 3)
        single_calls, multi_calls = 1, count + 2
        cols = st.columns(3)
        cols[0].metric("Single 호출", single_calls)
        cols[1].metric("Multi 호출", multi_calls, delta=multi_calls - single_calls)
        cols[2].metric("독립 실패 지점", multi_calls)
        st.write("Supervisor 1회 + Specialist N회 + Join 1회의 단순 추정입니다.")
    else:
        context = {
            "weather_agent": (["destination", "days", "weather_question"], ["get_weather"]),
            "budget_agent": (["destination", "days", "budget"], ["calculate_budget"]),
            "place_agent": (["destination", "days", "food_restriction"], ["search_places"]),
            "refund_policy_agent": (["order_id", "approval_id"], ["get_refund_policy"]),
        }
        agent_id = st.selectbox("Agent", list(context))
        allowed_context, _ = context[agent_id]
        allowed_tools = agents[agent_id]["allowed_tools"]
        st.subheader("전달 Context")
        st.write(allowed_context)
        st.subheader("허용 MCP Tool")
        st.write(allowed_tools)
        st.warning("payment_token, 전체 대화 원문, 다른 사용자 주문은 전달하지 않습니다.")


def show_lab(lab_id: str, lab: dict, providers: dict, scenarios: dict, patterns: dict, agents: dict) -> None:
    st.title(f"Lab {lab_id} · {lab['title']}")
    method, path, endpoint_description = LAB_BACKEND_ENDPOINTS[lab_id]
    if method and path:
        st.code(f"{method} {API}{path}", language="http")
        st.caption(f"Backend 호출: {endpoint_description}")
    else:
        st.code("Backend 실행 API 호출 없음", language="text")
        st.caption(endpoint_description)
    st.markdown("**이 화면에서 확인할 내용**")
    st.write(LAB_SCREEN_DESCRIPTIONS[lab_id])
    st.info(lab["question"])
    cols = st.columns(3)
    cols[0].metric("실제 LLM", "사용" if lab["real_llm"] else "미사용")
    cols[1].metric("예상 호출", lab["expected_calls"])
    cols[2].metric("Scenario", lab["scenario"])
    examples = LAB_REQUEST_EXAMPLES[lab_id]
    selected_example = st.selectbox(
        "사용자 요청 예시",
        examples,
        key=f"request-example-{lab_id}",
        help="예시를 선택한 뒤 실행 요청을 필요에 맞게 수정할 수 있습니다.",
    )
    if not lab["real_llm"]:
        st.caption(f"선택한 실습 사례: {selected_example}")
        show_concept_lab(lab_id, agents)
        return

    pattern = lab["pattern"]
    st.write(patterns[pattern])
    scenario = lab["scenario"] if lab["scenario"] in scenarios else "travel"
    selected_index = examples.index(selected_example)
    message = st.text_area(
        "사용자 요청",
        selected_example,
        height=110,
        key=f"message-{lab_id}-{selected_index}",
        help="선택된 예시를 그대로 실행하거나 문장을 직접 수정하세요.",
    )
    payload = {"scenario": scenario, "pattern": pattern, "provider_mode": "mixed", "provider": "openai", "message": message, "max_steps": 5, "provider_by_agent": {}}

    if pattern == "single_agent":
        payload["provider_mode"] = "single"
        payload["provider"] = st.selectbox("Travel Agent LLM", list(providers), key="single-provider")
    elif pattern == "provider_failover":
        payload["primary_provider"] = st.selectbox("Primary LLM", list(providers), index=list(providers).index("gemma"))
        payload["secondary_provider"] = st.selectbox("Secondary LLM", list(providers), index=list(providers).index("openai"))
        payload["simulate_primary_failure"] = st.checkbox("교육용 Primary 실패 시뮬레이션")
    else:
        with st.expander("Agent별 실제 LLM 배정", expanded=True):
            for actor in PATTERN_ACTORS[pattern]:
                default = DEFAULT_PROVIDER_BY_ACTOR.get(actor, "openai")
                payload["provider_by_agent"][actor] = st.selectbox(actor, list(providers), index=list(providers).index(default), key=f"{lab_id}-{actor}")

    if st.button("실제 LLM으로 실행", type="primary", key=f"run-{lab_id}", use_container_width=True):
        with st.spinner("실제 Agent와 MCP Tool을 실행하고 있습니다..."):
            try:
                st.session_state[f"result-{lab_id}"] = api_post("/api/runs", payload)
            except requests.RequestException as error:
                st.error(f"API 실행 실패: {error}")
    if result := st.session_state.get(f"result-{lab_id}"):
        show_result(result)


st.sidebar.title("🧭 Mini Multi-Agent 01")
menu = st.sidebar.radio(
    "학습 메뉴",
    ["과정 안내", "실행 환경 점검"] + [f"{lab_id} · {title}" for lab_id, title in [
        ("01", "Single AI Agent"), ("02", "Independent Agents"), ("03", "Agent 분리 판단"),
        ("04", "아키텍처 비용 비교"), ("05", "Context와 Tool 권한"), ("06", "Orchestration 비교"),
        ("07", "Sequential"), ("08", "Parallel + Join"), ("09", "Router"),
        ("10", "Supervisor–Worker"), ("11", "Handoff"), ("12", "Evaluator–Reviser"),
        ("13", "Provider Failover")]] + ["Provider 비교", "MCP Tool"],
)

try:
    labs, providers, scenarios, patterns, agents = api_get("/api/labs"), api_get("/api/providers"), api_get("/api/scenarios"), api_get("/api/patterns"), api_get("/api/agents")
except requests.RequestException as error:
    st.error(f"Backend에 연결할 수 없습니다: {error}")
    st.stop()

if menu == "과정 안내":
    st.title("Single AI Agent에서 Multi-Agent Orchestration까지")
    st.write("왼쪽 메뉴를 위에서 아래로 진행하며 개념·분리 기준·패턴·Failover를 학습합니다.")
    for group in dict.fromkeys(lab["group"] for lab in labs.values()):
        st.subheader(group)
        for lab_id, lab in labs.items():
            if lab["group"] == group:
                st.write(f"**{lab_id} {lab['title']}** — {lab['question']}")
elif menu == "실행 환경 점검":
    st.title("실행 환경 점검")
    st.dataframe([{"실행 이름": name, **value} for name, value in providers.items()], use_container_width=True)
    st.caption("Llama와 Gemma는 같은 Ollama Server를 사용하지만 설치 모델을 따로 확인합니다.")
    sources = api_get("/api/data-sources")
    st.subheader("MCP Data Source")
    st.dataframe([
        {"Tool 영역": "날씨", "현재 Source": sources["weather"]},
        {"Tool 영역": "여행 장소·교통·알레르기", "현재 Source": sources["travel_knowledge"]},
        {"Tool 영역": "콘텐츠 사실", "현재 Source": sources["content_knowledge"]},
        {"Tool 영역": "품질·코드 요구사항", "현재 Source": sources["quality_requirements"]},
        {"Tool 영역": "고객지원", "현재 Source": sources["support"]},
    ], use_container_width=True)
elif menu == "Provider 비교":
    st.title("같은 Pattern으로 네 LLM 비교")
    pattern = st.selectbox("Pattern", [name for name in patterns if name not in {"provider_failover", "orchestration_comparison"}])
    message = st.text_area("요청", scenarios["travel"], key="compare-message")
    if st.button("GPT·Gemini·Llama·Gemma 비교", type="primary"):
        result = api_post("/api/runs", {"scenario": "travel", "pattern": pattern, "provider_mode": "compare", "provider": "openai", "message": message, "max_steps": 5})
        show_result(result)
elif menu == "MCP Tool":
    st.title("MCP Tool")
    try:
        status = api_get("/api/mcp-status")
        st.success(f"연결됨 · Tool {status['tool_count']}개")
        st.dataframe(status["tools"], use_container_width=True)
    except requests.RequestException as error:
        st.error(f"MCP 연결 실패: {error}")
else:
    lab_id = menu[:2]
    show_lab(lab_id, labs[lab_id], providers, scenarios, patterns, agents)
