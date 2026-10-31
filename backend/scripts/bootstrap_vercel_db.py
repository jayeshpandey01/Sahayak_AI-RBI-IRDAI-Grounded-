"""Create the current ORM schema in a fresh PostgreSQL database for Vercel.

This is a one-time bootstrap for a new, empty database. It is not an upgrade
migration and intentionally refuses to run when tables already exist.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, inspect  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import ArgumentError  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> None:
    database_url = settings.SYNC_DATABASE_URL
    try:
        parsed_url = make_url(database_url)
    except (ArgumentError, TypeError) as exc:
        raise SystemExit(
            "Invalid SYNC_DATABASE_URL. Set it to a PostgreSQL SQLAlchemy URL, "
            "for example postgresql://USER:PASSWORD@HOST:5432/DATABASE. "
            "URL-encode reserved characters in the username or password."
        ) from exc

    if parsed_url.get_backend_name() == "sqlite":
        raise SystemExit("Vercel bootstrap requires a persistent PostgreSQL DATABASE_URL.")
    if parsed_url.get_backend_name() != "postgresql":
        raise SystemExit(
            "Vercel bootstrap requires PostgreSQL. Set SYNC_DATABASE_URL to a "
            "postgresql:// or postgresql+psycopg2:// SQLAlchemy URL."
        )

    # Importing app.database creates the application's global engine. Do this
    # only after validating the URL so malformed configuration gets the error above.
    from app.database import Base  # noqa: PLC0415
    import app.models.db_models  # noqa: PLC0415,F401

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
