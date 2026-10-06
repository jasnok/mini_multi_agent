"""mini_multi_agent_04 Schema와 교육용 업무 데이터를 PostgreSQL에 준비합니다."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402

from mcp_server.core.config import DATABASE_URL  # noqa: E402


def main() -> None:
    sql = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL) as database:
        database.execute(sql)
    print("mini_multi_agent_04 Schema와 Seed 데이터 준비가 완료됐습니다.")


if __name__ == "__main__":
    main()
