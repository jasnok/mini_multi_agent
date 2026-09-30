from mcp_server.database.connection import query_one

def order(order_id: str):
    return query_one("SELECT order_id,status FROM mini_multi_agent_03.orders WHERE order_id=%s", (order_id,))
def refund_policy():
    return query_one("SELECT policy_text FROM mini_multi_agent_03.refund_policies WHERE active=TRUE LIMIT 1")
def help_article(topic: str):
    return query_one("SELECT topic,article FROM mini_multi_agent_03.help_articles WHERE topic=%s", (topic,))
