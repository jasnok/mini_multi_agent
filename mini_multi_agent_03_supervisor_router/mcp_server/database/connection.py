import psycopg
from psycopg.rows import dict_row
from mcp_server.core.config import DATABASE_URL

def query_one(sql: str, params: tuple = ()):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        return connection.execute(sql, params).fetchone()
