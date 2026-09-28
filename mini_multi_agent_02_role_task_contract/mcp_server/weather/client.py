import httpx

KOREAN_CITY_QUERIES = {
    "서울": "Seoul", "부산": "Busan", "대구": "Daegu", "인천": "Incheon",
    "광주": "Gwangju", "대전": "Daejeon", "울산": "Ulsan",
    "제주": "Jeju City", "제주도": "Jeju City",
}

def get_live_weather(city: str) -> dict:
    requested_city = city.strip()
    query = KOREAN_CITY_QUERIES.get(requested_city, requested_city)
    params = {"name": query, "count": 5, "language": "ko", "format": "json"}
    if requested_city in KOREAN_CITY_QUERIES:
        params["countryCode"] = "KR"
    with httpx.Client(timeout=10) as client:
        response = client.get("https://geocoding-api.open-meteo.com/v1/search", params=params)
        response.raise_for_status()
        locations = response.json().get("results", [])
        if not locations:
            return {"success": False, "city": city, "reason": "도시 좌표를 찾지 못했습니다.", "source": "open-meteo"}
        location = next((item for item in locations if str(item.get("name", "")).casefold() == query.casefold()), locations[0])
        response = client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": location["latitude"], "longitude": location["longitude"], "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m", "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max", "timezone": "auto", "forecast_days": 3})
        response.raise_for_status()
        forecast = response.json()
    return {"success": True, "city": city, "geocoding_query": query, "resolved_location": {"name": location.get("name"), "admin1": location.get("admin1"), "country": location.get("country"), "latitude": location.get("latitude"), "longitude": location.get("longitude")}, "current": forecast.get("current"), "daily": forecast.get("daily"), "source": "open-meteo"}
