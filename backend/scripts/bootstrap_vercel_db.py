"""Create the current ORM schema in a fresh PostgreSQL database for Vercel.

This is a one-time bootstrap for a new, empty database. It is not an upgrade
migration and intentionally refuses to run when tables already exist.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, inspect  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models.db_models  # noqa: E402,F401


def main() -> None:
    database_url = settings.SYNC_DATABASE_URL
    if "sqlite" in database_url.lower():
        raise SystemExit("Vercel bootstrap requires a persistent PostgreSQL DATABASE_URL.")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        existing_tables = set(inspect(engine).get_table_names())
        if existing_tables:
            names = ", ".join(sorted(existing_tables))
            raise SystemExit(
                "Refusing to bootstrap a non-empty database. Use an empty database; "
                f"found existing tables: {names}"
            )

        Base.metadata.create_all(bind=engine)
        created_tables = set(inspect(engine).get_table_names())
        missing_tables = set(Base.metadata.tables) - created_tables
        if missing_tables:
            raise RuntimeError(
                "Database bootstrap did not create all application tables: "
                + ", ".join(sorted(missing_tables))
            )
        print(f"Vercel database bootstrap complete ({len(created_tables)} application tables).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
