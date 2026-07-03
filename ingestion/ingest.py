"""
ingest.py
----------
The heart of the "live" pipeline. Runs on a schedule, captures a daily
price + availability snapshot for every product, and appends to the
fact table — WITHOUT creating duplicates if it runs twice.

Two modes, controlled by SOURCE_MODE:
  * "simulate"  -> generates realistic daily price movements. Always works,
                   never breaks, perfect for a portfolio you must demo reliably.
  * "api"       -> a stub showing exactly where a real API call slots in.
                   Swap in Best Buy / eBay developer API here when ready.

The two things that make this a REAL pipeline (and the things interviewers
care about) are both handled here:
  1. IDEMPOTENCY  — re-running for the same day won't duplicate rows
                    (ON CONFLICT on the (product_id, date_id) unique key).
  2. ERROR HANDLING — API/db failures are caught, logged, and don't
                    corrupt a partial run.

Usage:
    python ingest.py                 # uses today's date
    python ingest.py 2026-06-25      # backfill a specific date
"""

import csv
import os
import random
import sqlite3
import sys
from datetime import date, datetime

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
SOURCE_MODE = "simulate"          # "simulate", "bestbuy", or "api"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "tracker.db")
CATALOG_CSV = os.path.join(os.path.dirname(__file__), "catalog.csv")


# ----------------------------------------------------------------------
# SOURCE: simulate  — generates a believable daily snapshot
# ----------------------------------------------------------------------
def get_prices_simulated(products, run_date):
    """
    Produce a price observation per product for run_date.
    Prices drift slightly day to day; items occasionally go on sale
    or out of stock — enough variation to make the analysis interesting.
    """
    seed = int(run_date.strftime("%Y%m%d"))
    rng = random.Random(seed)  # deterministic per-day, so backfills are stable

    observations = []
    for p in products:
        list_price = float(p["list_price"])
        # daily drift: +/- a few percent around list price
        drift = rng.uniform(-0.06, 0.04)
        on_sale = rng.random() < 0.15          # 15% chance of a promo
        sale_cut = rng.uniform(0.10, 0.30) if on_sale else 0.0
        price = round(list_price * (1 + drift) * (1 - sale_cut), 2)
        in_stock = rng.random() > 0.05         # 95% in stock
        observations.append({
            "sku": p["sku"],
            "price": price,
            "in_stock": in_stock,
            "on_sale": on_sale,
        })
    return observations


# ----------------------------------------------------------------------
# SOURCE: api  — STUB. This is where a real product API plugs in.
# ----------------------------------------------------------------------
def get_prices_api(products, run_date):
    """
    Replace the body of this function with a real API call. The shape of
    the returned list must match get_prices_simulated above.

    Example (pseudo-code) for a real provider:

        import requests
        out = []
        for p in products:
            r = requests.get(
                "https://api.provider.com/v1/products",
                params={"sku": p["sku"]},
                headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            out.append({
                "sku": p["sku"],
                "price": data["price"],
                "in_stock": data["availability"] == "InStock",
                "on_sale": data.get("onSale", False),
            })
        return out

    Note: real APIs rate-limit. Add time.sleep() between calls, batch
    where the API allows it, and catch per-item failures so one bad
    response doesn't kill the whole run.
    """
    raise NotImplementedError(
        "API mode is a stub. Set SOURCE_MODE='simulate', or implement "
        "get_prices_api() against your chosen provider."
    )


# ----------------------------------------------------------------------
# DB helpers
# ----------------------------------------------------------------------
def get_connection():
    return sqlite3.connect(DB_PATH)


def ensure_date_row(cur, run_date):
    """Insert the dim_date row for run_date if it isn't there yet."""
    cur.execute("SELECT 1 FROM dim_date WHERE date_id = ?", (run_date.isoformat(),))
    if cur.fetchone() is None:
        cur.execute(
            """INSERT INTO dim_date
               (date_id, day, month, month_name, quarter, year, day_of_week, is_weekend)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                run_date.isoformat(),
                run_date.day,
                run_date.month,
                run_date.strftime("%B"),
                (run_date.month - 1) // 3 + 1,
                run_date.year,
                run_date.strftime("%A"),
                1 if run_date.weekday() >= 5 else 0,
            ),
        )


def sku_to_product_id(cur):
    cur.execute("SELECT sku, product_id FROM dim_product")
    return {sku: pid for sku, pid in cur.fetchall()}


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def run(run_date):
    print(f"[{datetime.now():%H:%M:%S}] Ingestion start — mode={SOURCE_MODE}, date={run_date}")

    # Load the catalog (master data)
    try:
        with open(CATALOG_CSV) as f:
            products = list(csv.DictReader(f))
    except FileNotFoundError:
        print("ERROR: catalog.csv not found. Run seed_catalog.py first.")
        return 1

    # Fetch the day's prices from the chosen source, with error handling
    try:
        if SOURCE_MODE == "simulate":
            observations = get_prices_simulated(products, run_date)
        elif SOURCE_MODE == "bestbuy":
            # Real external data from the Best Buy Developer API.
            from bestbuy_api import get_prices_bestbuy
            observations = get_prices_bestbuy(products, run_date)
        elif SOURCE_MODE == "api":
            observations = get_prices_api(products, run_date)
        else:
            print(f"ERROR: unknown SOURCE_MODE '{SOURCE_MODE}'")
            return 1
    except Exception as e:
        # A source failure should fail loudly but cleanly — never write
        # a half-baked snapshot.
        print(f"ERROR fetching prices: {e}")
        return 1

    # Write to the DB inside a transaction
    conn = get_connection()
    try:
        cur = conn.cursor()
        ensure_date_row(cur, run_date)
        pid_map = sku_to_product_id(cur)

        inserted, skipped = 0, 0
        for obs in observations:
            pid = pid_map.get(obs["sku"])
            if pid is None:
                skipped += 1
                continue
            # IDEMPOTENT INSERT: if a row for (product, date) already
            # exists, do nothing. Re-running the job is safe.
            cur.execute(
                """INSERT INTO fact_price_history
                   (product_id, date_id, price, in_stock, on_sale)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(product_id, date_id) DO NOTHING""",
                (pid, run_date.isoformat(), obs["price"],
                 1 if obs["in_stock"] else 0,
                 1 if obs["on_sale"] else 0),
            )
            inserted += cur.rowcount

        conn.commit()
        print(f"[{datetime.now():%H:%M:%S}] Done — {inserted} new rows, "
              f"{skipped} unknown SKUs skipped.")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"ERROR writing to DB (rolled back): {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        run_date = date.today()
    sys.exit(run(run_date))
