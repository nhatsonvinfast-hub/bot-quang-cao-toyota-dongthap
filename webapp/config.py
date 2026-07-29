import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Vercel's deployment bundle is read-only outside /tmp; /tmp itself is
# ephemeral per instance (data does not persist across cold starts). This
# is a known limitation of running this app on serverless — see README.
IS_SERVERLESS = bool(os.getenv("VERCEL"))

if IS_SERVERLESS:
    DATA_DIR = Path("/tmp")
else:
    DATA_DIR = ROOT_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY_PATH = DATA_DIR / ".flask_secret"
    if SECRET_KEY_PATH.exists():
        SECRET_KEY = SECRET_KEY_PATH.read_text().strip()
    else:
        SECRET_KEY = secrets.token_hex(32)
        SECRET_KEY_PATH.write_text(SECRET_KEY)

_pg_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if _pg_url:
    # Neon/Vercel Postgres hands out real, persistent storage — unlike the
    # SQLite fallback below, this survives cold starts on serverless.
    if _pg_url.startswith("postgres://"):
        _pg_url = _pg_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _pg_url
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
else:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

DEFAULT_FB_PAGE_ID = os.getenv("FB_PAGE_ID")
DEFAULT_FB_PAGE_NAME = os.getenv("FB_PAGE_NAME", "")
DEFAULT_FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
