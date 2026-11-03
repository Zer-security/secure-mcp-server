import os

from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://YOUR_SERVER_HOST:8000/mcp",
)

MCP_SERVER_CA_CERT = os.getenv("MCP_SERVER_CA_CERT") or True

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "openrouter",
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "openrouter/free",
)

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
)
