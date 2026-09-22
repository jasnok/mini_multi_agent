"""여행 Agent가 사용하는 날씨·장소·예산 Tool."""
from mcp_server.core.config import WEATHER_DATA_SOURCE
from mcp_server.weather.client import get_live_weather
from mcp_server.database import knowledge_queries as knowledge


def get_weather(city: str) -> dict:
    """Open-Meteo에서 도시의 실제 날씨를 조회합니다."""
    if WEATHER_DATA_SOURCE != "live":
        raise RuntimeError("실시간 날씨 Source가 아닙니다.")
    return get_live_weather(city)


def search_places(city: str) -> dict:
    """PostgreSQL에서 출처가 있는 도시 장소 후보를 조회합니다."""
    items = knowledge.find_travel_places(city)
    return {"success": bool(items), "city": city, "items": items, "source": "postgresql"}


def search_transit(city: str) -> dict:
    """PostgreSQL에서 검증된 대중교통 이동 가이드를 조회합니다."""
    items = knowledge.find_transit_guides(city)
    return {"success": bool(items), "city": city, "items": items, "source": "postgresql"}


def get_allergy_guidance(city: str) -> dict:
    """PostgreSQL에서 알레르기 안전 안내를 조회합니다."""
    items = knowledge.find_allergy_guidance(city)
    return {"success": bool(items), "city": city, "items": items, "source": "postgresql"}


def calculate_budget(days: int, total_budget: int, people: int | None = None) -> dict:
    """사용자가 제시한 총예산을 여행 일수와 선택적 인원수로 나눕니다."""
    if days < 1 or total_budget < 1 or (people is not None and people < 1):
        raise ValueError("days, total_budget, people은 입력된 경우 모두 1 이상이어야 합니다.")
    result = {
        "success": True,
        "days": days,
        "people": people,
        "total_budget": total_budget,
        "daily_total_budget": total_budget // days,
        "source": "deterministic-calculation",
    }
    if people is not None:
        result["per_person_total_budget"] = total_budget // people
        result["per_person_daily_budget"] = total_budget // (days * people)
    return result
