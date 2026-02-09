import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from db import get_connection

BASE_URL = "https://www.ycombinator.com/companies"

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def now_utc():
    return datetime.now(timezone.utc)


def generate_hash(data: dict) -> str:
    text = json.dumps(data, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()


# -------------------------
# DATABASE
# -------------------------

async def upsert_company(conn, company):
    row = await conn.fetchrow(
        """
        INSERT INTO companies (yc_company_id, name, first_seen_at, last_seen_at)
        VALUES ($1, $2, $3, $3)
        ON CONFLICT (yc_company_id)
        DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
        RETURNING id
        """,
        company["id"],
        company["name"],
        now_utc()
    )
    return row["id"]


async def insert_snapshot(conn, company_id, snapshot):
    snapshot_hash = generate_hash(snapshot)

    prev = await conn.fetchrow(
        """
        SELECT snapshot_hash
        FROM company_snapshots
        WHERE company_id = $1
        ORDER BY scraped_at DESC
        LIMIT 1
        """,
        company_id
    )

    if prev and prev["snapshot_hash"] == snapshot_hash:
        return False

    await conn.execute(
        """
        INSERT INTO company_snapshots
        (company_id, batch, stage, description,
         location, tags, employee_range,
         scraped_at, snapshot_hash)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        company_id,
        snapshot["batch"],
        snapshot["stage"],
        snapshot["description"],
        snapshot["location"],
        json.dumps(snapshot["tags"]),
        snapshot["employee_range"],
        now_utc(),
        snapshot_hash
    )

    return True


# -------------------------
# SCRAPER
# -------------------------

async def scrape_all():
    conn = await get_connection()
    start_time = time.time()

    total = 0
    changes = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(BASE_URL)

        # Wait for initial company cards
        await page.wait_for_selector("a[href^='/companies/']", timeout=15000)

        # Scroll multiple times
        for _ in range(20):
            await page.mouse.wheel(0, 5000)
            await asyncio.sleep(1)

        # Extract links
        links = await page.eval_on_selector_all(
            "a[href^='/companies/']",
            "elements => elements.map(e => e.getAttribute('href'))"
        )

        # Remove duplicates
        unique_links = list(set(links))

        companies = []
        for link in unique_links:
            if not link:
                continue
            yc_id = link.split("/")[-1]
            companies.append({
                "id": yc_id,
                "name": yc_id,
                "url": "https://www.ycombinator.com" + link
            })

        print("Found companies:", len(companies))

        # Scrape details
        for comp in companies[:100]:  # safe limit
            try:
                await page.goto(comp["url"])
                html = await page.content()

                description = ""
                if 'meta name="description"' in html:
                    i = html.index('meta name="description"')
                    description = html[i:i+300]

                snapshot = {
                    "batch": "",
                    "stage": "",
                    "description": description,
                    "location": "",
                    "tags": [],
                    "employee_range": ""
                }

                company_id = await upsert_company(conn, comp)
                changed = await insert_snapshot(conn, company_id, snapshot)

                if changed:
                    changes += 1

                total += 1
                print(comp["id"], "processed")

            except Exception as e:
                logging.error(f"Failed {comp['id']}: {e}")

        await browser.close()

    total_time = time.time() - start_time

    print("\nScrape complete")
    print("Total companies:", total)
    print("Total changes:", changes)
    print("Runtime:", round(total_time, 2), "seconds")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(scrape_all())
