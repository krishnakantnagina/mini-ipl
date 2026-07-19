import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Cloud hosts (Render/Railway/Heroku) provide a Postgres URL via DATABASE_URL.
# Without it we fall back to the local SQLite file.
_db_url = os.environ.get("DATABASE_URL",
                         "sqlite:///" + os.path.join(BASE_DIR, "ipl.db"))
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "mini-ipl-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    # Default password: admin123  (override with ADMIN_PASSWORD env var)
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    MAX_SQUAD_SIZE = 15
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # photo uploads capped at 4 MB
