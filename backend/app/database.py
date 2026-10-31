import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger("sahayak.database")

engine = create_engine(
    settings.SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.SYNC_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_all_dbs() -> dict:
    """Verifies connectivity and health of all configured datastores and services."""
    results = {}

    # 1. Primary Relational DB (SQLAlchemy)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results["primary_db"] = {
            "status": "connected",
            "dialect": engine.dialect.name,
            "url": str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url),
            "tables": list(Base.metadata.tables.keys())
        }
    except Exception as exc:
        results["primary_db"] = {
            "status": "error",
            "detail": str(exc)
        }

    # 2. Firebase Service Account & Project
    firebase_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
    if firebase_path.exists():
        try:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(str(firebase_path))
            results["firebase"] = {
                "status": "configured",
                "project_id": creds.project_id,
                "client_email": creds.service_account_email
            }
        except Exception as exc:
            results["firebase"] = {"status": "error", "detail": str(exc)}
    else:
        results["firebase"] = {"status": "not_found", "path": str(firebase_path)}

    # 3. Supabase Configuration
    if settings.SUPABASE_URL:
        results["supabase"] = {
            "status": "configured",
            "url": settings.SUPABASE_URL,
            "has_key": bool(settings.SUPABASE_PUBLISHABLE_KEY),
            "has_secret_key": bool(settings.SUPABASE_SECRET_KEY),
        }
    else:
        results["supabase"] = {"status": "unconfigured"}

    return results

def init_db():
    """Initializes schemas and verifies table integrity."""
    # Ensure all ORM models are registered onto Base.metadata
    import app.models.db_models  # noqa: F401

    if settings.ENVIRONMENT == "production":
        # In production, DO NOT execute DDL create_all() on startup.
        # Verify connectivity only. Schema mutations must be applied via migrate.py.
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Production database connectivity verified. Schema mutations must be applied via migrate.py.")
    else:
        # In development / testing, auto-scaffold missing tables for local developer ergonomics
        Base.metadata.create_all(bind=engine)

        # Ensure backward compatibility for SQLite schemas with missing columns
        if "sqlite" in settings.SYNC_DATABASE_URL:
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE journeys ADD COLUMN user_id VARCHAR(64) DEFAULT 'user_sahayak_demo'"))
                    conn.commit()
                except Exception:
                    pass  # Column already exists or table freshly initialized
                try:
                    conn.execute(text("ALTER TABLE payment_orders ADD COLUMN version INTEGER DEFAULT 1 NOT NULL"))
                    conn.commit()
                except Exception:
                    pass
                try:
                    conn.execute(text("ALTER TABLE payment_orders ADD COLUMN completed_at TIMESTAMP"))
                    conn.commit()
                except Exception:
                    pass
                for statement in (
                    "ALTER TABLE payment_orders ADD COLUMN provider VARCHAR(32) NOT NULL DEFAULT 'stripe'",
                    "ALTER TABLE payment_orders ADD COLUMN provider_transaction_id VARCHAR(128)",
                ):
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception:
                        pass
                bill_columns = {column["name"] for column in inspect(conn).get_columns("recurring_bills")}
                if "schedule_day" not in bill_columns:
                    conn.execute(text(
                        "ALTER TABLE recurring_bills ADD COLUMN schedule_day INTEGER NOT NULL DEFAULT 1"
                    ))
                if "schedule_month" not in bill_columns:
                    conn.execute(text("ALTER TABLE recurring_bills ADD COLUMN schedule_month INTEGER"))
                conn.commit()

    # Verify connectivity with a quick ping
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    db_health = check_all_dbs()
    logger.info(f"Database ready: {db_health['primary_db']['dialect']} with tables {db_health['primary_db'].get('tables')}")
    return db_health
