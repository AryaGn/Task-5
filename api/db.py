import asyncpg
import os

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/yc_intelligence_system"
)

async def get_connection():
    return await asyncpg.connect(DB_URL)
