"""Scrapes Kitea Morocco products (Magento 2)."""
import asyncio
import re
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from db import Product, init_db, save_products

BASE = "https://www.kitea.com"

PAGES = {
    "Accueil":  BASE,
    "Salon":    f"{BASE}/par-espaces/salon-et-sejour.html",
}


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


async def scrape_category(page, category: str, url: str) -> List[Product]:
    products = []
    now = datetime.now().isoformat(timespec="seconds")

    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        # scroll to trigger lazy load
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
    except PWTimeout:
        print(f"  [kitea] timeout {category}")
        return products

    cards = await page.query_selector_all(".product-item")
    if not cards:
        print(f"  [kitea] {category}: 0 cards")
        return products

    print(f"  [kitea] {category}: {len(cards)} cards")

    for rank, card in enumerate(cards, 1):
        try:
            name_el = await card.query_selector(".product-item-name")
            name = (await name_el.inner_text()).strip() if name_el else ""
            if not name:
                continue

            price_els = await card.query_selector_all("span.price")
            prices = []
            for el in price_els:
                v = _parse_price(await el.inner_text())
                if v > 0:
                    prices.append(v)
            price = min(prices) if prices else 0.0
            original_price = max(prices) if len(prices) > 1 else price

            discount_pct = 0.0
            if original_price > price > 0:
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
                source="kitea",
                url=full_url,
                image_url=image_url,
                scraped_at=now,
            ))
        except Exception as e:
            print(f"  [kitea] card error: {e}")
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
            print(f"[kitea] scraping {category}...")
            products = await scrape_category(page, category, url)
            all_products.extend(products)
            await asyncio.sleep(2)

        await browser.close()

    save_products(all_products)
    print(f"[kitea] saved {len(all_products)} products")
    return all_products


if __name__ == "__main__":
    asyncio.run(run())
