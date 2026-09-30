LABS = {
    "01": {
        "title": "Rule Router", "question": "모든 자연어 분류에 LLM이 필요할까요?",
        "answer_summary": "아니요. 기준이 분명하고 단순하면 Python 규칙이 더 쉽고 일정합니다.",
        "answer_details": ["배송·환불·로그인처럼 명확한 Keyword는 규칙으로 빠르게 분류할 수 있습니다.", "Rule Router는 비용이 없고 같은 입력에 항상 같은 결과를 냅니다.", "표현이 다양하거나 의도가 섞이면 규칙만으로 부족할 수 있으므로 그때 LLM Router를 검토합니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "02": {
        "title": "LLM Router", "question": "선택과 Worker 실행은 왜 분리할까요?",
        "answer_summary": "Router는 담당자만 고르고 실제 업무는 권한과 역할이 제한된 Worker가 수행해야 합니다.",
        "answer_details": ["Router가 답변까지 만들면 선택 책임과 업무 책임이 섞입니다.", "선택된 Worker 하나만 자신의 MCP Tool을 사용해 결과를 만듭니다.", "Trace에서 Router 결정과 Worker 실행이 두 단계로 분리되는지 확인합니다."],
        "real_llm": True, "expected_calls": "최대 2회",
    },
    "03": {
        "title": "Routing 계약", "question": "Prompt만으로 선택 범위를 제한할 수 있을까요?",
        "answer_summary": "아니요. Prompt와 함께 Literal 기반 출력 계약으로 허용 Agent를 제한해야 합니다.",
        "answer_details": ["LLM은 Prompt에 없는 Agent 이름이나 불완전한 결과를 반환할 수 있습니다.", "각 사례에서 고객 질문과 Router 결과를 함께 보고, 허용되지 않은 선택이나 필수 정보 누락을 확인합니다.", "정보 요청을 선택했다면 missing_information도 함께 있어야 한다는 업무 규칙을 검사합니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "04": {
        "title": "Supervisor 결정", "question": "현재 State가 다음 선택에 어떻게 영향을 줄까요?",
        "answer_summary": "Supervisor는 완료된 작업을 확인하고 아직 실행하지 않은 다음 Agent를 선택합니다.",
        "answer_details": ["State에는 완료된 Agent와 검증된 결과가 들어 있습니다.", "완료 작업이 없으면 Analyst, 분석이 끝나면 Developer처럼 다음 선택이 달라집니다.", "Python은 현재 순서에서 허용된 Agent와 Supervisor 선택이 일치하는지 확인합니다."],
        "real_llm": True, "expected_calls": "1회",
    },
    "05": {
        "title": "Supervisor–Worker Loop", "question": "반복과 종료를 누가 통제해야 할까요?",
        "answer_summary": "LLM이 아니라 Python Orchestrator가 순서, 최대 호출 수와 종료를 최종 통제해야 합니다.",
        "answer_details": ["Supervisor는 다음 Agent를 제안하고 Worker는 실제 업무를 수행합니다.", "Worker 성공 결과만 State에 추가한 뒤 Supervisor를 다시 호출합니다.", "모든 Worker 완료, 실패 또는 최대 호출 수 도달 시 Python이 Loop를 종료합니다."],
        "real_llm": True, "expected_calls": "최대 5회",
    },
    "06": {
        "title": "Router vs Supervisor", "question": "어떤 업무에 어떤 구조가 적합할까요?",
        "answer_summary": "한 번 선택하면 되는 업무는 Router, 중간 결과를 보고 반복 선택하면 Supervisor가 적합합니다.",
        "answer_details": ["배송·환불 담당자 선택은 일반적으로 Router로 충분합니다.", "분석→구현→검토처럼 앞 결과가 다음 결정에 필요하면 Supervisor가 적합합니다.", "불필요한 Supervisor는 LLM 호출 수와 실패 지점만 늘릴 수 있습니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "07": {
        "title": "Supervisor와 세 Worker 협업", "question": "Supervisor가 세 Worker의 실행 순서를 어떻게 통제할까요?",
        "answer_summary": "Provider가 달라도 같은 계약, State와 Python 실행 순서를 적용합니다.",
        "answer_details": ["OpenAI Supervisor가 OpenAI Analyst, Llama Developer, Gemma Reviewer를 순서대로 선택합니다.", "Worker 설정은 YAML에 있지만 실행 순서와 종료 조건은 Python이 통제합니다.", "각 Provider의 성공·실패와 지연 시간은 Trace에 남기며 다른 Provider 성공으로 숨기지 않습니다."],
        "real_llm": True, "expected_calls": "최대 7회",
    },
    "09": {
        "title": "검토 피드백으로 계획 수정", "question": "검토가 승인되지 않으면 Supervisor는 어떻게 되돌아갈까요?",
        "answer_summary": "검증된 approved와 feedback을 읽고 계획 Agent를 최대 한 번 다시 실행한 뒤 재검토합니다.",
        "answer_details": ["장애 분석 → 대응 계획 → 검토 순서로 시작합니다.", "검토가 승인되지 않으면 구체적인 feedback을 계획 Agent에게 전달하고 수정본을 다시 검토합니다.", "Python은 허용 전이와 수정 횟수를 통제하며 두 번째 검토도 거절되면 needs_attention으로 종료합니다.", "실제 시스템 조치는 수행하지 않고 대응 계획만 작성합니다."],
        "real_llm": True, "expected_calls": "최대 11회",
    },
    "08": {
        "title": "다른 업무에 Router 적용", "question": "고객지원이 아닌 업무에도 같은 Router 구조를 사용할 수 있을까요?",
        "answer_summary": "네. 계약의 선택 목록과 Worker 역할을 바꾸면 같은 구조를 다른 업무에도 적용할 수 있습니다.",
        "answer_details": ["고객지원 대신 사내 계정·장비·시설 요청을 분류합니다.", "OpenAI Router는 담당자만 선택하고 선택된 Worker 하나가 안내를 작성합니다.", "정보가 부족하면 Worker를 실행하지 않고 필요한 정보를 다시 요청합니다.", "새 데이터베이스와 MCP Tool 없이 Router 구조 자체에 집중합니다."],
        "real_llm": True, "expected_calls": "1~2회",
    },
}


ROUTER_CASES = [
    # 쉬운 단일 의도부터 시작하고, 정보 부족과 복합 의도는 뒤에서 확인합니다.
    {"message": "ORDER-102 배송이 언제 도착하나요?", "expected": "delivery_agent", "learning_point": "명확한 단일 의도와 주문번호"},
    {"message": "주문을 환불하고 싶어요.", "expected": "refund_agent", "learning_point": "환불 Keyword로 담당 Agent 선택"},
    {"message": "로그인이 되지 않아요.", "expected": "technical_support_agent", "learning_point": "로그인 Keyword로 담당 Agent 선택"},
    {"message": "도와주세요.", "expected": "request_information", "learning_point": "담당자를 고를 정보가 부족함"},
    {"message": "ORDER-102 배송이 늦어서 환불하고 싶어요.", "expected": "delivery_agent", "learning_point": "Rule Router는 먼저 일치한 배송 규칙 하나를 선택"},
]


ARCHITECTURE_CASES = [
    {"request": "배송 상태를 알려 주세요.", "structure": "router", "selection_count": "1회", "state_required": False},
    {"request": "환불 정책을 알려 주세요.", "structure": "router", "selection_count": "1회", "state_required": False},
    {"request": "요구사항을 분석한 뒤 검토해 주세요.", "structure": "supervisor", "selection_count": "반복", "state_required": True},
    {"request": "요구사항을 분석하고 구현한 뒤 검토해 주세요.", "structure": "supervisor", "selection_count": "반복", "state_required": True},
]


ROUTING_VALIDATION_CASES = {
    "normal_delivery": {
        "title": "정상: 배송 문의를 배송 Agent로 전달",
        "request": "ORDER-102 배송 상태를 알려 주세요.",
        "issue": "문제 없음. 허용된 Agent와 선택 이유가 있습니다.",
        "expected_valid": True,
        "payload": {"selected_agent": "delivery_agent", "reason": "배송 상태 문의"},
    },
    "valid_information_request": {
        "title": "정상: 사용자에게 추가 질문",
        "request": "도와주세요.",
        "issue": "담당 업무를 판단할 정보가 부족하므로 구체적으로 무엇을 도울지 묻습니다.",
        "expected_valid": True,
        "payload": {
            "selected_agent": "request_information",
            "reason": "문의 유형이 명확하지 않음",
            "missing_information": ["배송·환불·로그인 중 어떤 도움이 필요한지"],
        },
    },
    "unknown_agent": {
        "title": "오류: 허용되지 않은 Agent 선택",
        "request": "결제 내역을 확인해 주세요.",
        "issue": "payment_agent는 SupportRouteDecision의 허용 목록에 없습니다.",
        "expected_valid": False,
        "payload": {"selected_agent": "payment_agent", "reason": "결제 처리"},
    },
    "missing_reason": {
        "title": "오류: 선택 이유 누락",
        "request": "주문을 환불하고 싶어요.",
        "issue": "refund_agent를 선택했지만 필수 필드 reason이 없습니다.",
        "expected_valid": False,
        "payload": {"selected_agent": "refund_agent"},
    },
    "missing_information_list": {
        "title": "오류: 추가 질문 항목 누락",
        "request": "도와주세요.",
        "issue": "정보 부족을 선택했다면 missing_information에 물어볼 내용을 적어야 합니다.",
        "expected_valid": False,
        "payload": {"selected_agent": "request_information", "reason": "문의가 모호함"},
    },
    "contradictory_state": {
        "title": "오류: Worker 선택과 정보 부족 상태가 충돌",
        "request": "배송 문의가 있어요. 주문 번호는 모르겠어요.",
        "issue": "delivery_agent를 선택하면서 missing_information도 기록했습니다. 계약상 둘 중 하나를 선택해야 합니다.",
        "expected_valid": False,
        "payload": {"selected_agent": "delivery_agent", "reason": "배송 문의", "missing_information": ["주문 번호"]},
    },
}
