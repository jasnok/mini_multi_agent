import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8010"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db")
