"""04 화면에서 사용하는 학습 질문과 답변입니다."""


LABS = {
    "01": {
        "title": "Execution Plan", "question": "Agent를 실행하기 전에 무엇을 먼저 정해야 할까요?",
        "answer_summary": "실행할 Agent, 순서, 선행 단계와 결과를 합칠 위치를 계획해야 합니다.",
        "answer_details": ["Execution Plan은 코드가 실행되기 전에 전체 작업 순서를 보여 주는 지도입니다.", "depends_on은 먼저 끝나야 할 단계이며 join은 여러 결과를 합치는 단계임을 표시합니다.", "Python은 중복 단계와 아직 정의되지 않은 선행 단계를 실행 전에 차단합니다."],
        "real_llm": False, "expected_calls": "0회",
    },
    "02": {
        "title": "Sequential Workflow", "question": "앞 Agent의 결과를 다음 Agent에게 어떻게 전달할까요?",
        "answer_summary": "앞 Agent의 검증된 결과를 Context로 저장한 뒤 다음 Agent의 입력으로 전달합니다.",
        "answer_details": ["Research 결과가 Writer에게, Writer 결과가 Reviewer에게 순서대로 전달됩니다.", "앞 Agent가 실패하면 검증된 Context가 없으므로 다음 Agent를 실행하지 않습니다.", "Orchestrator가 결과와 완료 Agent를 Shared State에 기록합니다."],
        "real_llm": True, "expected_calls": "최대 3회",
    },
    "03": {
        "title": "Parallel Workers", "question": "서로 독립적인 Agent를 동시에 실행할 수 있을까요?",
        "answer_summary": "네. 서로의 결과가 필요 없는 작업은 동시에 실행할 수 있습니다.",
        "answer_details": ["Weather, Place, Budget Agent는 같은 여행 요청을 독립적으로 처리합니다.", "asyncio.gather로 함께 실행하므로 완료 순서는 Provider 응답 시간에 따라 달라질 수 있습니다.", "Worker는 Shared State를 직접 수정하지 않고 Orchestrator가 각 결과를 기록합니다."],
        "real_llm": True, "expected_calls": "3회",
    },
    "04": {
        "title": "Join Results", "question": "병렬 결과를 언제 하나로 합칠 수 있을까요?",
        "answer_summary": "미리 정한 필수 결과가 모두 준비되고 계약을 통과했을 때 합칠 수 있습니다.",
        "answer_details": ["Weather와 Budget은 필수 결과이고 Place는 선택 결과입니다.", "필수 결과가 준비되면 Itinerary Agent가 병렬 결과를 Context로 받아 일정을 만듭니다.", "필수 결과가 없으면 Join Guard가 최종 Agent 실행을 차단합니다."],
        "real_llm": True, "expected_calls": "최대 4회",
    },
    "05": {
        "title": "Partial Failure", "question": "일부 Agent가 실패해도 계속할 수 있을까요?",
        "answer_summary": "실패한 Agent의 역할과 미리 선택한 정책에 따라 계속할 수 있습니다.",
        "answer_details": ["선택 Agent인 Place가 실패해도 Weather와 Budget이 있으면 계속할 수 있습니다.", "필수 Agent인 Weather 또는 Budget이 실패하면 최종 일정 생성을 중단합니다.", "실패 후 즉석에서 기준을 바꾸지 않고 실행 전에 정한 정책을 적용합니다."],
        "real_llm": True, "expected_calls": "3회",
    },
    "06": {
        "title": "Handoff Workflow", "question": "질문이 바뀌면 인계 대상과 전달 정보도 어떻게 달라질까요?",
        "answer_summary": "상담 Agent가 환불·배송·직접 답변 중 경로를 고르고, 인계 경로에는 필요한 Context만 전달합니다.",
        "answer_details": ["환불 문의는 refund_agent에게 주문번호와 환불 문의 내용을 넘깁니다.", "배송 문의는 delivery_agent에게 주문번호와 배송 문의 내용을 넘깁니다.", "일반 질문은 Handoff 없이 상담 Agent가 답합니다.", "04에서는 분기 흐름을 미리 보고 Handoff 계약과 보안은 05에서 자세히 학습합니다."],
        "real_llm": True, "expected_calls": "1~2회",
    },
    "07": {
        "title": "Distributed Workflow", "question": "병렬 실행과 Join의 진행 상황을 어떻게 확인할까요?",
        "answer_summary": "각 Agent의 시작·완료·실패 Event와 마지막 Shared State를 같은 run_id로 확인합니다.",
        "answer_details": ["세 Worker가 병렬 실행되고 실제 완료 순서대로 화면에 Event가 표시됩니다.", "필수 결과가 준비되면 Aggregator가 Join을 수행합니다.", "기본 수업은 Agent 순서와 Join을 보고 Redis Stream, SSE와 Snapshot은 심화로 확인합니다."],
        "real_llm": True, "expected_calls": "최대 4회",
    },
    "08": {
        "title": "다른 업무에 Parallel + Join 적용", "question": "여행이 아닌 업무에도 같은 병렬 협업 구조를 사용할 수 있을까요?",
        "answer_summary": "네. 서로 독립적인 작업을 동시에 실행하고 필수 결과가 준비되면 하나로 합치는 원리는 같습니다.",
        "answer_details": ["온라인 행사 준비를 콘텐츠·홍보·운영 작업으로 나누어 동시에 실행합니다.", "콘텐츠와 운영은 필수 결과이고 홍보는 선택 결과입니다.", "필수 결과가 준비된 뒤 Gemma 3 1B가 결과를 하나의 행사안으로 합칩니다.", "새 데이터베이스나 MCP Tool 없이 Parallel과 Join 구조 자체를 다시 확인합니다."],
        "real_llm": True, "expected_calls": "최대 4회",
    },
    "09": {
        "title": "LangGraph 순차 여행 Workflow",
        "question": "앞 Agent의 결과를 다음 Agent가 이어받는 여행 Workflow는 어떻게 만들까요?",
        "answer_summary": "날씨부터 가이드까지 순서대로 실행하고 검증된 누적 결과를 다음 Node의 Context로 전달합니다.",
        "answer_details": [
            "Weather → Place → Lodging → Budget → Guide 순서로 Node를 실행합니다.",
            "각 Agent는 자신보다 앞서 완료된 Agent 결과 전체를 Context로 받습니다.",
            "어느 단계든 실패하면 조건 Edge가 END로 이동해 근거 없는 후속 결과를 만들지 않습니다.",
            "07의 병렬·Join 예제와 비교하면 독립 작업과 의존 작업의 차이를 확인할 수 있습니다.",
        ],
        "real_llm": True, "expected_calls": "최대 5회",
    },
    "10": {
        "title": "LangGraph 날씨 → 장소 → 예산",
        "question": "날씨 결과가 뒤의 장소 선택과 예산에 어떻게 영향을 줄까요?",
        "answer_summary": "날씨 Tool의 강수확률로 실내·실외 경로를 고르고, DB 장소 비용을 예산에 반영합니다.",
        "answer_details": [
            "Weather Agent가 Open-Meteo 결과를 가져오면 Guard가 강수확률을 기준과 비교합니다.",
            "LangGraph 조건 Edge가 실내 또는 실외 장소 Node를 선택합니다. Place Agent의 DB 조회 후보만 사용합니다.",
            "Budget Agent의 기준 금액에 선택 장소의 1인 예상 비용 × 인원을 더해 예산 한도와 비교합니다.",
            "날씨·장소·예산 Tool이 실패하면 다음 결정을 추측하지 않고 종료합니다.",
        ],
        "real_llm": True, "expected_calls": "최대 3회",
    },
    "11": {
        "title": "온라인 주문 Join Guard",
        "question": "재고와 결제 중 하나의 결과가 없는데 주문 안내를 만들어도 될까요?",
        "answer_summary": "아니요. Python Join Guard가 재고·결제 결과를 모두 확인한 뒤에만 주문 안내 Agent를 실행합니다.",
        "answer_details": [
            "재고와 결제 확인은 필수, 쿠폰 안내는 선택 결과입니다.",
            "세 Agent를 병렬 실행한 후 Python 코드가 필수 결과 두 개를 검사합니다.",
            "재고 또는 결제 결과가 없으면 주문 안내 Agent는 실행되지 않습니다. 쿠폰만 없어도 진행합니다.",
            "모든 결과는 교육용 모의 결과이며 실제 주문·결제는 실행하지 않습니다.",
        ],
        "real_llm": True, "expected_calls": "실패 선택에 따라 2~4회",
    },

}
