# 🇲🇦 Best-Selling Products Morocco

Market intelligence platform that tracks best-selling products and promotions across Morocco's largest e-commerce retailers, stores them daily in a local database, and surfaces trends through a web dashboard.

## Purpose

The goal is to answer "what is selling well in Morocco right now?" automatically. Every day the project:

1. **Scrapes** top sellers and promotion pages from major Moroccan retailers.
2. **Stores** the data in a SQLite database (one snapshot per product per day).
3. **Exports** everything to CSV for offline analysis.
4. **Serves** the latest data through a REST API and a browsable dashboard, so you can rank products by reviews, rating, discount, or price.

Use cases: competitor/product research, pricing & discount monitoring, dropshipping sourcing, or tracking retail trends over time.

## Data Sources

| Source          | Platform             | What is scraped                                   |
|-----------------|----------------------|---------------------------------------------------|
| Jumia.ma        | Custom front-end     | Top sellers across 9 categories (approx. 120/cat) |
| Marjane         | Web                  | Top products & promotions                         |
| Electroplanet   | Magento 2            | "Top Ventes" & "Promotions" pages                 |
| Kitea           | Web                  | Top products & promotions                         |
| Hmizate         | Web                  | Top products & promotions                         |

## Tech Stack

**Scraping (Python)**
- [Playwright](https://playwright.dev/python/) — headless Chromium browser automation for JavaScript-heavy sites
- `requests` + `beautifulsoup4` + `lxml` — targeted HTML parsing
- `pandas` — data handling and CSV export
- `tqdm` — progress bars
- `matplotlib` — analytics/plotting support

**Storage**
- SQLite (`data/market_intel.db`) — schema in `db.py`, one row per (product, source, day)
- CSV export via `db.export_csv()`

**API (Backend)**
- [FastAPI](https://fastapi.tiangolo.com/) + `uvicorn` — REST endpoints:
  - `GET /api/bestsellers` — filterable/sortable product feed
  - `GET /api/categories`, `/api/sources`, `/api/dates` — facet data
  - `GET /api/stats` — aggregate KPIs
  - `GET /api/image` — CORS-safe image proxy
- `httpx` — image proxying

**Dashboard (Frontend)**
- [Next.js](https://nextjs.org/) 14 (App Router) + React 18
- TypeScript
- Tailwind CSS

**Automation**
- `Makefile` — install / scrape / run commands
- `cron` — scheduled daily scrape at 11:00 AM (`make cron`)

## Project Layout

```
.
├── db.py                      # SQLite schema + CRUD + CSV export
├── market_runner.py           # Orchestrates all scrapers, prints rankings
├── jumia_scraper.py           # Jumia.ma scraper
├── marjane_scraper.py         # Marjane scraper
├── electroplanet_scraper.py   # Electroplanet (Magento 2) scraper
├── kitea_scraper.py           # Kitea scraper
├── hmizate_scraper.py         # Hmizate scraper
├── scrape.sh                  # cron entrypoint (daily scrape)
├── requirements.txt           # Root Python dependencies (scraping)
├── Makefile                   # install / scrape / cron / backend / frontend
├── data/                      # SQLite DB + CSV output (generated)
└── platform/
    ├── backend/               # FastAPI app (main.py)
    └── frontend/              # Next.js dashboard (App Router + Tailwind)
```

## Getting Started

```bash
# 1. Install everything (Python deps + Playwright Chromium + Node deps)
make install

# 2. Run the scrapers once
make scrape

# 3. Launch the dashboard (backend :8000 + frontend :3000)
make start
# → Dashboard: http://localhost:3000
# → API:       http://localhost:8000
```

Run only specific sources:

```bash
python3 market_runner.py jumia electroplanet
```

### Automated daily scraping

```bash
make cron        # install a daily 11:00 AM cron job
make cron-remove # remove it
```

### Common make targets

| Command         | Description                              |
|-----------------|------------------------------------------|
| `make install`  | Install Python + Node dependencies       |
| `make scrape`   | Run all scrapers now                     |
| `make cron`     | Install daily cron job (11:00)           |
| `make backend`  | Start FastAPI on :8000                   |
| `make frontend` | Start Next.js on :3000                   |
| `make start`    | Start backend + frontend together        |
| `make setup`    | Full first-time setup (install + cron)   |

## Data Pipeline

```
scrape.sh (cron, 11:00)
        └──▶ market_runner.py ──▶ jumia / marjane / electroplanet / kitea / hmizate scrapers
                                    │
                                    ▼
                             db.save_products()   (Playwright → SQLite)
                                    │
                    ┌───────────────┴────────────────┐
                    ▼                                ▼
          data/market_intel.db           export_csv() → market_intel.csv
                    │
                    ▼
        FastAPI /api/*  (read-only queries)
                    │
                    ▼
        Next.js dashboard (filter / sort / paginate)
```

## Notes

- Each product is stored once per calendar day per source (unique index on `name + source + date`), so you can track price and discount changes over time.
- Scrapers run sequentially to keep memory usage low (each one opens a full browser).
- Respect retailer terms of service — this project is intended for personal research and small-scale use.