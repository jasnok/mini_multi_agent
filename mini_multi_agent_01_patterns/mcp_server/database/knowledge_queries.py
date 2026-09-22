"""여행·콘텐츠·코드 실습용 검증 데이터 조회."""
from mcp_server.database.connection import query_all


def find_travel_places(city: str) -> list[dict]:
    return query_all(
        """SELECT name, category, address, nearest_station, indoor,
                  allergy_note, source_url, verified_at
           FROM mini_multi_agent_01.travel_places
           WHERE city = %s ORDER BY place_id""",
        (city,),
    )


def find_transit_guides(city: str) -> list[dict]:
    return query_all(
        """SELECT origin, destination, transport_type, route_summary,
                  estimated_minutes, estimated_fare, source_url, verified_at
           FROM mini_multi_agent_01.transit_guides
           WHERE city = %s ORDER BY guide_id""",
        (city,),
    )


def find_allergy_guidance(city: str) -> list[dict]:
    return query_all(
        """SELECT title, guidance, emergency, source_url, verified_at
           FROM mini_multi_agent_01.allergy_guidance
           WHERE city IN (%s, '공통') ORDER BY emergency DESC, guidance_id""",
        (city,),
    )


def find_content_facts(topic: str) -> list[dict]:
    return query_all(
        """SELECT fact, source_url, verified_at
           FROM mini_multi_agent_01.content_facts
           WHERE topic = %s ORDER BY fact_id""",
        (topic,),
    )


def find_requirements(scenario: str) -> list[dict]:
    return query_all(
        """SELECT requirement_key, requirement_text, source_url, verified_at
           FROM mini_multi_agent_01.quality_requirements
           WHERE scenario = %s ORDER BY requirement_id""",
        (scenario,),
    )
