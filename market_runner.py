"""Run both Jumia and Marjane scrapers, print summary, export CSV."""
import asyncio
import sys
from collections import Counter

import jumia_scraper
import marjane_scraper
from db import init_db, export_csv, get_top


async def main():
    init_db()

    print("=" * 50)
    print("MARKET INTEL SCRAPER")
    print("=" * 50)

    targets = sys.argv[1:]  # optional: 'jumia' or 'marjane' to run one
    run_jumia = not targets or "jumia" in targets
    run_marjane = not targets or "marjane" in targets

    all_products = []

    if run_jumia and run_marjane:
        # run concurrently
        results = await asyncio.gather(
            jumia_scraper.run(),
            marjane_scraper.run(),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                print(f"[error] {r}")
            else:
                all_products.extend(r)
    elif run_jumia:
        all_products = await jumia_scraper.run()
    elif run_marjane:
        all_products = await marjane_scraper.run()

    print("\n" + "=" * 50)
    print(f"TOTAL SCRAPED: {len(all_products)} products")

    by_source = Counter(p.source for p in all_products)
    for src, count in by_source.items():
        print(f"  {src}: {count}")

    export_csv()

    print("\nTOP 20 BY REVIEWS (all sources):")
    print(f"{'Rank':<5} {'Source':<10} {'Category':<15} {'Reviews':<8} {'Rating':<7} {'Price':<10} Name")
    print("-" * 90)
    for i, p in enumerate(get_top(20), 1):
        name_short = p["name"][:45] + "…" if len(p["name"]) > 45 else p["name"]
        print(f"{i:<5} {p['source']:<10} {p['category']:<15} {p['review_count']:<8} "
              f"{p['rating']:<7} {p['price']:<10.0f} {name_short}")

    print("\nTOP 20 BY DISCOUNT:")
    from db import DB_PATH
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT source, category, discount_pct, price, name FROM products "
        "WHERE discount_pct > 0 ORDER BY discount_pct DESC LIMIT 20"
    )
    rows = cur.fetchall()
    conn.close()
    print(f"{'#':<4} {'Source':<10} {'Category':<15} {'Disc%':<7} {'Price':<10} Name")
    print("-" * 80)
    for i, (src, cat, disc, price, name) in enumerate(rows, 1):
        name_short = name[:40] + "…" if len(name) > 40 else name
        print(f"{i:<4} {src:<10} {cat:<15} {disc:<7.0f} {price:<10.0f} {name_short}")

    print("\nDone. Data in data/market_intel.db + data/market_intel.csv")


if __name__ == "__main__":
    asyncio.run(main())
