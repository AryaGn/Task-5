import asyncio
import asyncpg

DB_URL = "postgresql://postgres:postgres@localhost:5432/yc_intelligence_system"

async def fix_tables():
    conn = await asyncpg.connect(DB_URL)

    print("Creating missing tables...")

    await conn.execute("""
    CREATE TABLE IF NOT EXISTS company_changes (
        id SERIAL PRIMARY KEY,
        company_id INT REFERENCES companies(id),
        change_type TEXT,
        old_value TEXT,
        new_value TEXT,
        detected_at TIMESTAMP
    );
    """)

    await conn.execute("""
    CREATE TABLE IF NOT EXISTS company_scores (
        company_id INT PRIMARY KEY REFERENCES companies(id),
        momentum_score NUMERIC,
        stability_score NUMERIC,
        last_computed_at TIMESTAMP
    );
    """)

    await conn.close()
    print("Tables created successfully.")

asyncio.run(fix_tables())
