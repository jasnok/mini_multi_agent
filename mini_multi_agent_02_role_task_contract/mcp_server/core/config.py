import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8010"))
WEATHER_DATA_SOURCE = os.getenv("WEATHER_DATA_SOURCE", "live").lower()
TRAVEL_DATA_SOURCE = os.getenv("TRAVEL_DATA_SOURCE", "postgresql").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db")

if WEATHER_DATA_SOURCE != "live":
    raise ValueError("WEATHER_DATA_SOURCE는 live만 지원합니다. Mock/JSON fallback은 제거되었습니다.")
if TRAVEL_DATA_SOURCE != "postgresql":
    raise ValueError("TRAVEL_DATA_SOURCE는 postgresql만 지원합니다. Mock/JSON fallback은 제거되었습니다.")
