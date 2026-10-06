"""Place Agent와 Budget Agent가 PostgreSQL을 조회하는 Tool입니다."""

from mcp_server.database.collaboration_queries import find_budget_reference, find_places


def search_places(city: str) -> dict[str, object]:
    places = find_places(city)
    return {"success": bool(places), "city": city, "places": places, "source": "PostgreSQL"}


def calculate_budget(days: int, people: int, city: str = "부산") -> dict[str, object]:
    if days < 1 or people < 1:
        return {"success": False, "error": "일수와 인원은 1 이상이어야 합니다."}
    reference = find_budget_reference(city)
    if reference is None:
        return {"success": False, "city": city, "error": "예산 기준을 찾을 수 없습니다."}
    total = days * people * int(reference["daily_budget"])
    return {
        "success": True,
        "city": city,
        "days": days,
        "people": people,
        "daily_budget": reference["daily_budget"],
        "total": total,
        "currency": "KRW",
        "source": "PostgreSQL",
    }
