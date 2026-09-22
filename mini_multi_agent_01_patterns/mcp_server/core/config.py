"""MCP Server가 사용하는 환경변수를 한곳에서 읽는다."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


MCP_HOST = env("MCP_HOST", "127.0.0.1")
MCP_PORT = int(env("MCP_PORT", "8010"))
WEATHER_DATA_SOURCE = env("WEATHER_DATA_SOURCE", "live").lower()
SUPPORT_DATA_SOURCE = env("SUPPORT_DATA_SOURCE", "postgresql").lower()

if WEATHER_DATA_SOURCE != "live":
    raise ValueError("WEATHER_DATA_SOURCE는 live만 지원합니다. Mock/JSON fallback은 제거되었습니다.")
if SUPPORT_DATA_SOURCE != "postgresql":
    raise ValueError("SUPPORT_DATA_SOURCE는 postgresql만 지원합니다. Mock/JSON fallback은 제거되었습니다.")
DATABASE_URL = env("DATABASE_URL", "postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db")
