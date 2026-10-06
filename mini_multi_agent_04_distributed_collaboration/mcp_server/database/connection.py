import psycopg
from psycopg.rows import dict_row

from mcp_server.core.config import DATABASE_URL


def query(sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    """MCP 조회 Tool이 사용하는 읽기 전용 PostgreSQL 연결입니다."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5) as database:
        database.execute("SET TRANSACTION READ ONLY")
        database.execute("SET LOCAL statement_timeout = '10s'")
        return database.execute(sql, params).fetchall()
