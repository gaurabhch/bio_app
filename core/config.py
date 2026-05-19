"""
Centralised configuration — reads from the single .env at project root.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env that sits alongside main.py  (i.e. app/.env)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

# ── Database URLs ────────────────────────────────────────────────────
AUTH_DATABASE_URL: str = os.environ["AUTH_DATABASE_URL"]      # Login_Signup Neon DB
DATABASE_URL: str = os.environ["DATABASE_URL"]                # Features + Questionnaire Neon DB

# ── LLM / AI ────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── Firebase ─────────────────────────────────────────────────────────
FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT_PATH",
    str(Path(__file__).resolve().parent.parent / "serviceAccountKey.json"),
)
