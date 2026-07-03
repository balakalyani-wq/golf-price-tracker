"""
setup_db.py
------------
One-time setup. Creates the SQLite database, applies the schema
(adapted from schema.sql), and loads catalog.csv into the dimension
tables (dim_brand, dim_category, dim_product).

After this runs, the DB is ready and you just call ingest.py daily.

Usage:
    python setup_db.py
"""

import csv
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "tracker.db")
CATALOG_CSV = os.path.join(os.path.dirname(__file__), "..", "ingestion", "catalog.csv")

# SQLite-flavored schema (BOOLEAN->INTEGER, NUMERIC->REAL, SERIAL->AUTOINCREMENT)
SCHEMA = """
CREATE TABLE IF NOT EXISTS dim_brand (
    brand_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name  TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS dim_category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    UNIQUE (category, subcategory)
);
CREATE TABLE IF NOT EXISTS dim_product (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    brand_id     INTEGER NOT NULL REFERENCES dim_brand(brand_id),
    category_id  INTEGER NOT NULL REFERENCES dim_category(category_id),
    list_price   REAL,
    first_seen   TEXT NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS dim_date (
    date_id     TEXT PRIMARY KEY,
    day         INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT NOT NULL,
    quarter     INTEGER NOT NULL,
    year        INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_price_history (
    price_obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL REFERENCES dim_product(product_id),
    date_id      TEXT NOT NULL REFERENCES dim_date(date_id),
    price        REAL NOT NULL,
    in_stock     INTEGER NOT NULL,
    on_sale      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (product_id, date_id)
);
CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_date    ON fact_price_history(date_id);
"""


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    with open(CATALOG_CSV) as f:
        products = list(csv.DictReader(f))

    for p in products:
        # brand
        cur.execute("INSERT OR IGNORE INTO dim_brand (brand_name) VALUES (?)", (p["brand"],))
        cur.execute("SELECT brand_id FROM dim_brand WHERE brand_name = ?", (p["brand"],))
        brand_id = cur.fetchone()[0]
        # category
        cur.execute("INSERT OR IGNORE INTO dim_category (category, subcategory) VALUES (?,?)",
                    (p["category"], p["subcategory"]))
        cur.execute("SELECT category_id FROM dim_category WHERE category=? AND subcategory=?",
                    (p["category"], p["subcategory"]))
        category_id = cur.fetchone()[0]
        # product
        cur.execute(
            """INSERT OR IGNORE INTO dim_product
               (sku, product_name, brand_id, category_id, list_price, first_seen)
               VALUES (?,?,?,?,?,?)""",
            (p["sku"], p["product_name"], brand_id, category_id,
             float(p["list_price"]), p["first_seen"]),
        )

    conn.commit()
    # report
    for t in ["dim_brand", "dim_category", "dim_product"]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t:15s}: {cur.fetchone()[0]} rows")
    conn.close()
    print(f"\nDatabase ready at {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    main()
