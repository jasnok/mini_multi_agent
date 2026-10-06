"""06 화면에서 사용하는 학생용 질문과 상세 답변입니다."""


LABS = {
    "01": {"title": "Prompt Injection", "question": "사용자 입력이 Agent의 지시를 바꾸려고 하면 어떻게 해야 할까요?", "answer_summary": "LLM과 Tool을 호출하기 전에 Python이 의심 문구를 검사하고 차단합니다.", "answer_details": ["정상 여행 요청과 이전 지시를 무시하라는 요청을 비교합니다.", "차단된 입력은 LLM에게 전달하지 않습니다.", "단순 문구 검사는 여러 방어선 중 첫 단계이며 완벽한 방어로 보지 않습니다."], "real_llm": False, "expected_calls": "0회"},
    "02": {"title": "Input Validation", "question": "문장이 안전해 보여도 입력 형식을 확인해야 할까요?", "answer_summary": "네. Pydantic 계약으로 길이, 범위, 빈 값을 별도로 검사합니다.", "answer_details": ["여행 일수는 1~7일처럼 허용 범위를 정합니다.", "취향 개수와 문자열 길이도 제한합니다.", "보안 문구 검사와 데이터 형식 검사는 서로 다른 역할입니다."], "real_llm": False, "expected_calls": "0회"},
    "03": {"title": "Response Policy", "question": "LLM이 만든 답변은 바로 사용자에게 보내도 될까요?", "answer_summary": "아니요. 허위 실행 주장과 민감정보가 없는지 마지막에 다시 검사합니다.", "answer_details": ["예약이나 결제를 하지 않았는데 완료했다고 말하면 차단합니다.", "API Key·비밀번호·Access Token 표현도 검사합니다.", "입력 검사를 통과했어도 출력 검사는 별도로 필요합니다."], "real_llm": False, "expected_calls": "0회"},
    "04": {"title": "Agent · Tool Permission", "question": "Agent 설명에 Tool 사용 금지를 적으면 충분할까요?", "answer_summary": "아니요. 서버가 Agent별 Tool 허용 목록을 실행 직전에 확인해야 합니다.", "answer_details": ["Weather Agent는 get_weather만 사용할 수 있습니다.", "허용되지 않은 save_itinerary 요청은 Python이 차단합니다.", "Prompt의 역할 설명은 안내이고 서버 권한 검사가 실제 경계입니다."], "real_llm": False, "expected_calls": "0회"},
    "05": {"title": "Approval Boundary", "question": "조회와 데이터 변경을 같은 기준으로 실행해도 될까요?", "answer_summary": "아니요. 변경 작업은 사용자의 명확한 승인을 확인한 뒤에만 실행해야 합니다.", "answer_details": ["날씨 조회는 자동으로 실행할 수 있습니다.", "일정 저장과 같은 변경 작업은 승인 여부를 확인합니다.", "이 예제는 실제 예약이나 결제를 수행하지 않습니다."], "real_llm": False, "expected_calls": "0회"},
    "06": {"title": "Idempotent Write", "question": "같은 저장 요청이 재시도되면 두 번 실행될 수 있을까요?", "answer_summary": "멱등성 키로 같은 요청을 식별하여 중복 변경을 막습니다.", "answer_details": ["첫 요청은 executed, 같은 재시도는 reused가 됩니다.", "같은 키에 다른 요청 내용이 들어오면 conflict로 차단합니다.", "네트워크 재시도가 실제 변경을 반복하지 않도록 합니다."], "real_llm": False, "expected_calls": "0회"},
    "07": {"title": "Context Access", "question": "모든 Agent가 전체 State를 읽어야 할까요?", "answer_summary": "아니요. Agent가 자신의 업무에 필요한 필드만 받도록 제한합니다.", "answer_details": ["Weather Agent는 목적지와 일수만 받습니다.", "내부 메모처럼 필요 없는 값은 전달 전에 제거합니다.", "Context 허용 목록은 YAML에 선언하고 Python이 실제 값을 골라냅니다."], "real_llm": False, "expected_calls": "0회"},
    "08": {"title": "Integrated Guardrail", "question": "여러 보안 검사는 실제 Workflow에서 어떤 순서로 동작할까요?", "answer_summary": "입력→Context→Tool→LLM→응답 검사를 순서대로 실행하고 모두 기록합니다.", "answer_details": ["Prompt Injection이면 Tool과 LLM 실행 전에 중단합니다.", "정상 요청은 실제 날씨와 OpenAI 초안을 거쳐 Gemma 3 1B가 답변을 정리합니다.", "허용·차단·실패를 Redis Audit Event에서 같은 run_id로 확인합니다."], "real_llm": True, "expected_calls": "최대 2회"},
    "09": {"title": "다른 업무에 Guardrail 적용", "question": "여행이 아닌 고객지원 답변에도 같은 보안 순서를 사용할 수 있을까요?", "answer_summary": "네. 입력 검사, 최소 Context와 응답 검사는 업무가 달라도 그대로 적용할 수 있습니다.", "answer_details": ["OpenAI가 고객 문의 초안을 만들고 Gemma 3 1B가 사용자 답변을 정리합니다.", "고객 ID·문제 내용만 전달하고 내부 메모와 API Key는 제거합니다.", "공격 입력은 LLM 호출 전에 차단하고 최종 답변도 다시 검사합니다.", "새 데이터베이스와 MCP Tool 없이 Guardrail 구조 자체를 비교합니다."], "real_llm": True, "expected_calls": "0회 또는 2회"},
    "10": {
        "title": "Human-in-the-loop Approval",
        "question": "Agent가 변경 작업을 제안하면 사용자가 확인할 때까지 실행을 멈출 수 있을까요?",
        "answer_summary": "네. 변경 내용을 승인 요청으로 저장하고 Workflow를 멈춘 뒤, 올바른 사용자가 승인했을 때만 저장을 실행합니다.",
        "answer_details": [
            "Agent는 일정을 바로 저장하지 않고 승인 요청을 만든 뒤 pending_approval 상태로 멈춥니다.",
            "사용자는 실제 저장할 일정과 실행 내용을 확인한 뒤 승인하거나 거부합니다.",
            "승인은 특정 실행 인자와 연결되며 다른 사용자, 만료된 승인과 변경된 인자는 차단합니다.",
            "승인 전과 거부 후에는 저장 함수가 실행되지 않고 모든 결정은 Audit Event에 기록됩니다.",
        ],
        "real_llm": True,
        "expected_calls": "초안 생성 1회",
    },
    "11": {
        "title": "Enterprise Data Leak Guard",
        "question": "직원이 회사 기밀이나 개인정보를 AI에게 붙여 넣으면 어떻게 막을까요?",
        "answer_summary": "외부 LLM 호출 전에 Python Guard가 개인정보와 회사 기밀을 차단하거나 마스킹합니다.",
        "answer_details": [
            "고객 이메일과 전화번호는 마스킹할 수 있습니다.",
            "API Key, access_token, INTERNAL_ONLY 문구는 외부 전송 전에 차단합니다.",
            "중요한 보안 판단은 LLM에게 맡기지 않고 Python 코드가 결정합니다.",
        ],
        "real_llm": False,
        "expected_calls": "0회",
    },
    "12": {
        "title": "Policy Database Guard",
        "question": "보안 단어와 패턴을 코드가 아니라 DB에서 관리할 수 있을까요?",
        "answer_summary": "자주 바뀌는 보안 정책은 저장소에서 읽고 Python Guard가 최종 판단합니다.",
        "answer_details": [
            "예제에서는 Python list를 DB처럼 사용합니다.",
            "운영에서는 Supabase, PostgreSQL, Redis, 사내 정책 DB로 바꿀 수 있습니다.",
            "정책 저장소를 바꿔도 Tool 실행 권한 자체는 서버 코드가 강제해야 합니다.",
        ],
        "real_llm": False,
        "expected_calls": "0회",
    },
    "13": {
        "title": "Double Click Idempotency",
        "question": "사용자가 저장 버튼을 두 번 누르면 데이터도 두 번 저장될까요?",
        "answer_summary": "같은 idempotency key를 사용하면 두 요청이 와도 실제 저장은 한 번만 실행됩니다.",
        "answer_details": [
            "첫 번째 클릭은 executed가 됩니다.",
            "두 번째 클릭은 reused가 되어 저장 함수를 다시 실행하지 않습니다.",
            "이 구조는 더블클릭, 새로고침, 네트워크 재시도 상황에서 중복 저장을 막습니다.",
        ],
        "real_llm": False,
        "expected_calls": "0회",
    }
}
