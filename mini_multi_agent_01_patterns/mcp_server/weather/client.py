"""Open-Meteo에서 도시 좌표와 실제 예보를 조회한다."""
import httpx


KOREAN_CITY_QUERIES = {
    "서울": "Seoul",
    "부산": "Busan",
    "대구": "Daegu",
    "인천": "Incheon",
    "광주": "Gwangju",
    "대전": "Daejeon",
    "울산": "Ulsan",
    "제주": "Jeju City",
    "제주도": "Jeju City",
}


def get_live_weather(city: str) -> dict:
    query = KOREAN_CITY_QUERIES.get(city.strip(), city.strip())
    geocoding_params = {"name": query, "count": 5, "language": "ko", "format": "json"}
    if city.strip() in KOREAN_CITY_QUERIES:
        geocoding_params["countryCode"] = "KR"

    with httpx.Client(timeout=10) as client:
        response = client.get("https://geocoding-api.open-meteo.com/v1/search", params=geocoding_params)
        response.raise_for_status()
        locations = response.json().get("results", [])
        if not locations:
            return {"success": False, "city": city, "reason": "도시 좌표를 찾지 못했습니다.", "source": "open-meteo"}

        location = next(
            (item for item in locations if str(item.get("name", "")).casefold() == query.casefold()),
            locations[0],
        )
        response = client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": location["latitude"], "longitude": location["longitude"], "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m", "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code", "timezone": "auto", "forecast_days": 3})
        response.raise_for_status()
        forecast = response.json()

    return {
        "success": True,
        "city": city,
        "geocoding_query": query,
        "resolved_location": {"name": location.get("name"), "admin1": location.get("admin1"), "country": location.get("country"), "latitude": location["latitude"], "longitude": location["longitude"]},
        "current": forecast.get("current"),
        "current_units": forecast.get("current_units"),
        "daily": forecast.get("daily"),
        "daily_units": forecast.get("daily_units"),
        "source": "open-meteo",
    }
