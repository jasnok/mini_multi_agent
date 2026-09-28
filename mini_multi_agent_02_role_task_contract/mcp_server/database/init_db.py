r"""02 전용 PostgreSQL Schema와 Seed 데이터를 준비합니다.

다음 두 실행 방법을 모두 지원합니다.

    python -m mcp_server.database.init_db
    python .\mcp_server\database\init_db.py

파일 경로로 직접 실행하면 Python은 이 파일이 있는 ``database`` 폴더만 검색 경로에
넣습니다. 아래 코드는 프로젝트 루트를 검색 경로에 추가해 ``mcp_server`` Package를
동일하게 import할 수 있게 합니다.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402

from mcp_server.core.config import DATABASE_URL  # noqa: E402


def main() -> None:
    sql_path = Path(__file__).resolve().parent / "schema.sql"
    sql = sql_path.read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(sql)
    print("mini_multi_agent_02 Schema와 Seed 데이터 준비가 완료됐습니다.")


if __name__ == "__main__":
    main()
