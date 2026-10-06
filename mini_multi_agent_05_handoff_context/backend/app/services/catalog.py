"""05 화면에서 사용하는 학생용 질문과 상세 답변입니다."""


LABS = {
    "01": {
        "title": "Minimum Context", "question": "다음 Agent에게 전체 State를 모두 넘겨야 할까요?",
        "answer_summary": "아니요. 다음 업무에 꼭 필요한 Context만 골라서 전달해야 합니다.",
        "answer_details": ["전체 대화와 내부 Prompt는 다음 Agent의 업무에 필요하지 않습니다.", "목적지·기간·날씨처럼 일정 작성에 필요한 값만 전달합니다.", "전달 항목이 적으면 정보 노출과 잘못된 해석 가능성도 줄어듭니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "02": {
        "title": "Handoff Envelope", "question": "Context 외에 무엇을 함께 전달해야 할까요?",
        "answer_summary": "누가 누구에게 어떤 책임을 넘기는지 추적할 수 있는 Handoff 정보가 필요합니다.",
        "answer_details": ["from_agent와 to_agent는 책임을 주고받는 Agent를 나타냅니다.", "responsibility는 대상 Agent가 이어서 수행할 업무입니다.", "handoff_id와 trace_id는 중복 처리 방지와 실행 추적에 사용합니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "03": {
        "title": "경로와 Context 확인", "question": "LLM이 Handoff를 제안하면 바로 실행해도 될까요?",
        "answer_summary": "아니요. Python이 허용 경로, 현재 책임자와 전달 Context를 먼저 확인해야 합니다.",
        "answer_details": ["YAML에는 허용된 출발·도착 Agent와 필요한 Context를 적습니다.", "Python은 현재 책임자, 사용자, 중복 ID와 민감정보를 확인합니다.", "검사를 통과한 proposed Handoff만 validated 상태가 됩니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "04": {
        "title": "Ownership Transition", "question": "책임자는 언제 대상 Agent로 바뀌어야 할까요?",
        "answer_summary": "대상 Agent가 Handoff를 받아 유효한 결과를 만든 뒤에 바뀌어야 합니다.",
        "answer_details": ["Handoff 제안이나 검증만으로 책임자를 바꾸지 않습니다.", "대상 Agent 실행이 실패하면 원래 Agent가 책임을 유지합니다.", "성공한 뒤 owner_agent와 Handoff 상태를 함께 갱신합니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "05": {
        "title": "Rejection and Failure", "question": "어떤 Handoff를 실행 전에 차단해야 할까요?",
        "answer_summary": "다른 사용자, 잘못된 경로, 민감정보, 필수 Context 누락과 중복 요청을 차단합니다.",
        "answer_details": ["차단된 Handoff는 대상 Agent를 실행하지 않습니다.", "실패 이유를 숨기지 않고 rejected 또는 failed 상태로 남깁니다.", "수락 전에 실패하면 원래 책임자가 그대로 유지됩니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "06": {
        "title": "실제 여행 Handoff", "question": "실제 Agent Handoff는 어떤 순서로 실행될까요?",
        "answer_summary": "OpenAI가 날씨를 확인해 Handoff를 제안하고, 검증 후 Gemma 3 1B가 일정을 작성합니다.",
        "answer_details": ["Weather Agent는 Open-Meteo 결과를 읽고 전달할 날씨 Context를 만듭니다.", "Python이 경로와 최소 Context를 검증합니다.", "Gemma Itinerary Agent가 성공한 뒤 책임자가 변경되며 Event가 화면에 표시됩니다."],
        "real_llm": True, "expected_calls": "최대 2회",
    },
    "07": {
        "title": "다른 업무에 Handoff 적용", "question": "여행이 아닌 업무에도 같은 책임 이전 구조를 사용할 수 있을까요?",
        "answer_summary": "네. 사내 IT 접수 Agent가 계정 지원 Agent에게 책임과 최소 Context를 넘길 수 있습니다.",
        "answer_details": ["OpenAI 접수 Agent가 계정 문제를 확인하고 Handoff를 제안합니다.", "직원 ID·시스템 이름·문제 내용만 검증하여 전달합니다.", "Gemma 3 1B 계정 지원 Agent가 결과를 만든 뒤에만 책임자가 변경됩니다.", "새 데이터베이스와 MCP Tool 없이 Handoff 구조 자체를 비교합니다."],
        "real_llm": True, "expected_calls": "최대 2회",
    },
    "08": {
        "title": "라우터가 선택하는 세 가지 Handoff",
        "question": "라우터가 대상 Agent를 고르면 각 Handoff의 Context는 어떻게 달라질까요?",
        "answer_summary": "선택한 경로의 정책에 맞춰 Envelope를 만들고 Guard가 검증한 뒤 대상 Agent에게 전달합니다.",
        "answer_details": [
            "라우터의 RoutedSupportDecision Output Contract가 대상·이유·책임을 정합니다.",
            "선택된 경로에서 허용된 최소 Context만 전달합니다. 기기 문제는 요청 내용에 기기 이름을 적습니다.",
            "검증된 HandoffEnvelope만 대상 Agent에게 전달하고, 결과를 받은 뒤 책임자를 바꿉니다.",
        ],
        "real_llm": True, "expected_calls": "2회",
    },
    "09": {
        "title": "간단한 환불 문의 Handoff",
        "question": "상담 Agent의 결과로 어떤 내용을 환불 Agent에게 전달할까요?",
        "answer_summary": "상담 결과의 주문번호와 문의 내용을 Envelope에 담아 검증한 뒤 환불 Agent에게 넘깁니다.",
        "answer_details": [
            "SupportRefundDecision Output Contract가 인계 이유·책임·최소 Context를 정합니다.",
            "HandoffEnvelope를 만든 뒤 Guard가 주문번호와 문의 내용, 경로를 확인합니다.",
            "RefundHandoffResult가 반환되면 환불 문의 책임자를 환불 Agent로 바꿉니다.",
            "이 실습에서는 실제 환불을 실행하지 않습니다.",
        ],
        "real_llm": True, "expected_calls": "2회",
    },

}
