"""
bestbuy_api.py
---------------
Real product data from the Best Buy Developer API (free with a key).

This replaces the SIMULATION with a genuine external source. It does two jobs:

  1. seed_catalog_from_api()  -> fetches real sporting-goods products and
                                 writes catalog.csv (run once, like seed_catalog.py)
  2. get_prices_bestbuy()     -> fetches TODAY's real price + availability for
                                 the catalog SKUs (called by ingest.py each day)

------------------------------------------------------------------
GETTING A KEY (one-time, ~5 min, free):
  1. Go to https://developer.bestbuy.com and create a developer account.
     IMPORTANT: Best Buy does NOT issue keys to free email addresses
     (gmail/yahoo/etc.). Use a .edu address (your CMU one is ideal) or
     another non-free address. Activate via the email they send.
  2. Copy your API key.
  3. Set it as an environment variable so it's never hard-coded:
       Windows (PowerShell):  $env:BESTBUY_API_KEY="your_key_here"
       macOS/Linux:           export BESTBUY_API_KEY="your_key_here"
     For GitHub Actions, add it as a repository Secret named BESTBUY_API_KEY.
------------------------------------------------------------------

Best Buy product attributes used (all real):
  sku        -> their product SKU (our natural key)
  name       -> product name
  salePrice  -> current selling price          (our "price")
  regularPrice -> list price                    (our "list_price")
  onSale     -> boolean promo flag              (our "on_sale")
  inStoreAvailability / onlineAvailability -> availability (our "in_stock")
  manufacturer -> brand
"""

import csv
import os
import time
import requests

API_KEY = os.environ.get("BESTBUY_API_KEY", "")
BASE = "https://api.bestbuy.com/v1"

# Best Buy category IDs for sporting goods / fitness keep the project
# on-theme. "Sports & Fitness" sits under pcmcat columns; we search by
# keyword + category to stay close to the golf/sporting-goods story.
SEARCH_TERMS = ["golf", "fitness tracker", "treadmill", "exercise bike",
                "sports watch", "golf simulator"]

REQUEST_PAUSE = 0.3   # be polite; Best Buy free tier is ~5 req/sec, 50k/day


def _require_key():
    if not API_KEY:
        raise RuntimeError(
            "BESTBUY_API_KEY is not set. Get a key at developer.bestbuy.com "
            "and export it (see header of this file)."
        )


# ----------------------------------------------------------------------
# 1. SEED CATALOG from real Best Buy products
# ----------------------------------------------------------------------
def seed_catalog_from_api(out_path="catalog.csv", per_term=20):
    """
    Pull real products for each search term and write catalog.csv with the
    SAME columns the rest of the pipeline expects:
        sku, product_name, brand, category, subcategory, list_price, first_seen
    """
    _require_key()
    from datetime import date
    rows, seen = [], set()

    for term in SEARCH_TERMS:
        url = f"{BASE}/products(search={term})"
        params = {
            "apiKey": API_KEY,
            "format": "json",
            "show": "sku,name,salePrice,regularPrice,manufacturer,categoryPath.name",
            "pageSize": per_term,
            "sort": "salePrice.dsc",
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  WARN: search '{term}' failed: {e}")
            continue

        for prod in data.get("products", []):
            sku = str(prod.get("sku"))
            if not sku or sku in seen or not prod.get("salePrice"):
                continue
            seen.add(sku)
            # categoryPath is a list of {name:...}; use last two levels as
            # category / subcategory to build the hierarchy.
            cats = [c["name"] for c in prod.get("categoryPath", []) if c.get("name")]
            category = cats[1] if len(cats) > 1 else (cats[0] if cats else "Sporting Goods")
            subcategory = cats[-1] if cats else term.title()
            rows.append({
                "sku": sku,
                "product_name": prod.get("name", "")[:120],
                "brand": prod.get("manufacturer") or "Unknown",
                "category": category,
                "subcategory": subcategory,
                "list_price": prod.get("regularPrice") or prod.get("salePrice"),
                "first_seen": date.today().isoformat(),
            })
        time.sleep(REQUEST_PAUSE)

    if not rows:
        print("No products returned. Check your key and try again.")
        return 0

    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} REAL Best Buy products to {out_path}")
    return len(rows)


# ----------------------------------------------------------------------
# 2. DAILY PRICE FETCH for catalog SKUs (called by ingest.py)
# ----------------------------------------------------------------------
def get_prices_bestbuy(products, run_date):
    """
    Fetch today's real price + availability for each catalog SKU.
    Returns the same shape the pipeline expects:
        [{sku, price, in_stock, on_sale}, ...]

    Per-item failures are caught so one bad SKU never kills the run.
    """
    _require_key()
    observations = []
    for p in products:
        sku = p["sku"]
        url = f"{BASE}/products(sku={sku})"
        params = {
            "apiKey": API_KEY,
            "format": "json",
            "show": "sku,salePrice,onSale,onlineAvailability",
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("products", [])
            if not items:
                continue
            prod = items[0]
            observations.append({
                "sku": sku,
                "price": prod.get("salePrice"),
                "in_stock": bool(prod.get("onlineAvailability", False)),
                "on_sale": bool(prod.get("onSale", False)),
            })
        except Exception as e:
            # log and move on — robustness over completeness
            print(f"  WARN: sku {sku} failed: {e}")
        time.sleep(REQUEST_PAUSE)
    return observations


# ----------------------------------------------------------------------
# Quick self-test:  python bestbuy_api.py
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing Best Buy API connection...")
    try:
        _require_key()
    except RuntimeError as e:
        print(e)
        raise SystemExit(1)

    # tiny smoke test: one search
    r = requests.get(
        f"{BASE}/products(search=golf)",
        params={"apiKey": API_KEY, "format": "json",
                "show": "sku,name,salePrice", "pageSize": 3},
        timeout=15,
    )
    if r.ok:
        prods = r.json().get("products", [])
        print(f"OK — got {len(prods)} sample products:")
        for p in prods:
            print(f"  [{p.get('sku')}] {p.get('name','')[:50]} — ${p.get('salePrice')}")
        print("\nKey works. Now run:  python bestbuy_api.py  then seed + ingest.")
    else:
        print(f"Request failed: {r.status_code} {r.text[:200]}")
