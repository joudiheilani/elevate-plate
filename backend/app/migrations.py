"""Small, idempotent schema migrations, run on every startup after create_all().

create_all() only creates missing tables; it never alters existing ones. Databases
created before user accounts existed need an owner column on each data table and
per-user (instead of global) unique constraints. Each step checks before acting, so
running this repeatedly is safe.
"""

from sqlalchemy import inspect, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import OWNED_MODELS

# Old app-wide unique constraints that must become per-user.
_LEGACY_UNIQUES = {
    "meal_plan_entries": ["day", "meal_type"],
    "food_restrictions": ["name"],
}
_PER_USER_UNIQUES = {
    "uq_user_meal_slot": ("meal_plan_entries", "user_id, day, meal_type"),
    "uq_user_restriction": ("food_restrictions", "user_id, name"),
    "uq_profile_user": ("profile", "user_id"),
}


def migrate(engine: Engine) -> list[str]:
    """Bring an existing database up to date. Returns the steps applied."""
    applied = []
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    is_postgres = engine.dialect.name == "postgresql"

    with engine.begin() as conn:
        for model in OWNED_MODELS:
            table = model.__tablename__
            if table not in tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "user_id" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN user_id INTEGER "
                        "REFERENCES users(id) ON DELETE CASCADE"
                    )
                )
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id ON {table} (user_id)")
                )
                applied.append(f"added {table}.user_id")

        # SQLite can't drop constraints; it's only used for local development, where
        # deleting mealplanner.db gives a fresh schema.
        if is_postgres:
            for table, columns in _LEGACY_UNIQUES.items():
                if table not in tables:
                    continue
                for constraint in inspector.get_unique_constraints(table):
                    if constraint["column_names"] == columns:
                        conn.execute(
                            text(f'ALTER TABLE {table} DROP CONSTRAINT "{constraint["name"]}"')
                        )
                        applied.append(f"dropped {table}.{constraint['name']}")

        existing_indexes = {
            index["name"]
            for table in tables
            for index in inspector.get_indexes(table)
            if table in {t for t, _ in _PER_USER_UNIQUES.values()}
        }
        existing_uniques = {
            constraint["name"]
            for table in tables
            if table in {t for t, _ in _PER_USER_UNIQUES.values()}
            for constraint in inspector.get_unique_constraints(table)
        }
        for name, (table, columns) in _PER_USER_UNIQUES.items():
            if table in tables and name not in existing_indexes | existing_uniques:
                conn.execute(
                    text(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} ({columns})")
                )
                applied.append(f"created {name}")

        # The old single-profile code inserted id=1 explicitly, which leaves Postgres's
        # id sequence behind; move it past existing rows so new profiles get fresh ids.
        if is_postgres and "profile" in tables:
            conn.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('profile', 'id'), "
                    "GREATEST((SELECT COALESCE(MAX(id), 0) FROM profile), 1))"
                )
            )
    return applied


def claim_unowned_rows(db: Session, user_id: int) -> None:
    """Give rows created before accounts existed to the first account."""
    for model in OWNED_MODELS:
        db.execute(update(model).where(model.user_id.is_(None)).values(user_id=user_id))
