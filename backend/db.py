"""Database setup helpers."""
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    """Enable foreign keys and WAL when running the SQLite dev fallback."""
    module = dbapi_connection.__class__.__module__
    if not module.startswith("sqlite3"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def init_app(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        database_path = Path(uri.replace("sqlite:///", "", 1))
        database_path.parent.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
