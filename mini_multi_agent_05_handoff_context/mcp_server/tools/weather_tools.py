import httpx


CITIES = {"부산": {"latitude": 35.1796, "longitude": 129.0756}}


def get_weather(city: str, days: int = 3) -> dict:
    """Open-Meteo에서 실제 일별 날씨를 조회합니다."""
    if city not in CITIES:
        return {"success": False, "city": city, "error": "이 Lab은 부산 좌표를 제공합니다."}
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
    return {"success": True, "city": city, "source": "Open-Meteo", "daily": response.json()["daily"]}
