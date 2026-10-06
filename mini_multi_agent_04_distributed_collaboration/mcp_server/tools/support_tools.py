"""Support Agent와 Refund Agent가 PostgreSQL을 조회하는 Tool입니다."""

from mcp_server.database.collaboration_queries import find_order, find_policy


def get_order_status(order_id: str) -> dict[str, object]:
    order = find_order(order_id)
    return {"success": order is not None, "order": order, "source": "PostgreSQL"}


def get_refund_policy() -> dict[str, object]:
    policy = find_policy("delivery_delay_refund")
    return {"success": policy is not None, "policy": policy, "source": "PostgreSQL"}
