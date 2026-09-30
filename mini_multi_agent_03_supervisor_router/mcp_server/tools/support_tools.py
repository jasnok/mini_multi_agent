from mcp_server.database import support_queries as db

def get_order_status(order_id: str) -> dict:
    """PostgreSQL에서 주문 배송 상태를 조회합니다."""
    row = db.order(order_id.upper())
    return {"success": row is not None, "order": row, "source": "postgresql"}
def get_refund_policy() -> dict:
    """PostgreSQL에서 현재 환불 정책을 조회합니다."""
    row = db.refund_policy()
    return {"success": row is not None, "policy": row, "source": "postgresql"}
def search_help_article(topic: str) -> dict:
    """PostgreSQL에서 기술지원 문서를 조회합니다."""
    row = db.help_article(topic)
    return {"success": row is not None, "article": row, "source": "postgresql"}
