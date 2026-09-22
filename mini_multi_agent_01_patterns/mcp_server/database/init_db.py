"""01 전용 PostgreSQL Schema와 교육용 Seed 데이터를 생성한다."""
import sys
from pathlib import Path

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.core.config import DATABASE_URL


def main() -> None:
    sql = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL, connect_timeout=5) as connection:
        connection.execute(sql)
    print("mini_multi_agent_01 Schema와 Seed 데이터 준비가 완료됐습니다.")


if __name__ == "__main__":
    main()
