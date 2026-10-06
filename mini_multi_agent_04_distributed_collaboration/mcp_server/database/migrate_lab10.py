"""기존 04 DB에 10번 장소 필드와 후보만 추가합니다."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402
from mcp_server.core.config import DATABASE_URL  # noqa: E402


def main() -> None:
    sql = (Path(__file__).resolve().parent / "migrate_lab10.sql").read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL) as database:
        database.execute(sql)
    print("Lab 10 장소 필드와 후보 준비 완료")


if __name__ == "__main__":
    main()
