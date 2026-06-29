import sqlite3
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "market_intel.db"


@dataclass
class Product:
    name: str
    price: float
    original_price: float
    discount_pct: float
    rating: float
    review_count: int
    category: str
    rank: int
    source: str  # 'jumia' | 'marjane'
    url: str
    image_url: str
    scraped_at: str


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            original_price REAL,
            discount_pct REAL,
            rating REAL,
            review_count INTEGER,
            category TEXT,
            rank INTEGER,
            source TEXT,
            url TEXT,
            image_url TEXT,
            scraped_at TEXT
        )
    """)
    # migrate: add image_url if missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(products)").fetchall()]
    if "image_url" not in cols:
        conn.execute("ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT ''")
    # unique constraint: one entry per (name, source) per calendar day
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_product_daily
        ON products (name, source, DATE(scraped_at))
    """)
    conn.commit()
    conn.close()


def save_products(products: List[Product]):
    if not products:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        """INSERT OR REPLACE INTO products
           (name, price, original_price, discount_pct, rating, review_count,
            category, rank, source, url, image_url, scraped_at)
           VALUES (:name, :price, :original_price, :discount_pct, :rating,
                   :review_count, :category, :rank, :source, :url, :image_url, :scraped_at)""",
        [asdict(p) for p in products],
    )
    conn.commit()
    conn.close()


def export_csv(path: str = None, source: Optional[str] = None):
    if path is None:
        path = str(DATA_DIR / "market_intel.csv")
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM products"
    params: list = []
    if source:
        query += " WHERE source = ?"
        params.append(source)
    query += " ORDER BY scraped_at DESC, source, rank ASC"
    cur = conn.execute(query, params)
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(col_names)
        w.writerows(rows)
    print(f"Exported {len(rows)} rows → {path}")


def get_top(n: int = 20, source: Optional[str] = None) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM products"
    params: list = []
    if source:
        query += " WHERE source = ?"
        params.append(source)
    query += " ORDER BY review_count DESC, rating DESC LIMIT ?"
    params.append(n)
    cur = conn.execute(query, params)
    col_names = [d[0] for d in cur.description]
    rows = [dict(zip(col_names, r)) for r in cur.fetchall()]
    conn.close()
    return rows
