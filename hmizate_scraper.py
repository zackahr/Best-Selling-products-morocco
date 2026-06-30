"""Scrapes Hmizate Morocco deals (PrestaShop)."""
import asyncio
import re
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from db import Product, init_db, save_products

BASE = "https://www.hmizate.ma"

PAGES = {
    "High Tech":    f"{BASE}/35-high-tech",
    "Electromenager": f"{BASE}/36-electromenager",
    "Mode":         f"{BASE}/38-mode-et-beaute",
    "Maison":       f"{BASE}/39-maison-et-jardin",
    "Sport":        f"{BASE}/40-sport-et-loisirs",
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


async def scrape_page(page, category: str, url: str) -> List[Product]:
    products = []
    now = datetime.now().isoformat(timespec="seconds")

    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
    except PWTimeout:
        print(f"  [hmizate] timeout {category}")
        return products

    # PrestaShop product cards
    cards = await page.query_selector_all(".tvproduct-wrapper, article.product-miniature, .product-miniature")
    if not cards:
        # fallback
        cards = await page.query_selector_all("[class*='product']:not([class*='product-list'])")

    print(f"  [hmizate] {category}: {len(cards)} cards")

    for rank, card in enumerate(cards, 1):
        try:
            # name — take first line only to avoid concatenated category text
            name = ""
            for name_sel in [".tvproduct-name", ".product-title", "h2", "h3"]:
                name_el = await card.query_selector(name_sel)
                if name_el:
                    name = (await name_el.inner_text()).strip().splitlines()[0].strip()
                    if name:
                        break
            if not name:
                continue

            # price — try specific children first to avoid concat
            price = 0.0
            original_price = 0.0

            current_el = await card.query_selector(".current-price, .tvproduct-price-after, [class*='current']")
            regular_el = await card.query_selector(".regular-price, .tvproduct-price-before, [class*='regular'], [class*='old']")

            if current_el:
                price = _parse_price(await current_el.inner_text())
            if regular_el:
                original_price = _parse_price(await regular_el.inner_text())

            if price == 0:
                # fallback: grab all price text and take min
                price_el = await card.query_selector(".tv-product-price, .price")
                if price_el:
                    raw = await price_el.inner_text()
                    nums = re.findall(r"[\d]+[,.][\d]+", raw)
                    vals = [_parse_price(n) for n in nums if _parse_price(n) > 0]
                    if vals:
                        price = min(vals)
                        original_price = max(vals) if len(vals) > 1 else price

            if original_price < price:
                original_price = price

            discount_pct = 0.0
            if original_price > price > 0:
                discount_pct = round((1 - price / original_price) * 100, 1)
            else:
                disc_el = await card.query_selector(".product-flag.discount, [class*='discount'], [class*='promo']")
                if disc_el:
                    m = re.search(r"(\d+)\s*%", await disc_el.inner_text())
                    if m:
                        discount_pct = float(m.group(1))

            # image
            img_el = await card.query_selector("img.tvproduct-defult-img, img[class*='product'], img")
            image_url = ""
            if img_el:
                image_url = (await img_el.get_attribute("src") or
                             await img_el.get_attribute("data-src") or "")

            # link
            link_el = await card.query_selector("a.thumbnail, a.product-thumbnail, a[href]")
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
                source="hmizate",
                url=full_url,
                image_url=image_url,
                scraped_at=now,
            ))
        except Exception as e:
            print(f"  [hmizate] card error: {e}")
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
            print(f"[hmizate] scraping {category}...")
            products = await scrape_page(page, category, url)
            all_products.extend(products)
            await asyncio.sleep(2)

        await browser.close()

    save_products(all_products)
    print(f"[hmizate] saved {len(all_products)} products")
    return all_products


if __name__ == "__main__":
    asyncio.run(run())
