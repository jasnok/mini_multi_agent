"""Weather Agent가 사용하는 실제 Open-Meteo 읽기 Tool입니다."""

import httpx


CITIES = {
    "서울": {"latitude": 37.5665, "longitude": 126.9780},
    "부산": {"latitude": 35.1796, "longitude": 129.0756},
    "제주": {"latitude": 33.4996, "longitude": 126.5312},
}


def get_weather(city: str, days: int = 3) -> dict[str, object]:
    """지원 도시의 실제 일별 날씨를 Open-Meteo에서 조회합니다."""
    if city not in CITIES:
        return {"success": False, "city": city, "error": "지원 도시는 서울, 부산, 제주입니다."}
    location = CITIES[city]
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            **location,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Asia/Seoul",
            "forecast_days": days,
        },
        timeout=10,
    )
    response.raise_for_status()
    return {"success": True, "city": city, "forecast": response.json()["daily"], "source": "Open-Meteo"}
