from mcp_server.core.config import TRAVEL_DATA_SOURCE, WEATHER_DATA_SOURCE
from mcp_server.database import travel_queries as db
from mcp_server.weather.client import get_live_weather

def get_weather(city: str) -> dict:
    """Open-Meteo에서 여행지의 실제 날씨를 조회합니다."""
    if WEATHER_DATA_SOURCE != "live":
        raise RuntimeError("실시간 날씨 Source가 아닙니다.")
    return get_live_weather(city)

def search_places(city: str) -> dict:
    """PostgreSQL에서 출처가 있는 장소 후보를 조회합니다."""
    items = db.find_places(city)
    return {"success": bool(items), "city": city, "items": items, "source": "postgresql"}

def get_lodging_reference(city: str, days: int) -> dict:
    """교육용 숙박 기준으로 잠정 숙소 유형과 비용을 반환합니다."""
    if days < 2:
        raise ValueError("숙박 여행에는 days가 2 이상이어야 합니다.")
    reference = db.find_budget_reference(city)
    if reference is None:
        return {"success": False, "city": city, "source": "postgresql"}
    nights = days - 1
    nightly_cost = int(reference["lodging_per_night"])
    return {
        "success": True, "city": city,
        "option": f"{city} 대중교통 접근형 숙소 유형(교육용 후보)",
        "nightly_cost": nightly_cost, "nights": nights,
        "total_cost": nightly_cost * nights,
        "availability_confirmed": False,
        "source_note": reference["source_note"],
        "source_url": reference["source_url"],
        "source": "postgresql",
    }


def get_budget_reference(city: str, days: int, people: int, total_budget: int) -> dict:
    """저장된 비용 기준을 조회하고 합계가 정확한 예산안을 계산합니다."""
    if min(days, people, total_budget) < 1:
        raise ValueError("days, people, total_budget은 1 이상이어야 합니다.")
    reference = db.find_budget_reference(city)
    source = "postgresql"
    if reference is None:
        return {
            "success": False,
            "city": city,
            "days": days,
            "people": people,
            "total_budget": total_budget,
            "reference": None,
            "source": source,
        }

    # 금액 계산은 LLM이 아니라 Tool의 결정적 Python 코드가 담당합니다.
    nights = max(days - 1, 1)
    transport = int(reference["transport"]) * people
    lodging = int(reference["lodging_per_night"]) * nights
    food = int(reference["food_per_day"]) * days * people
    required_budget = transport + lodging + food
    budget_feasible = required_budget <= total_budget
    reserve = max(total_budget - required_budget, 0)
    per_person_required = required_budget // people

    return {
        "success": True,
        "city": city,
        "days": days,
        "nights": nights,
        "people": people,
        "total_budget": total_budget,
        "reference": reference,
        "required_budget": required_budget,
        "per_person_required": per_person_required,
        "budget_feasible": budget_feasible,
        "recommended_breakdown": {
            "transport": transport,
            "lodging": lodging,
            "food": food,
            "reserve": reserve,
        },
        "calculation": {
            "transport": f"{reference['transport']} × {people}명",
            "lodging": f"{reference['lodging_per_night']} × {nights}박",
            "food": f"{reference['food_per_day']} × {days}일 × {people}명",
            "reserve": "총예산 - 필수 비용, 음수이면 0",
        },
        "limitations": [
            "교육용 비용 기준이며 실제 예약 가격이 아닙니다.",
            "숙박비는 객실 수가 아닌 여행 전체의 1박 기준으로 계산합니다.",
            "실제 예약 전에는 source_url과 최신 가격을 다시 확인해야 합니다.",
        ],
        "source": source,
    }
