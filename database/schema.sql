-- =============================================================
-- Golf Equipment Price Tracker — Database Schema
-- Star schema: a price-history fact table surrounded by
-- product, brand, category, and date dimensions.
--
-- Written for PostgreSQL. For SQLite, see notes at the bottom.
-- =============================================================

-- ---------- DIMENSION: brand ----------
CREATE TABLE IF NOT EXISTS dim_brand (
    brand_id      SERIAL PRIMARY KEY,
    brand_name    TEXT NOT NULL UNIQUE
);

-- ---------- DIMENSION: category (the SKU hierarchy lives here) ----------
-- category -> subcategory mirrors how product master data is
-- organized in systems like SAP. This is your master-data talking point.
CREATE TABLE IF NOT EXISTS dim_category (
    category_id    SERIAL PRIMARY KEY,
    category       TEXT NOT NULL,   -- e.g. 'Clubs', 'Balls', 'Apparel'
    subcategory    TEXT NOT NULL,   -- e.g. 'Drivers', 'Irons', 'Putters'
    UNIQUE (category, subcategory)
);

-- ---------- DIMENSION: product (one row per SKU) ----------
CREATE TABLE IF NOT EXISTS dim_product (
    product_id     SERIAL PRIMARY KEY,
    sku            TEXT NOT NULL UNIQUE,   -- natural/business key from the source
    product_name   TEXT NOT NULL,
    brand_id       INTEGER NOT NULL REFERENCES dim_brand(brand_id),
    category_id    INTEGER NOT NULL REFERENCES dim_category(category_id),
    list_price     NUMERIC(10,2),          -- manufacturer list / reference price
    first_seen     DATE NOT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------- DIMENSION: date ----------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id        DATE PRIMARY KEY,
    day            INTEGER NOT NULL,
    month          INTEGER NOT NULL,
    month_name     TEXT NOT NULL,
    quarter        INTEGER NOT NULL,
    year           INTEGER NOT NULL,
    day_of_week    TEXT NOT NULL,
    is_weekend     BOOLEAN NOT NULL
);

-- ---------- FACT: price observations ----------
-- One row per (product, day) snapshot. This is what the
-- ingestion script appends to on every run.
CREATE TABLE IF NOT EXISTS fact_price_history (
    price_obs_id   BIGSERIAL PRIMARY KEY,
    product_id     INTEGER NOT NULL REFERENCES dim_product(product_id),
    date_id        DATE NOT NULL REFERENCES dim_date(date_id),
    price          NUMERIC(10,2) NOT NULL,
    in_stock       BOOLEAN NOT NULL,
    on_sale        BOOLEAN NOT NULL DEFAULT FALSE,
    -- IDEMPOTENCY KEY: one observation per product per day.
    -- Re-running the ingestion for the same day will not create
    -- duplicates because of this unique constraint + ON CONFLICT.
    UNIQUE (product_id, date_id)
);

-- ---------- Helpful indexes for analysis queries ----------
CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_date    ON fact_price_history(date_id);

-- =============================================================
-- SQLite notes (if you choose SQLite instead of Postgres):
--   * Replace SERIAL / BIGSERIAL with INTEGER PRIMARY KEY AUTOINCREMENT
--   * Replace NUMERIC(10,2) with REAL
--   * Replace BOOLEAN with INTEGER (0/1)
--   * Replace TEXT (fine as-is)
--   * ON CONFLICT works in modern SQLite the same way
-- =============================================================
