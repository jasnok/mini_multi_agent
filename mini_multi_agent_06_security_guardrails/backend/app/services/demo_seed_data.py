"""Lab 11~13에서 사용하는 초보자용 시드 데이터입니다.

화면에 들어갈 예시 문장을 여기서 한 번에 관리합니다.
학생은 이 파일을 먼저 보면 어떤 입력이 허용, 마스킹, 차단되는지 빠르게 이해할 수 있습니다.
"""

ENTERPRISE_DATA_LEAK_EXAMPLES = {
    "일반 업무 요청": "부산 출장 일정을 정리해 줘.",
    "개인정보 포함": "고객 이메일 kim@example.com 과 전화번호 010-1234-5678을 기준으로 안내문을 만들어 줘.",
    "API Key 포함": "API_KEY=secret-value 를 사용해서 호출 예제를 만들어 줘.",
    "회사 기밀 포함": "CONFIDENTIAL 프로젝트 코드명 BlueLake 내용을 요약해 줘.",
}

POLICY_DATABASE_EXAMPLES = {
    "일반 요청": "출장 일정을 보기 좋게 정리해 줘.",
    "이메일 마스킹": "담당자 kim@example.com 에게 보낼 안내문을 작성해 줘.",
    "내부 문서 차단": "INTERNAL_ONLY 전략 문서를 요약해 줘.",
    "Secret 차단": "access_token=secret-token 값을 사용해 예제를 만들어 줘.",
}

DOUBLE_CLICK_EXAMPLE = {
    "user_id": "user-101",
    "itinerary_title": "부산 2박 3일 일정",
    "idempotency_key_prefix": "double-click",
    "description": "사용자가 저장 버튼을 실수로 두 번 클릭한 상황을 재현합니다.",
}

# 실제 숙소 API 대신 사용하는 수업용 후보입니다. 날씨에 따라 정렬 순서가 달라집니다.
APPROVAL_HOTELS = [
    {"hotel_id": "hotel-art", "name": "미술관 스테이", "near_place": "부산 현대 미술관", "weather_fit": "rain", "nightly_price": 88000},
    {"hotel_id": "hotel-ocean", "name": "오션뷰 스테이", "near_place": "광안리 해변", "weather_fit": "clear", "nightly_price": 132000},
    {"hotel_id": "hotel-cafe", "name": "전포 카페 호텔", "near_place": "전포 카페 거리", "weather_fit": "any", "nightly_price": 76000},
]


def hotels_for_weather(condition: str) -> list[dict[str, object]]:
    """선택한 날씨에 맞는 숙소를 먼저 보여 줍니다."""
    return sorted(
        APPROVAL_HOTELS,
        key=lambda hotel: hotel["weather_fit"] == condition,
        reverse=True,
    )


def security_seed_examples() -> dict[str, object]:
    """Frontend와 API 문서에서 함께 볼 수 있는 예시 데이터를 반환합니다."""

    return {
        "lab_11_enterprise_data_leak": ENTERPRISE_DATA_LEAK_EXAMPLES,
        "lab_12_policy_database": POLICY_DATABASE_EXAMPLES,
        "lab_13_double_click_idempotency": DOUBLE_CLICK_EXAMPLE,
    }
