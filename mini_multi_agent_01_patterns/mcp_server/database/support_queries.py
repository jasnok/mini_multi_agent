"""고객지원 Tool이 사용하는 SQL을 Tool 구현과 분리한다."""
from mcp_server.database.connection import query_one


def find_order(order_id: str) -> dict | None:
    return query_one("SELECT order_id, status FROM mini_multi_agent_01.orders WHERE order_id = %s", (order_id,))


def find_active_refund_policy() -> dict | None:
    return query_one("SELECT policy_text FROM mini_multi_agent_01.refund_policies WHERE active = TRUE ORDER BY policy_id LIMIT 1")


def find_help_article(topic: str) -> dict | None:
    return query_one("SELECT topic, article FROM mini_multi_agent_01.help_articles WHERE topic = %s", (topic,))
