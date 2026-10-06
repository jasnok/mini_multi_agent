from pathlib import Path

import yaml

from app.agents.models import AgentProfile


POLICY_PATH = Path(__file__).parent / "definitions" / "security_policies.yaml"


INPUT_GUARD_AGENT = AgentProfile(
    agent_id="input_guard_agent",
    name="Input Guard Agent",
    goal="사용자 입력의 형식과 Prompt Injection 위험을 먼저 검사한다.",
    description="LLM 호출 전에 실행되는 결정적 입력 방어선입니다.",
    instructions="의심 요청을 수정해서 성공시키지 말고 차단 이유를 명확히 기록하세요.",
    allowed_tools=frozenset(),
)

WEATHER_AGENT = AgentProfile(
    agent_id="weather_agent",
    name="Weather Agent",
    goal="허용된 MCP Tool로 실제 날씨만 조회한다.",
    description="최소 Context만 받고 get_weather만 사용할 수 있습니다.",
    instructions="Tool Result에 없는 날씨를 만들지 마세요.",
    allowed_tools=frozenset({"get_weather"}),
)

TRAVEL_AGENT = AgentProfile(
    agent_id="travel_agent",
    name="OpenAI Travel Agent",
    goal="검증된 입력과 실제 날씨로 여행 초안을 만든다.",
    description="실제 OpenAI를 사용하지만 예약이나 결제는 수행하지 않습니다.",
    instructions="제공된 날씨와 사용자 조건만 사용하고 실행하지 않은 작업을 완료했다고 말하지 마세요.",
    allowed_tools=frozenset(),
)

ITINERARY_AGENT = AgentProfile(
    agent_id="itinerary_agent",
    name="Safe Itinerary Agent",
    goal="사용자가 승인한 경우에만 완성된 일정을 저장한다.",
    description="조회와 답변 생성은 하지 않고 변경 작업의 승인 경계를 보여 줍니다.",
    instructions="승인 정보가 없거나 현재 요청과 다르면 저장을 제안하거나 실행하지 마세요.",
    allowed_tools=frozenset({"save_itinerary", "book_demo_hotel"}),
)

RESPONSE_GUARD_AGENT = AgentProfile(
    agent_id="response_guard_agent",
    name="Response Guard Agent",
    goal="최종 응답의 허위 실행 주장과 민감정보를 차단한다.",
    description="Gemma 응답 뒤에 실행되는 결정적 출력 방어선입니다.",
    instructions="Policy 위반 답변은 사용자에게 전달하지 말고 이유를 Audit Log에 기록하세요.",
    allowed_tools=frozenset(),
)

SUPPORT_DRAFT_AGENT = AgentProfile(
    agent_id="support_draft_agent",
    name="고객지원 초안 Agent",
    goal="검증된 고객 문의 Context로 안전한 안내 초안을 만든다.",
    description="내부 메모와 민감정보를 받지 않고 고객 문의 초안만 작성합니다.",
    instructions="전달받은 Context만 사용하고 실제 계정 변경이나 처리를 완료했다고 말하지 마세요.",
    allowed_tools=frozenset(),
)

SUPPORT_ANSWER_AGENT = AgentProfile(
    agent_id="support_answer_agent",
    name="고객지원 답변 Agent",
    goal="검증된 초안을 사용자가 읽기 쉬운 답변으로 정리한다.",
    description="Gemma 3 1B로 최종 답변을 만들며 새로운 사실을 추가하지 않습니다.",
    instructions="초안에 없는 사실과 민감정보를 추가하지 말고 실행하지 않은 작업을 완료했다고 말하지 마세요.",
    allowed_tools=frozenset(),
)

AGENTS = {
    profile.agent_id: profile
    for profile in [INPUT_GUARD_AGENT, WEATHER_AGENT, TRAVEL_AGENT, ITINERARY_AGENT, RESPONSE_GUARD_AGENT, SUPPORT_DRAFT_AGENT, SUPPORT_ANSWER_AGENT]
}


def load_policies() -> dict[str, object]:
    with POLICY_PATH.open(encoding="utf-8") as policy_file:
        policies = yaml.safe_load(policy_file)
    if not isinstance(policies, dict):
        raise ValueError("security_policies.yaml 형식이 올바르지 않습니다.")
    required_sections = {"input", "tools", "write_tools", "context_access", "response"}
    missing_sections = required_sections - set(policies)
    if missing_sections:
        raise ValueError(f"Security Policy 필수 Section 누락: {sorted(missing_sections)}")
    policy_agents = set(policies["tools"])
    unknown_agents = policy_agents - set(AGENTS)
    if unknown_agents:
        raise ValueError(f"Tool Policy가 등록되지 않은 Agent를 참조합니다: {sorted(unknown_agents)}")
    for agent_id, profile in AGENTS.items():
        declared = set(policies["tools"].get(agent_id, []))
        if declared != set(profile.allowed_tools):
            raise ValueError(
                f"{agent_id}의 Python/YAML Tool 권한이 다릅니다: "
                f"python={sorted(profile.allowed_tools)}, yaml={sorted(declared)}"
            )
    all_allowed_tools = {
        tool_name for tool_names in policies["tools"].values() for tool_name in tool_names
    }
    unknown_write_tools = set(policies["write_tools"]) - all_allowed_tools
    if unknown_write_tools:
        raise ValueError(f"허용 목록에 없는 변경 Tool입니다: {sorted(unknown_write_tools)}")
    if not isinstance(policies["input"].get("max_length"), int) or policies["input"]["max_length"] < 1:
        raise ValueError("input.max_length는 1 이상의 정수여야 합니다.")
    return policies


# 잘못된 YAML 설정은 요청 처리 중이 아니라 애플리케이션 시작 시 차단합니다.
load_policies()


def registry_view() -> dict[str, object]:
    return {
        "agents": {
            agent_id: {
                "name": profile.name,
                "goal": profile.goal,
                "description": profile.description,
                "allowed_tools": sorted(profile.allowed_tools),
            }
            for agent_id, profile in AGENTS.items()
        },
        "policies": load_policies(),
    }
