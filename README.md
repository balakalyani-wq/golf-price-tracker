# Golf Equipment Price Tracker — a live pricing & availability analytics pipeline

A real, scheduled data pipeline that captures daily price and stock
snapshots for a golf-equipment catalog, models them in a star schema,
analyzes pricing behavior in Python, and surfaces findings in a Power BI
dashboard.

**Business question it answers:** *Where is pricing drifting, which
products and categories see the most discounting, and where do we have
availability problems?*

---

## Why this project

Built to demonstrate the end-to-end analyst workflow on a **live data
source**, not a static CSV:

- **Master data & SKU modeling** — a clean product hierarchy
  (category → subcategory → SKU) with brands and list prices.
- **A real pipeline** — scheduled ingestion with idempotency and
  error handling, so re-runs never duplicate data and a source failure
  never corrupts a partial load.
- **Analyst-grade analysis** — price volatility, promo intensity,
  availability, and trend, each tied to a business question.
- **Stakeholder communication** — a one-page findings summary and a
  Power BI dashboard, not just code.

---

## Architecture

```
  Source (simulated daily prices, or real product API)
        │
        ▼
  ingest.py  ──► idempotent INSERT (one row per product per day)
        │
        ▼
  SQLite / Postgres  (star schema: fact_price_history + dimensions)
        │
        ▼
  analyze.py  ──► clean CSV exports
        │
        ▼
  Power BI dashboard  +  Excel summary  +  one-page findings
```

Scheduling is handled by **GitHub Actions** (cloud, always-on) or
**Task Scheduler / cron** (laptop).

---

## Project structure

```
price-tracker/
├── database/
│   ├── schema.sql          # star schema (Postgres-flavored, with SQLite notes)
│   └── tracker.db          # the SQLite database (created by setup_db.py)
├── ingestion/
│   ├── seed_catalog.py     # builds the golf product catalog (master data)
│   ├── setup_db.py         # creates DB, loads dimensions  (run once)
│   ├── ingest.py           # daily price snapshot  (run on schedule)
│   └── catalog.csv         # generated catalog
├── analysis/
│   ├── queries.sql         # the business questions in SQL
│   └── analyze.py          # analyses + Power BI exports
├── powerbi/                # CSV exports the dashboard connects to
└── docs/
    └── findings.md         # one-page stakeholder summary
```

---

## How to run it

```bash
# 1. Build the product catalog (master data)
cd ingestion
python seed_catalog.py

# 2. Create the database and load dimensions (once)
python setup_db.py

# 3. Capture a daily snapshot (this is the scheduled job)
python ingest.py                 # today
python ingest.py 2026-06-25      # or backfill a specific date

# 4. Run the analysis and export for Power BI
cd ../analysis
python analyze.py
```

To make it live, schedule step 3:
- **Cloud (recommended):** commit `.github/workflows/daily-ingest.yml`
  (provided) — runs daily on GitHub's servers, free.
- **Laptop:** point Windows Task Scheduler (or cron) at `ingest.py`.

---

## Switching from simulated to a real API

`ingest.py` has two modes. Set `SOURCE_MODE = "api"` and implement
`get_prices_api()` against a real provider (Best Buy / eBay developer
APIs both have free tiers and real product/pricing data). The return
shape is documented in the function. Everything downstream — schema,
analysis, dashboard — stays the same.

The simulation is the default so the project **always works when you
demo it**, which matters for a portfolio piece.

---

## Talking points for interviews

- **Idempotency:** the `(product_id, date_id)` unique key plus
  `ON CONFLICT DO NOTHING` means the job is safe to re-run — no
  duplicate snapshots. (This is the question that separates people who
  have built a pipeline from people who haven't.)
- **Star schema:** why a fact table + dimensions, and how it maps to
  how reporting tools and BI tools expect data.
- **Master data:** the SKU hierarchy and pricing structure — the same
  thinking product-information/pricing roles screen for.
- **Stakeholder framing:** lead with findings and recommendations
  (see `docs/findings.md`), methods underneath.
```
