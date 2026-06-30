"""Run all scrapers, print summary, export CSV."""
import asyncio
import sys
from collections import Counter

import jumia_scraper
import marjane_scraper
import electroplanet_scraper
import kitea_scraper
import hmizate_scraper
from db import init_db, export_csv, get_top, DB_PATH
import sqlite3

ALL_SCRAPERS = {
    "jumia":         jumia_scraper.run,
    "marjane":       marjane_scraper.run,
    "electroplanet": electroplanet_scraper.run,
    "kitea":         kitea_scraper.run,
    "hmizate":       hmizate_scraper.run,
}


async def main():
    init_db()

    print("=" * 50)
    print("MARKET INTEL SCRAPER")
    print("=" * 50)

    targets = sys.argv[1:]  # pass source names to run only those, e.g. "jumia electroplanet"
    to_run = {k: v for k, v in ALL_SCRAPERS.items() if not targets or k in targets}

    print(f"Running: {', '.join(to_run.keys())}")

    # run sequentially — each scraper opens a full browser, concurrent = memory pressure
    all_products = []
    for name, fn in to_run.items():
        try:
            result = await fn()
            all_products.extend(result)
        except Exception as e:
            print(f"[error] {name}: {e}")

    print("\n" + "=" * 50)
    print(f"TOTAL SCRAPED: {len(all_products)} products")
    by_source = Counter(p.source for p in all_products)
    for src, count in sorted(by_source.items()):
        print(f"  {src}: {count}")

    export_csv()

    print("\nTOP 20 BY REVIEWS:")
    print(f"{'#':<4} {'Source':<15} {'Category':<18} {'Reviews':<8} {'Rating':<7} {'Price':<10} Name")
    print("-" * 95)
    for i, p in enumerate(get_top(20), 1):
        print(f"{i:<4} {p['source']:<15} {p['category']:<18} {p['review_count']:<8} "
              f"{p['rating']:<7} {p['price']:<10.0f} {p['name'][:40]}")

    print("\nTOP 20 BY DISCOUNT:")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT source, category, discount_pct, price, name FROM products "
        "WHERE discount_pct > 0 ORDER BY discount_pct DESC LIMIT 20"
    ).fetchall()
    conn.close()
    print(f"{'#':<4} {'Source':<15} {'Category':<18} {'Disc%':<7} {'Price':<10} Name")
    print("-" * 85)
    for i, (src, cat, disc, price, name) in enumerate(rows, 1):
        print(f"{i:<4} {src:<15} {cat:<18} {disc:<7.0f} {price:<10.0f} {name[:40]}")

    print("\nDone. Data → data/market_intel.db + data/market_intel.csv")


if __name__ == "__main__":
    asyncio.run(main())
