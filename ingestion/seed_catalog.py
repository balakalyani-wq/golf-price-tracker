"""
seed_catalog.py
----------------
Builds a realistic golf-equipment product catalog (the dimension data).

This is the "master data" layer — the SKUs, brands, categories, and
list prices that your price observations will reference. Building a
clean, hierarchical catalog yourself is exactly the master-data skill
the analyst role probes (SKU structure, pricing, categorization).

Run this ONCE to populate the dimension tables. The ingestion script
(ingest.py) then appends daily price observations against these SKUs.

Output: a catalog.csv you can inspect, plus direct DB insertion.
"""

import csv
import random
from datetime import date

random.seed(42)  # reproducible catalog

# ---- The category hierarchy (category -> subcategories) ----
HIERARCHY = {
    "Clubs":       ["Drivers", "Irons", "Putters", "Wedges", "Fairway Woods", "Hybrids"],
    "Balls":       ["Tour Balls", "Distance Balls", "Value Balls"],
    "Bags":        ["Cart Bags", "Stand Bags", "Travel Bags"],
    "Apparel":     ["Polos", "Outerwear", "Headwear", "Gloves"],
    "Accessories": ["Rangefinders", "Tees", "Towels", "Umbrellas"],
}

BRANDS = ["Titleist", "Callaway", "TaylorMade", "Ping", "Cobra",
          "Mizuno", "Srixon", "Cleveland", "Wilson", "Bridgestone"]

# Rough realistic price bands per subcategory (low, high)
PRICE_BANDS = {
    "Drivers": (350, 650), "Irons": (700, 1400), "Putters": (180, 450),
    "Wedges": (120, 200), "Fairway Woods": (250, 400), "Hybrids": (200, 320),
    "Tour Balls": (40, 55), "Distance Balls": (25, 35), "Value Balls": (15, 22),
    "Cart Bags": (200, 350), "Stand Bags": (180, 300), "Travel Bags": (120, 250),
    "Polos": (55, 95), "Outerwear": (90, 200), "Headwear": (25, 40), "Gloves": (18, 30),
    "Rangefinders": (200, 500), "Tees": (5, 12), "Towels": (15, 30), "Umbrellas": (30, 70),
}

def build_catalog(n_products=120):
    rows = []
    sku_counter = 1000
    for _ in range(n_products):
        category = random.choice(list(HIERARCHY.keys()))
        subcategory = random.choice(HIERARCHY[category])
        brand = random.choice(BRANDS)
        low, high = PRICE_BANDS[subcategory]
        list_price = round(random.uniform(low, high), 2)
        sku_counter += 1
        sku = f"GLF-{sku_counter}"
        product_name = f"{brand} {subcategory[:-1] if subcategory.endswith('s') else subcategory} {random.choice(['Pro','Tour','Max','ST','X','Elite'])}"
        rows.append({
            "sku": sku,
            "product_name": product_name,
            "brand": brand,
            "category": category,
            "subcategory": subcategory,
            "list_price": list_price,
            "first_seen": date.today().isoformat(),
        })
    return rows

if __name__ == "__main__":
    catalog = build_catalog()
    out = "catalog.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=catalog[0].keys())
        writer.writeheader()
        writer.writerows(catalog)
    print(f"Wrote {len(catalog)} products to {out}")
    # quick preview
    for r in catalog[:5]:
        print(r)
