from mcp_server.database.connection import query

def find_places(city: str) -> list[dict]:
    return query("SELECT name, category, transit_note, source_url, verified_at, indoor FROM mini_multi_agent_02.places WHERE city = %s ORDER BY place_id", (city,))

def find_budget_reference(city: str) -> dict | None:
    rows = query("SELECT transport, lodging_per_night, food_per_day, source_note, source_url, verified_at FROM mini_multi_agent_02.budget_reference WHERE city = %s", (city,))
    return rows[0] if rows else None
