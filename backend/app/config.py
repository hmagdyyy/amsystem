import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pm_data.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import Portfolio, Holding, CashFlow, NavHistory, Order, UploadLog  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_db()


def _migrate_db():
    """Add any missing columns to existing tables (SQLite doesn't do this via create_all)."""
    import sqlite3
    if not DATABASE_URL.startswith("sqlite"):
        return
    db_path = DATABASE_URL.replace("sqlite:///./", "").replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    migrations = [
        ("portfolios", "beginning_nav_per_unit", "FLOAT NOT NULL DEFAULT 0.0"),
        ("portfolios", "parent_id", "INTEGER"),
        ("portfolios", "portfolio_type", "TEXT NOT NULL DEFAULT 'standalone'"),
        ("portfolios", "cash_balance", "FLOAT NOT NULL DEFAULT 0.0"),
        ("portfolios", "fees_under_payment", "FLOAT NOT NULL DEFAULT 0.0"),
        ("portfolios", "dividends", "FLOAT NOT NULL DEFAULT 0.0"),
        ("holdings", "holding_type", "TEXT NOT NULL DEFAULT 'equity'"),
        ("portfolios", "entity_type", "TEXT NOT NULL DEFAULT 'fund'"),
    ]

    for table, column, col_type in migrations:
        c.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in c.fetchall()]
        if column not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    conn.commit()
    conn.close()
