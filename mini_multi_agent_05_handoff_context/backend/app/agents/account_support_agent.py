from app.agents.models import AgentProfile


ACCOUNT_SUPPORT_AGENT = AgentProfile(
    agent_id="account_support_agent",
    name="계정 지원 Agent",
    goal="검증된 사내 계정 Context로 확인 절차를 안내한다.",
    description="접수 Agent에게 책임을 넘겨받아 계정 문제의 다음 단계를 안내한다.",
    instructions="전달받은 Context만 사용하고 실제 권한 변경이나 비밀번호 초기화를 완료했다고 말하지 마세요.",
    provider="gemma",
    output_contract="AccountSupportResult",
)
