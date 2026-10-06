from mcp_server.database.connection import query


def find_places(city: str) -> list[dict[str, object]]:
    return query(
        """SELECT name, category, transit_note, is_indoor, estimated_cost
           FROM mini_multi_agent_04.places
           WHERE city = %s ORDER BY place_id""",
        (city,),
    )


def find_budget_reference(city: str) -> dict[str, object] | None:
    rows = query(
        """SELECT city, daily_budget
           FROM mini_multi_agent_04.budget_reference
           WHERE city = %s""",
        (city,),
    )
    return rows[0] if rows else None


def find_order(order_id: str) -> dict[str, object] | None:
    rows = query(
        """SELECT order_id, status, updated_at
           FROM mini_multi_agent_04.orders
           WHERE order_id = %s""",
        (order_id,),
    )
    return rows[0] if rows else None


def find_policy(policy_key: str) -> dict[str, object] | None:
    rows = query(
        """SELECT policy_key, title, policy_text, version
           FROM mini_multi_agent_04.support_policies
           WHERE policy_key = %s AND active = TRUE""",
        (policy_key,),
    )
    return rows[0] if rows else None
