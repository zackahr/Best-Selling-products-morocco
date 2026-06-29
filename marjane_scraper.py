"""Scrapes Marjane Morocco promotions page.
Note: Marjane is primarily an online grocery — data reflects food/FMCG promotions.
"""
import asyncio
import re
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from db import Product, init_db, save_products

BASE = "https://www.marjane.ma"

PAGES = {
    "Promotions": f"{BASE}/promotions",
}

# additional pagination via scroll — Marjane loads more on scroll
MAX_SCROLLS = 5


def _parse_price(text: str) -> float:
    try:
        # "74,95DH" → 74.95
        cleaned = re.sub(r"[^\d,.]", "", text)
        cleaned = cleaned.replace(",", ".")
        # handle "1.299.00" (thousands separator then decimal)
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0


async def scrape_page(page, section: str, url: str) -> List[Product]:
    products = []
    now = datetime.now().isoformat(timespec="seconds")

    try:
        await page.goto(url, timeout=40000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
    except PWTimeout:
        print(f"  [marjane] timeout on {section}")
        return products

    # scroll to load more products
    prev_count = 0
    for _ in range(MAX_SCROLLS):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        cards = await page.query_selector_all('[class*="product-card"]')
        if len(cards) == prev_count:
            break
        prev_count = len(cards)

    cards = await page.query_selector_all('[class*="product-card"]')
    print(f"  [marjane] {section}: {len(cards)} cards")

    for rank, card in enumerate(cards, 1):
        try:
            # name
            name_el = await card.query_selector("h2")
            if not name_el:
                name_el = await card.query_selector("h3, h1, [class*='title'], [class*='name']")
            name = (await name_el.inner_text()).strip() if name_el else ""

            if not name:
                raw = await card.inner_text()
                lines = [l.strip() for l in raw.splitlines() if l.strip()]
                name = lines[0] if lines else ""

            # price — first [class*="price"] span
            price = 0.0
            price_els = await card.query_selector_all('[class*="price"]')
            prices_found = []
            for el in price_els:
                txt = (await el.inner_text()).strip()
                v = _parse_price(txt)
                if v > 0:
                    prices_found.append(v)
            if prices_found:
                price = min(prices_found)

            # check for old price (strikethrough)
            original_price = price
            old_el = await card.query_selector('[class*="old"], [class*="before"], s, del, strike')
            if old_el:
                old_txt = (await old_el.inner_text()).strip()
                v = _parse_price(old_txt)
                if v > price:
                    original_price = v

            discount_pct = 0.0
            if original_price > price > 0:
                discount_pct = round((1 - price / original_price) * 100, 1)
            else:
                # look for % badge
                badge_el = await card.query_selector('[class*="badge"], [class*="discount"], [class*="promo"], [class*="reduction"]')
                if badge_el:
                    badge_txt = await badge_el.inner_text()
                    m = re.search(r"(\d+)\s*%", badge_txt)
                    if m:
                        discount_pct = float(m.group(1))

            # link
            a_el = await card.query_selector("a[href]")
            href = await a_el.get_attribute("href") if a_el else ""
            full_url = f"{BASE}{href}" if href and href.startswith("/") else href or url

            # image
            img_el = await card.query_selector("img")
            image_url = ""
            if img_el:
                image_url = await img_el.get_attribute("src") or ""
                if not image_url:
                    srcset = await img_el.get_attribute("srcset") or ""
                    if srcset:
                        image_url = srcset.split(",")[0].split(" ")[0]

            # category from URL path
            path_parts = href.split("/") if href else []
            category = section
            if len(path_parts) > 2:
                category = path_parts[2].replace("-", " ").title()

            if not name or len(name) < 3:
                continue

            products.append(Product(
                name=name,
                price=price,
                original_price=original_price,
                discount_pct=discount_pct,
                rating=0.0,
                review_count=0,
                category=category,
                rank=rank,
                source="marjane",
                url=full_url,
                image_url=image_url,
                scraped_at=now,
            ))
        except Exception as e:
            print(f"  [marjane] parse error rank {rank}: {e}")
            continue

    return products


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

        for section, url in PAGES.items():
            print(f"[marjane] scraping {section}...")
            products = await scrape_page(page, section, url)
            all_products.extend(products)
            await asyncio.sleep(2)

        await browser.close()

    save_products(all_products)
    print(f"[marjane] saved {len(all_products)} products total")
    return all_products


if __name__ == "__main__":
    asyncio.run(run())
