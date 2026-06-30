"""Scrapes Electroplanet Morocco top sellers and promotions (Magento 2)."""
import asyncio
import re
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from db import Product, init_db, save_products

BASE = "https://www.electroplanet.ma"

PAGES = {
    "Top Ventes":  f"{BASE}/top-ventes",
    "Promotions":  f"{BASE}/promotions",
}

MAX_PAGES = 5  # Magento 2 pagination


def _parse_price(text: str) -> float:
    try:
        cleaned = re.sub(r"[^\d,.]", "", text.strip())
        cleaned = cleaned.replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0


async def scrape_page(page, category: str, url: str, page_num: int) -> List[Product]:
    products = []
    now = datetime.now().isoformat(timespec="seconds")
    target = url if page_num == 1 else f"{url}?p={page_num}"

    try:
        await page.goto(target, timeout=35000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
    except PWTimeout:
        print(f"  [electroplanet] timeout {category} p{page_num}")
        return products

    cards = await page.query_selector_all(".product-item")
    if not cards:
        return products

    print(f"  [electroplanet] {category} p{page_num}: {len(cards)} cards")

    for rank, card in enumerate(cards, (page_num - 1) * 40 + 1):
        try:
            name_el = await card.query_selector(".product-item-name")
            name = (await name_el.inner_text()).strip() if name_el else ""
            if not name:
                continue

            price_els = await card.query_selector_all(".price")
            prices = []
            for el in price_els:
                v = _parse_price(await el.inner_text())
                if v > 0:
                    prices.append(v)
            price = min(prices) if prices else 0.0
            original_price = max(prices) if len(prices) > 1 else price

            discount_pct = 0.0
            badge_el = await card.query_selector("[class*='badge'], [class*='discount'], [class*='promo'], .percent")
            if badge_el:
                badge_txt = await badge_el.inner_text()
                m = re.search(r"(\d+)\s*%", badge_txt)
                if m:
                    discount_pct = float(m.group(1))
            elif original_price > price > 0:
                discount_pct = round((1 - price / original_price) * 100, 1)

            img_el = await card.query_selector("img.product-image-photo")
            image_url = ""
            if img_el:
                image_url = (await img_el.get_attribute("src") or
                             await img_el.get_attribute("data-src") or "")

            link_el = await card.query_selector("a.product-item-photo, a.product-item-link")
            href = await link_el.get_attribute("href") if link_el else ""
            full_url = href if href.startswith("http") else f"{BASE}{href}"

            products.append(Product(
                name=name,
                price=price,
                original_price=original_price,
                discount_pct=discount_pct,
                rating=0.0,
                review_count=0,
                category=category,
                rank=rank,
                source="electroplanet",
                url=full_url,
                image_url=image_url,
                scraped_at=now,
            ))
        except Exception as e:
            print(f"  [electroplanet] card error: {e}")
            continue

    return products


async def run() -> List[Product]:
    init_db()
    all_products: List[Product] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="fr-MA",
        )
        page = await context.new_page()

        for category, url in PAGES.items():
            print(f"[electroplanet] scraping {category}...")
            first_name = None
            for page_num in range(1, MAX_PAGES + 1):
                products = await scrape_page(page, category, url, page_num)
                if not products:
                    break
                # stop when Magento loops back to page 1
                if page_num == 1:
                    first_name = products[0].name
                elif products[0].name == first_name:
                    print(f"  [electroplanet] {category}: pagination loop detected, stopping")
                    break
                all_products.extend(products)
                await asyncio.sleep(1.5)

        await browser.close()

    save_products(all_products)
    print(f"[electroplanet] saved {len(all_products)} products")
    return all_products


if __name__ == "__main__":
    asyncio.run(run())
