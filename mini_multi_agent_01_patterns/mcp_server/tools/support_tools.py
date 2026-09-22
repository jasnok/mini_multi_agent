"""고객지원 Agent가 사용하는 주문·환불·도움말 Tool."""
from mcp_server.database import support_queries as db


def get_order_status(order_id: str) -> dict:
    """선택한 Data Source에서 주문 상태를 조회합니다."""
    order_id = order_id.upper()
    row = db.find_order(order_id)
    return {"success": row is not None, "order_id": order_id, "status": row["status"] if row else None, "source": "postgresql"}


def get_refund_policy() -> dict:
    """선택한 Data Source에서 환불 정책을 조회합니다."""
    row = db.find_active_refund_policy()
    return {"success": row is not None, "policy": row["policy_text"] if row else None, "source": "postgresql"}


def search_help_article(topic: str) -> dict:
    """선택한 Data Source에서 기술지원 도움말을 조회합니다."""
    row = db.find_help_article(topic)
    return {"success": row is not None, "topic": topic, "article": row["article"] if row else None, "source": "postgresql"}
