from app.agents.models import AgentProfile


IT_TRIAGE_AGENT = AgentProfile(
    agent_id="it_triage_agent",
    name="사내 IT 접수 Agent",
    goal="사내 IT 요청을 확인하고 계정 지원 Handoff 필요성을 판단한다.",
    description="요청을 처음 접수하고 전문 Agent에게 넘길 책임을 정리한다.",
    instructions="계정·로그인·권한 문제이면 account_support_agent Handoff를 제안하세요. 직접 해결했다고 말하지 마세요.",
    provider="openai",
    output_contract="InternalHandoffDecision",
)
