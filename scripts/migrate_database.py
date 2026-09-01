"""Apply the checked-in PostgreSQL schema safely and idempotently.

Run this only against the intended IP-SAKTI database.  It is suitable for
local/dev environments and controlled deployment jobs; production should run
the same script from CI/CD with a short-lived database credential.
"""

import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


async def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required. Copy .env.example to .env and set it first.")
    schema_path = Path(__file__).resolve().parents[1] / "data" / "relational-store" / "schema.sql"
    if not schema_path.exists():
        raise SystemExit(f"Schema file is missing: {schema_path}")
    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute(schema_path.read_text(encoding="utf-8"))
    finally:
        await connection.close()
    print("Database schema migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
