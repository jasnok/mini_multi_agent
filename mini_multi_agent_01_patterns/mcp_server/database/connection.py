"""MCP Tool이 공유하는 읽기 전용 PostgreSQL Query 함수."""
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.core.config import DATABASE_URL


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5)


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with connect() as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL statement_timeout = '10s'")
        return connection.execute(sql, params).fetchone()


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL statement_timeout = '10s'")
        return connection.execute(sql, params).fetchall()
