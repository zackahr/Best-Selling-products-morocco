import sqlite3
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

DB_PATH = Path(__file__).parent.parent.parent / "data" / "market_intel.db"

app = FastAPI(title="Morocco Market Intel")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# scraped_at stored as ISO "2026-06-29T15:12:08" — normalize to space for SQLite DATETIME ops
LATEST_BATCH = (
    "REPLACE(scraped_at, 'T', ' ') >= "
    "DATETIME(REPLACE((SELECT MAX(scraped_at) FROM products), 'T', ' '), '-2 hours')"
)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/bestsellers")
def bestsellers(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort: str = Query("reviews", enum=["reviews", "discount", "rating", "price_asc", "price_desc"]),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    conn = get_conn()
    clauses = []
    params: list = []

    if date:
        clauses.append("DATE(scraped_at) = ?")
        params.append(date)
    else:
        clauses.append(LATEST_BATCH)

    if source:
        clauses.append("source = ?")
        params.append(source)
    if category:
        clauses.append("category = ?")
        params.append(category)

    where = "WHERE " + " AND ".join(clauses)
    order = {
        "reviews": "review_count DESC, rating DESC",
        "discount": "discount_pct DESC",
        "rating": "rating DESC, review_count DESC",
        "price_asc": "price ASC",
        "price_desc": "price DESC",
    }[sort]

    cur = conn.execute(
        f"SELECT * FROM products {where} ORDER BY {order} LIMIT ? OFFSET ?",
        params + [limit, offset],
    )
    rows = [dict(r) for r in cur.fetchall()]
    total = conn.execute(f"SELECT COUNT(*) FROM products {where}", params).fetchone()[0]
    conn.close()
    return {"total": total, "items": rows}


@app.get("/api/categories")
def categories(
    date: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
):
    conn = get_conn()
    clauses = []
    params: list = []
    if date:
        clauses.append("DATE(scraped_at) = ?")
        params.append(date)
    else:
        clauses.append(LATEST_BATCH)
    if source:
        clauses.append("source = ?")
        params.append(source)
    where = "WHERE " + " AND ".join(clauses)
    cur = conn.execute(
        f"SELECT category, COUNT(*) as count FROM products {where} GROUP BY category ORDER BY count DESC",
        params,
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/sources")
def sources():
    conn = get_conn()
    cur = conn.execute(
        "SELECT source, COUNT(*) as count FROM products "
        f"WHERE {LATEST_BATCH} GROUP BY source ORDER BY source"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/dates")
def dates():
    conn = get_conn()
    cur = conn.execute(
        "SELECT DATE(scraped_at) as date, COUNT(*) as count "
        "FROM products GROUP BY DATE(scraped_at) ORDER BY date DESC"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/stats")
def stats(date: Optional[str] = Query(None)):
    conn = get_conn()
    clauses = []
    params: list = []
    if date:
        clauses.append("DATE(scraped_at) = ?")
        params.append(date)
    else:
        clauses.append(LATEST_BATCH)
    where = "WHERE " + " AND ".join(clauses)
    cur = conn.execute(
        f"""SELECT
            COUNT(*) as total,
            COUNT(DISTINCT source) as sources,
            COUNT(DISTINCT category) as categories,
            MAX(discount_pct) as max_discount,
            ROUND(AVG(CASE WHEN rating > 0 THEN rating END), 2) as avg_rating,
            DATE(MAX(scraped_at)) as last_scraped
        FROM products {where}""",
        params,
    )
    row = dict(cur.fetchone())
    conn.close()
    return row


@app.get("/api/image")
async def proxy_image(url: str = Query(...)):
    """Proxy product images to avoid CORS."""
    if not url.startswith("http"):
        raise HTTPException(400, "Invalid URL")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            return Response(
                content=r.content,
                media_type=r.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        raise HTTPException(502, "Image fetch failed")
