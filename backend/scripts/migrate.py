#!/usr/bin/env python3
"""
Sahayak AI — Versioned Database Migration Runner (Milestone 1)
Safely executes versioned migrations and tracks them in `schema_migrations`.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

# Add backend directory to sys.path so app modules import cleanly
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings

MIGRATIONS_DIR = BACKEND_DIR / "migrations"

def get_engine():
    return create_engine(
        settings.SYNC_DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.SYNC_DATABASE_URL else {}
    )

def init_migrations_table(engine):
    """Ensures the schema_migrations tracking table exists."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(32) PRIMARY KEY,
                name VARCHAR(128) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

def get_applied_migrations(engine) -> dict:
    """Returns a dict of applied migration versions to applied_at timestamp."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version, applied_at FROM schema_migrations ORDER BY version ASC"))
        return {row[0]: row[1] for row in result}

def get_available_migrations() -> list:
    """Discovers all SQL migration files in order."""
    if not MIGRATIONS_DIR.exists():
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(MIGRATIONS_DIR.glob("V*__*.sql"))
    migrations = []
    for f in files:
        version = f.name.split("__")[0]
        name = f.stem.split("__", 1)[1] if "__" in f.stem else f.stem
        migrations.append({"version": version, "name": name, "path": f})
    return migrations

def check_status():
    engine = get_engine()
    init_migrations_table(engine)
    applied = get_applied_migrations(engine)
    available = get_available_migrations()

    print(f"\nDatabase: {engine.dialect.name} ({settings.ENVIRONMENT} mode)")
    print("=" * 65)
    print(f"{'Version':<12} | {'Migration Name':<30} | {'Status':<15}")
    print("-" * 65)

    for m in available:
        v = m["version"]
        if v in applied:
            status_str = f"APPLIED ({applied[v]})"
        else:
            status_str = "PENDING"
        print(f"{v:<12} | {m['name'][:30]:<30} | {status_str:<15}")

    print("=" * 65)
    pending_count = len([m for m in available if m["version"] not in applied])
    print(f"Total: {len(available)} migrations, {pending_count} pending.\n")
    return pending_count

def apply_migrations():
    engine = get_engine()
    init_migrations_table(engine)
    applied = get_applied_migrations(engine)
    available = get_available_migrations()

    pending = [m for m in available if m["version"] not in applied]
    if not pending:
        print("\nAll database migrations are up to date! Nothing to apply.\n")
        return 0

    print(f"\nApplying {len(pending)} pending migrations...")
    for m in pending:
        v = m["version"]
        name = m["name"]
        print(f" -> Executing {v}__{name}...")
        
        sql_content = m["path"].read_text(encoding="utf-8")
        
        with engine.connect() as conn:
            # Execute migration statements
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
            
            # Record in schema_migrations
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                text("INSERT INTO schema_migrations (version, name, applied_at) VALUES (:version, :name, :applied_at)"),
                {"version": v, "name": name, "applied_at": now}
            )
            conn.commit()
            print(f" ✓ Applied {v}__{name}")

    print("\n✓ Database migrations applied successfully.\n")
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        check_status()
    elif cmd == "apply":
        apply_migrations()
    else:
        print(f"Unknown command: {cmd}. Usage: python migrate.py [status|apply]")
        sys.exit(1)

