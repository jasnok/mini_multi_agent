from app.schemas.contracts import AgentRoleCard, SpecialistStatus


LABS = {
    "01": {
        "title": "Agent Role 정의", "question": "Agent 이름만 다르면 역할이 분리될까요?",
        "answer_summary": "아니요. 이름이 아니라 목표, 책임, 하지 않을 일까지 달라야 역할이 분리됩니다.",
        "answer_details": [
            "weather_agent와 budget_agent라는 이름만 붙여도 두 Agent가 같은 Prompt와 Tool을 사용하면 실제 책임은 분리되지 않습니다.",
            "Role에는 Goal, Responsibilities, Non-goals를 함께 적어야 합니다. Non-goal은 다른 Agent의 일을 침범하지 않도록 경계를 만듭니다.",
            "코드에서는 ROLE_CARDS의 goal, responsibilities, non_goals를 비교합니다.",
        ], "real_llm": False, "expected_calls": "0회",
    },
    "02": {
        "title": "Task 분할", "question": "큰 요청을 어떤 책임 단위로 나눌까요?",
        "answer_summary": "각 Agent가 독립적으로 완료하고 결과를 확인할 수 있는 작업 단위로 나눕니다.",
        "answer_details": [
            "여행 요청은 날씨 확인, 장소 검색, 예산 계산, 안전 확인, 일정 통합처럼 책임이 다른 작업으로 나눌 수 있습니다.",
            "Task마다 담당 Agent, 필요한 입력, 기대 출력, 완료 조건이 있어야 끝났는지 판단할 수 있습니다.",
            "문장을 임의로 잘게 자르거나 Provider별로 나누는 것이 아니라 업무 책임과 의존 관계를 기준으로 나눕니다.",
        ], "real_llm": False, "expected_calls": "0회",
    },
    "03": {
        "title": "입출력 계약", "question": "Agent 사이에서 자연어만 주고받아도 될까요?",
        "answer_summary": "사용자 설명에는 자연어가 편하지만 Agent 사이의 경계에는 구조화된 계약이 필요합니다.",
        "answer_details": [
            "자연어만 전달하면 필수값 누락, 숫자 형식, 필드 이름을 다음 Agent가 다시 해석해야 합니다.",
            "Pydantic 입력 계약은 LLM과 Tool을 호출하기 전에 빈 목적지, 0일 여행, 음수 예산을 차단합니다.",
            "Lab 03에서는 destination, days, total_budget 세 필드만 가진 BudgetAgentInput으로 가장 작은 계약부터 확인합니다.",
        ], "real_llm": False, "expected_calls": "0회",
    },
    "04": {
        "title": "역할별 계약", "question": "모든 Agent가 같은 출력 구조를 사용해야 할까요?",
        "answer_summary": "아니요. 공통 실행 정보는 공유하되 업무 결과는 역할에 맞는 계약을 사용해야 합니다.",
        "answer_details": [
            "Weather Agent에는 예보와 주의사항이 필요하고 Budget Agent에는 항목별 금액과 합계가 필요합니다.",
            "모든 결과를 summary 문자열 하나에 넣으면 다음 Agent가 내용을 다시 해석해야 하므로 오류가 늘어납니다.",
            "WeatherResult와 BudgetResult의 JSON Schema를 비교하면 역할별 필드 차이를 확인할 수 있습니다.",
        ], "real_llm": False, "expected_calls": "0회",
    },
    "05": {
        "title": "계약 검증", "question": "타입이 맞으면 업무 의미도 올바를까요?",
        "answer_summary": "아니요. 타입 검증 뒤에 합계, 역할, 상태 같은 업무 규칙도 확인해야 합니다.",
        "answer_details": [
            "모든 금액이 정수여도 breakdown의 합과 total이 다르면 잘못된 예산입니다.",
            "WeatherResult 모양이 맞아도 agent_id가 budget_agent이면 다른 역할의 결과이므로 차단해야 합니다.",
            "계약 통과는 최신 날씨나 실제 가격의 사실성까지 보장하지 않습니다. 사실 확인은 MCP Tool과 출처가 담당합니다.",
        ], "real_llm": False, "expected_calls": "0회",
    },
    "06": {
        "title": "불완전 결과", "question": "정보 부족과 실행 실패는 같은 상태일까요?",
        "answer_summary": "아니요. 정보 부족은 사용자에게 질문하고, 실행 실패는 재시도하거나 종료해야 합니다.",
        "answer_details": [
            "숙박 가격이 없는 것은 업무 입력이 부족한 상태이며 Provider Timeout은 실행 과정이 실패한 상태입니다.",
            "두 상태를 completed=false 하나로만 표현하면 다음 행동을 결정할 수 없습니다.",
            "완료는 다음 Agent 실행, 정보 부족은 추가 질문, 실행 실패는 실패 정책 적용으로 연결합니다.",
        ], "real_llm": False, "expected_calls": "0회",
    },
    "07": {
        "title": "네 LLM 계약 실행", "question": "Provider가 달라도 계약을 유지할 수 있을까요?",
        "answer_summary": "네. Provider 호출 방식은 달라도 Agent의 입력과 출력 계약은 동일하게 유지할 수 있습니다.",
        "answer_details": [
            "OpenAI, Gemini, Llama, Gemma는 호출 API와 모델이 다르지만 결과는 역할별 Pydantic 계약으로 검증합니다.",
            "계약을 Provider와 분리하면 모델을 바꾸어도 다음 Agent와 Orchestrator의 코드를 크게 바꾸지 않아도 됩니다.",
            "같은 계약을 쓴다고 모든 Provider가 항상 성공하거나 같은 품질을 낸다는 뜻은 아닙니다. 오류와 지연 시간은 별도로 기록합니다.",
        ], "real_llm": True, "expected_calls": "4회",
    },
    "08": {
        "title": "검증 결과 전달", "question": "어떤 결과를 다음 Agent에게 전달할 수 있을까요?",
        "answer_summary": "필수 계약과 업무 규칙을 통과해 완료된 결과만 다음 Agent에게 전달합니다.",
        "answer_details": [
            "JSON이 있다는 이유만으로 전달하지 않고 올바른 Agent 결과인지, 필수 필드가 있는지, 업무 불변식을 지키는지 확인합니다.",
            "BudgetResult가 검증되면 Itinerary Agent의 Context로 전달하고, 실패하면 Itinerary Agent를 실행하지 않습니다.",
            "실패 결과를 억지로 보완해 전달하지 않고 Trace에 거부와 Skip을 남기는 것이 안전합니다.",
        ], "real_llm": True, "expected_calls": "2회",
    },
    "09": {
        "title": "다른 업무에 계약 적용", "question": "여행이 아닌 업무에도 같은 Agent 계약 구조를 사용할 수 있을까요?",
        "answer_summary": "네. 역할별 필드는 달라지지만 Role·Task·Contract·검증된 전달 순서는 같습니다.",
        "answer_details": [
            "고객 문의 분석 Agent는 주문번호, 문제와 요청 행동을 SupportCaseResult로 정리합니다.",
            "주문번호가 없으면 값을 추측하지 않고 추가 정보가 필요하다고 반환하며 답변 작성 Agent는 실행하지 않습니다.",
            "03의 Router처럼 담당자를 동적으로 고르지 않고, 02에서 배운 고정된 계약 전달만 다른 업무에 적용합니다.",
        ], "real_llm": True, "expected_calls": "1~2회",
    },
}


LABS["10"] = {
    "title": "AgentTask 실제 실행",
    "question": "Task 명세의 입력·출력·완료 조건을 실행 경계에 어떻게 연결할까요?",
    "answer_summary": "AgentTask를 조회해 필수 입력을 확인하고, 담당 Agent 실행 후 출력과 완료 조건을 검증합니다.",
    "answer_details": [
        "allocate_budget Task의 required_input을 실제 입력 확인에 사용합니다. 빠진 값이 있으면 LLM을 호출하지 않습니다.",
        "agent_id로 등록된 Budget Agent를 실행하고 expected_output 필드와 BudgetResult 계약을 확인합니다.",
        "completion_condition은 설명 문장입니다. 실제 완료 판정은 명시적인 Python 규칙으로 연결합니다.",
    ],
    "real_llm": True, "expected_calls": "0~1회",
}


LABS["11"] = {
    "title": "날씨에 따라 장소·숙소·예산 결정",
    "question": "사용자 문장에 Task 필수 입력이 빠져 있으면 어떻게 할까요?",
    "answer_summary": "날씨 결과를 검증해 실내 장소 여부를 정하고, 장소·숙소 후보·예산을 순서대로 검증합니다.",
    "answer_details": [
        "사용자 문장에서 목적지·일수·인원·이동수단·제약·예산을 추출합니다. 없는 값은 추측하지 않습니다.",
        "부족한 항목은 AgentTask.required_input과 대조해 질문하고, 다음 답변에서 받은 값을 앞선 값과 합칩니다.",
        "입력이 모이면 Weather → Place → Lodging → Budget 순서로 실행하고 검증된 결과만 다음 단계에 전달합니다.",
    ],
    "real_llm": True, "expected_calls": "0~4회",
}


ROLE_CARDS = [
    AgentRoleCard(
        agent_id="weather_agent",
        goal="여행 기간의 날씨 위험과 준비 사항을 정리한다.",
        responsibilities=["날씨 요약", "주의사항 작성", "출처 확인 여부 표시"],
        non_goals=["여행지 예약", "예산 변경", "결제 실행"],
    ),
    AgentRoleCard(
        agent_id="budget_agent",
        goal="사용자 한도 안에서 여행 예산을 항목별로 나눈다.",
        responsibilities=["비용 항목 분류", "총액 계산", "예산 초과 확인"],
        non_goals=["날씨 예측", "예약 확정", "결제 실행"],
    ),
    AgentRoleCard(agent_id="place_agent", goal="사용자 조건에 맞는 장소 후보와 선택 근거를 정리한다.", responsibilities=["장소 조회", "후보 정리", "선택 근거 작성"], non_goals=["날씨 예측", "예산 변경", "일정 확정"]),
    AgentRoleCard(agent_id="safety_agent", goal="사용자 제약의 위험과 확인 행동을 독립적으로 정리한다.", responsibilities=["제약 확인", "위험 정리", "확인 행동 작성"], non_goals=["의학적 진단", "예약 실행", "근거 없는 위험 단정"]),
    AgentRoleCard(agent_id="itinerary_agent", goal="검증된 전문 결과를 날짜별 일정으로 통합한다.", responsibilities=["검증 Context 사용", "날짜별 일정 작성", "반영 조건 표시"], non_goals=["누락 정보 생성", "전문 결과 변경", "예약·결제 실행"]),
]


INCOMPLETE_STATES = {
    "completed": SpecialistStatus(summary="필요한 예산 결과가 준비되었습니다.", completed=True),
    "missing_information": SpecialistStatus(summary="정확한 계산에 정보가 부족합니다.", missing_information=["숙박 가격", "출발지 교통비"], completed=False),
    "execution_error": {"agent_id": "budget_agent", "result": None, "completed": False, "error": "Provider timeout"},
}
