from app.agents.models import AgentProfile

DEVICE_SUPPORT_AGENT = AgentProfile(
    agent_id="device_support_agent",
    name="기기 지원 Agent",
    goal="기기 문제의 안전한 확인 절차를 안내한다.",
    description="검증된 기기 문제 Context만 받아 처리한다.",
    instructions="전달받은 내용만 사용하세요. 실제 수리나 원격 조치를 완료했다고 말하지 마세요.",
    provider="gemma",
    output_contract="DeviceSupportResult",
)
