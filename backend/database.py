from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite() -> None:
    """Tiny ad-hoc migration layer.

    SQLAlchemy's create_all only creates missing tables — it does NOT add new
    columns to existing tables. When we add columns to a model, list them here
    so existing dev DBs pick them up without needing a wipe.
    """
    insp = inspect(engine)
    additions = {
        "knowledge_entries": [
            ("updated_at", "DATETIME"),
        ],
    }
    with engine.begin() as conn:
        for table, cols in additions.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl_type in cols:
                if name in existing:
                    continue
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
                except Exception:
                    pass


def init_db():
    import models  # noqa: F401 — ensure models are registered
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()
