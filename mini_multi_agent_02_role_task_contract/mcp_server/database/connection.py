import psycopg
from psycopg.rows import dict_row
from mcp_server.core.config import DATABASE_URL

def query(sql: str, params: tuple = ()) -> list[dict]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL statement_timeout = '10s'")
        return connection.execute(sql, params).fetchall()
