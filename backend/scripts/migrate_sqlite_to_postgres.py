"""Copy application tables from the local SQLite database to PostgreSQL."""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, func, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import PROJECT_ROOT
from app.database.session import Base, normalize_async_database_url
from app.models import Artifact, ChatSession, KnowledgeSource, Message  # noqa: F401

MODEL_TYPES = (Artifact, ChatSession, KnowledgeSource, Message)
DEFAULT_SOURCE_URL = "sqlite+aiosqlite:///./lenny_assistant.db"
LEGACY_COLUMN_NAMES = {
    "messages": {"sources_json": "citations"},
    "artifacts": {"artifact_type": "type"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely merge existing application data from SQLite into PostgreSQL."
    )
    parser.add_argument(
        "--source-url",
        default=os.getenv("SQLITE_SOURCE_URL", DEFAULT_SOURCE_URL),
        help="SQLite source URL (default: SQLITE_SOURCE_URL or the local app database).",
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("POSTGRES_DATABASE_URL"),
        help="PostgreSQL target URL (default: POSTGRES_DATABASE_URL from the environment/.env).",
    )
    return parser.parse_args()


async def migrate(source_url: str, target_url: str) -> dict[str, int]:
    source_url = normalize_async_database_url(source_url)
    target_url = normalize_async_database_url(target_url)
    source_engine = create_async_engine(source_url)
    target_engine = create_async_engine(target_url)

    try:
        async with source_engine.connect() as source_connection:
            source_metadata = MetaData()
            await source_connection.run_sync(source_metadata.reflect)
            source_names = set(source_metadata.tables)
            model_table_names = {model.__tablename__ for model in MODEL_TYPES}
            tables = [
                table
                for table in Base.metadata.sorted_tables
                if table.name in source_names and table.name in model_table_names
            ]
            if not tables:
                raise RuntimeError("The SQLite database contains no recognized application tables.")

            source_rows: dict[str, list[dict[str, object]]] = {}
            for target_table in tables:
                source_table = source_metadata.tables[target_table.name]
                rows = (
                    await source_connection.execute(select(source_table))
                ).mappings().all()
                source_rows[target_table.name] = [
                    {
                        column.name: (
                            row[column.name]
                            if column.name in row
                            else row.get(
                                LEGACY_COLUMN_NAMES.get(target_table.name, {}).get(
                                    column.name, ""
                                )
                            )
                        )
                        for column in target_table.columns
                        if column.name in row
                        or LEGACY_COLUMN_NAMES.get(target_table.name, {}).get(
                            column.name
                        )
                        in row
                    }
                    for row in rows
                ]

        async with target_engine.begin() as target_connection:
            await target_connection.run_sync(Base.metadata.create_all)

            migrated: dict[str, int] = {}
            for table in tables:
                rows = source_rows[table.name]
                primary_keys = list(table.primary_key.columns)
                if len(primary_keys) != 1:
                    raise RuntimeError(
                        f"Migration requires one primary-key column on '{table.name}'."
                    )
                primary_key = primary_keys[0]
                if any(primary_key.name not in row for row in rows):
                    raise RuntimeError(
                        f"Source rows in '{table.name}' are missing primary key '{primary_key.name}'."
                    )

                before_count = await target_connection.scalar(
                    select(func.count()).select_from(table)
                )
                existing_ids: set[object] = set()
                source_ids = [row[primary_key.name] for row in rows]
                for start in range(0, len(source_ids), 500):
                    batch = source_ids[start : start + 500]
                    if batch:
                        result = await target_connection.execute(
                            select(primary_key).where(primary_key.in_(batch))
                        )
                        existing_ids.update(result.scalars().all())

                new_rows = [
                    row for row in rows if row[primary_key.name] not in existing_ids
                ]
                for start in range(0, len(new_rows), 500):
                    await target_connection.execute(
                        table.insert(),
                        new_rows[start : start + 500],
                    )

                after_count = await target_connection.scalar(
                    select(func.count()).select_from(table)
                )
                expected_count = before_count + len(new_rows)
                if after_count != expected_count:
                    raise RuntimeError(
                        f"Row-count validation failed for '{table.name}': "
                        f"expected {expected_count}, found {after_count}."
                    )

                migrated[table.name] = len(new_rows)
                migrated[f"{table.name}_skipped_existing"] = (
                    len(rows) - len(new_rows)
                )
            return migrated
    finally:
        await source_engine.dispose()
        await target_engine.dispose()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    target_url = args.target_url or os.getenv("POSTGRES_DATABASE_URL")
    if not target_url:
        raise SystemExit(
            "Set POSTGRES_DATABASE_URL in the environment or project .env file, "
            "or pass --target-url."
        )

    if not args.source_url.startswith(("sqlite:", "sqlite+")):
        raise SystemExit("--source-url must be a SQLite URL.")
    if not target_url.startswith(("postgres:", "postgresql:")):
        raise SystemExit("The migration target must be a PostgreSQL URL.")

    source_path = args.source_url.split("///", maxsplit=1)[-1]
    if source_path != ":memory:" and not Path(source_path).is_file():
        raise SystemExit(
            f"SQLite database file not found: {source_path}. "
            "Run this command from the backend directory or set SQLITE_SOURCE_URL."
        )

    counts = asyncio.run(migrate(args.source_url, target_url))
    print("Migration completed. Existing rows were left unchanged.")
    for table_name, count in counts.items():
        if table_name.endswith("_skipped_existing"):
            continue
        skipped = counts.get(f"{table_name}_skipped_existing", 0)
        print(f"  {table_name}: {count} inserted, {skipped} already present")


if __name__ == "__main__":
    main()
