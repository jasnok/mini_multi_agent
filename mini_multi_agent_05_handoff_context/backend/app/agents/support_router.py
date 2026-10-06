from app.agents.models import AgentProfile

SUPPORT_ROUTER = AgentProfile(
    agent_id="support_router",
    name="사내 지원 라우터",
    goal="요청을 계정, 기기, 접근 권한 중 한 전문 Agent에게 분류한다.",
    description="요청을 읽고 인계 대상과 책임을 결정한다.",
    instructions=(
        "로그인·비밀번호·계정 잠금은 account_support_agent, "
        "노트북·프린터·네트워크·장치 고장은 device_support_agent, "
        "새 권한·시스템 접근 승인은 access_support_agent로 분류하세요. "
        "실제 문제를 해결했다고 말하지 마세요."
    ),
    provider="openai",
    output_contract="RoutedSupportDecision",
)
