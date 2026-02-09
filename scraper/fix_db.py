import asyncio
import asyncpg

DB_URL = "postgresql://postgres:postgres@localhost:5432/yc_intelligence_system"

async def fix_db():
    conn = await asyncpg.connect(DB_URL)

    print("Fixing database schema...")

    await conn.execute("""
        ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS search_vector tsvector;
    """)

    await conn.execute("""
        UPDATE companies
        SET search_vector = to_tsvector('english', COALESCE(name, ''));
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_companies_search
        ON companies
        USING GIN(search_vector);
    """)

    await conn.close()
    print("Database fixed successfully.")

asyncio.run(fix_db())
