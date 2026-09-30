"""03 전용 PostgreSQL Schema를 모듈 또는 파일 경로 실행으로 준비합니다."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402

from mcp_server.core.config import DATABASE_URL  # noqa: E402


def main() -> None:
    sql = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(sql)
    print("mini_multi_agent_03 Schema 준비 완료")


if __name__ == "__main__":
    main()
