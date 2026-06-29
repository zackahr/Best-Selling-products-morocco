"""Scrapes Jumia Morocco category pages via window.__STORE__ JSON extraction."""
import asyncio
import re
import json
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from db import Product, init_db, save_products

BASE = "https://www.jumia.ma"

CATEGORIES = {
    "Telephones": "/telephones-tablettes/",
    "Electronique": "/electronique/",
    "Mode Homme": "/mode-homme/",
    "Mode Femme": "/mode-femme/",
    "Sante Beaute": "/sante-beaute/",
    "Sport": "/sport-fitness/",
    "Jouets": "/jeux-jouets/",
    "Electromenager": "/electromenager/",
    "Epicerie": "/epicerie/",
}

MAX_PAGES = 3  # 40 products/page × 3 = 120 per category


def _parse_price(text: str) -> float:
    try:
        return float(re.sub(r"[^\d.]", "", text.replace(",", "").replace(" ", "")))
    except (ValueError, TypeError):
        return 0.0


def _extract_products(html: str, category: str, page_num: int) -> List[Product]:
    products = []
    now = datetime.now().isoformat(timespec="seconds")

    m = re.search(r"window\.__STORE__=(\{.*?\});</script>", html, re.DOTALL)
    if not m:
        return products

    try:
        store = json.loads(m.group(1))
    except json.JSONDecodeError:
        return products

    raw_products = store.get("products", [])
    offset = (page_num - 1) * 40

    for rank, p in enumerate(raw_products, offset + 1):
        try:
            prices = p.get("prices", {})
            price = _parse_price(prices.get("rawPrice", "0"))
            old_price_str = prices.get("oldPrice", "")
            original_price = _parse_price(old_price_str) if old_price_str else price
            discount_pct = _parse_price(prices.get("discount", "0"))

            rating_data = p.get("rating", {})
            rating = float(rating_data.get("average", 0) or 0)
            review_count = int(rating_data.get("totalRatings", 0) or 0)

            url = p.get("url", "")
            if url and url.startswith("/"):
                url = BASE + url

            image_url = p.get("image", "")

            name = p.get("displayName") or p.get("name", "")
            if not name:
                continue

            products.append(Product(
                name=name,
                price=price,
                original_price=original_price,
                discount_pct=discount_pct,
                rating=rating,
                review_count=review_count,
                category=category,
                rank=rank,
                source="jumia",
                url=url,
                image_url=image_url,
                scraped_at=now,
            ))
        except Exception:
            continue

    return products


async def scrape_category(page, category: str, slug: str) -> List[Product]:
    all_products = []

    for page_num in range(1, MAX_PAGES + 1):
        url = f"{BASE}{slug}" if page_num == 1 else f"{BASE}{slug}?page={page_num}"
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(1)
        except PWTimeout:
            print(f"  [jumia] timeout {category} p{page_num}")
            break

        html = await page.content()
        products = _extract_products(html, category, page_num)

        if not products:
            print(f"  [jumia] {category} p{page_num}: 0 products — stopping")
            break

        all_products.extend(products)
        print(f"  [jumia] {category} p{page_num}: {len(products)} products")

    return all_products


async def run() -> List[Product]:
    init_db()
    all_products: List[Product] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            locale="fr-MA",
        )
        page = await context.new_page()

        # seed cookies by visiting homepage first
        print("[jumia] seeding cookies via homepage...")
        try:
            await page.goto(BASE, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
        except PWTimeout:
            pass

        for category, slug in CATEGORIES.items():
            print(f"[jumia] scraping {category}...")
            products = await scrape_category(page, category, slug)
            all_products.extend(products)
            await asyncio.sleep(2)

        await browser.close()

    save_products(all_products)
    print(f"[jumia] saved {len(all_products)} products total")
    return all_products


if __name__ == "__main__":
    asyncio.run(run())
