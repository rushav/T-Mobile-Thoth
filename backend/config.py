import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL") or None
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Two-tier model routing for token efficiency:
#   fast    — classification, follow-ups, single-shot answers (cheap, low latency)
#   quality — synthesis, revision, anything that demands accuracy on long context
MODELS = {
    # Haiku 4.5: cheap and fast — used for classification, follow-ups, single-
    # shot retrieval-grounded answers, and clarification generation.
    "fast": os.getenv("CLAUDE_FAST_MODEL", "claude-haiku-4-5-20251001"),
    # Sonnet 4: used for synthesis and revision where accuracy on long context
    # matters more than token cost.
    "quality": os.getenv("CLAUDE_QUALITY_MODEL", "claude-sonnet-4-20250514"),
}

# Bearer token for the /api/v1 benchmark API. The benchmark evaluator passes
# this in the Authorization header. If unset, the middleware accepts any key
# (useful for local dev) but logs a warning.
BENCHMARK_API_KEY = os.getenv("BENCHMARK_API_KEY", "")

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
