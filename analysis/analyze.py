"""
analyze.py
-----------
Reads the price history from the database, runs the analyst-grade
analyses, prints findings, and exports clean CSVs that Power BI / Excel
connect to.

Analyses:
  1. Price volatility per product (which SKUs are most/least stable)
  2. Promo intensity by category
  3. Availability (stock-out) by brand
  4. Daily catalog price trend (time series)
  5. A flat "powerbi_export.csv" — the denormalized table the dashboard uses

Run after you have some days of history:
    python analyze.py
"""

import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "tracker.db")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "powerbi")


def load_frame(conn):
    """Denormalized fact+dimensions — the analyst's working table."""
    q = """
    SELECT f.date_id, f.price, f.in_stock, f.on_sale,
           p.sku, p.product_name, p.list_price,
           b.brand_name, c.category, c.subcategory
    FROM fact_price_history f
    JOIN dim_product  p ON f.product_id = p.product_id
    JOIN dim_brand    b ON p.brand_id   = b.brand_id
    JOIN dim_category c ON p.category_id = c.category_id
    """
    df = pd.read_csv("/dev/stdin") if False else pd.read_sql_query(q, conn)
    df["date_id"] = pd.to_datetime(df["date_id"])
    return df


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    df = load_frame(conn)
    conn.close()

    print(f"Loaded {len(df):,} price observations across "
          f"{df['sku'].nunique()} products and "
          f"{df['date_id'].nunique()} days.\n")

    # 1. Price volatility per product
    vol = (df.groupby(["sku", "product_name"])["price"]
             .agg(["mean", "std", "min", "max"])
             .reset_index())
    vol["volatility_pct"] = (vol["std"] / vol["mean"] * 100).round(1)
    vol = vol.sort_values("volatility_pct", ascending=False)
    print("Most volatile products (top 5):")
    print(vol.head(5)[["product_name", "mean", "volatility_pct"]].to_string(index=False))
    print()

    # 2. Promo intensity by category
    promo = (df.groupby(["category", "subcategory"])["on_sale"]
               .mean().mul(100).round(1)
               .reset_index(name="pct_on_sale")
               .sort_values("pct_on_sale", ascending=False))
    print("Categories with most discounting (top 5):")
    print(promo.head(5).to_string(index=False))
    print()

    # 3. Stock-out rate by brand
    stock = (df.groupby("brand_name")["in_stock"]
               .apply(lambda s: round((1 - s.mean()) * 100, 1))
               .reset_index(name="stockout_rate_pct")
               .sort_values("stockout_rate_pct", ascending=False))
    print("Stock-out rate by brand (top 5):")
    print(stock.head(5).to_string(index=False))
    print()

    # 4. Daily catalog price trend
    trend = (df.groupby("date_id")
               .agg(avg_price=("price", "mean"),
                    pct_on_sale=("on_sale", lambda s: s.mean() * 100))
               .round(2).reset_index())
    print("Price trend (first & last day):")
    print(trend.iloc[[0, -1]].to_string(index=False))
    print()

    # 5. Exports for Power BI / Excel
    df.to_csv(os.path.join(OUT_DIR, "powerbi_export.csv"), index=False)
    vol.to_csv(os.path.join(OUT_DIR, "volatility.csv"), index=False)
    promo.to_csv(os.path.join(OUT_DIR, "promo_by_category.csv"), index=False)
    stock.to_csv(os.path.join(OUT_DIR, "stockout_by_brand.csv"), index=False)
    trend.to_csv(os.path.join(OUT_DIR, "price_trend.csv"), index=False)
    print(f"Exports written to {os.path.abspath(OUT_DIR)}/")


if __name__ == "__main__":
    main()
