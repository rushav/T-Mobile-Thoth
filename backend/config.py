import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL") or None
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "thoth.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

for d in (DATA_DIR, CHROMA_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
