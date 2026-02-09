from fastapi import FastAPI
from db import get_connection

app = FastAPI()


# -------------------------
# SEARCH
# -------------------------
@app.get("/")
async def root():
    return {"status": "YC Intelligence API running"}

@app.get("/api/search")
async def search_companies(
    q: str = "",
    min_score: float = 0,
    limit: int = 20,
    offset: int = 0
):
    conn = await get_connection()

    rows = await conn.fetch(
        """
        SELECT
            c.id,
            c.name,
            COALESCE(s.momentum_score, 0) AS momentum_score,
            ts_rank(c.search_vector, plainto_tsquery($1)) AS rank
        FROM companies c
        LEFT JOIN company_scores s
        ON c.id = s.company_id
        WHERE
            c.search_vector @@ plainto_tsquery($1)
            AND COALESCE(s.momentum_score, 0) >= $2
        ORDER BY momentum_score DESC, rank DESC
        LIMIT $3
        OFFSET $4
        """,
        q,
        min_score,
        limit,
        offset
    )

    await conn.close()
    return [dict(r) for r in rows]


# -------------------------
# COMPANY DETAIL
# -------------------------
@app.get("/api/companies/{company_id}")
async def get_company(company_id: int):
    conn = await get_connection()

    company = await conn.fetchrow(
        "SELECT * FROM companies WHERE id = $1",
        company_id
    )

    snapshots = await conn.fetch(
        """
        SELECT *
        FROM company_snapshots
        WHERE company_id = $1
        ORDER BY scraped_at DESC
        """,
        company_id
    )

    changes = await conn.fetch(
        """
        SELECT *
        FROM company_changes
        WHERE company_id = $1
        ORDER BY detected_at DESC
        """,
        company_id
    )

    scores = await conn.fetchrow(
        """
        SELECT *
        FROM company_scores
        WHERE company_id = $1
        """,
        company_id
    )

    await conn.close()

    return {
        "company": dict(company) if company else None,
        "snapshots": [dict(s) for s in snapshots],
        "changes": [dict(c) for c in changes],
        "scores": dict(scores) if scores else None
    }


# -------------------------
# LEADERBOARD
# -------------------------
@app.get("/api/leaderboard")
async def leaderboard():
    conn = await get_connection()

    top_momentum = await conn.fetch(
        """
        SELECT c.id, c.name, s.momentum_score
        FROM company_scores s
        JOIN companies c ON c.id = s.company_id
        ORDER BY s.momentum_score DESC
        LIMIT 10
        """
    )

    most_stable = await conn.fetch(
        """
        SELECT c.id, c.name, s.stability_score
        FROM company_scores s
        JOIN companies c ON c.id = s.company_id
        ORDER BY s.stability_score DESC
        LIMIT 10
        """
    )

    recent_changes = await conn.fetch(
        """
        SELECT c.id, c.name, ch.detected_at
        FROM company_changes ch
        JOIN companies c ON c.id = ch.company_id
        ORDER BY ch.detected_at DESC
        LIMIT 10
        """
    )

    await conn.close()

    return {
        "top_momentum": [dict(r) for r in top_momentum],
        "most_stable": [dict(r) for r in most_stable],
        "recent_changes": [dict(r) for r in recent_changes]
    }


# -------------------------
# TRENDS
# -------------------------
@app.get("/api/trends")
async def trends():
    conn = await get_connection()

    # Stage change trends
    stage_trends = await conn.fetch(
        """
        SELECT
            change_type,
            COUNT(*) as count
        FROM company_changes
        GROUP BY change_type
        ORDER BY count DESC
        """
    )

    await conn.close()

    return {
        "change_trends": [dict(r) for r in stage_trends]
    }
