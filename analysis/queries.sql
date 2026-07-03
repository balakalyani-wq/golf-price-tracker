-- =============================================================
-- Analysis queries — the business questions, answered in SQL.
-- These are the queries you walk an interviewer through, and the
-- basis for the Power BI measures. Each maps to a real question a
-- pricing/product analyst would be asked.
-- =============================================================

-- Q1. Current price snapshot per product (latest observation)
--     "What does our catalog look like right now?"
SELECT p.sku, p.product_name, b.brand_name, c.category, c.subcategory,
       f.price, f.in_stock, f.on_sale, f.date_id
FROM fact_price_history f
JOIN dim_product  p ON f.product_id = p.product_id
JOIN dim_brand    b ON p.brand_id   = b.brand_id
JOIN dim_category c ON p.category_id = c.category_id
WHERE f.date_id = (SELECT MAX(date_id) FROM fact_price_history)
ORDER BY c.category, f.price DESC;

-- Q2. Biggest price movers over the tracked window
--     "Which products changed price the most?" (window function)
WITH price_window AS (
    SELECT p.sku, p.product_name,
           FIRST_VALUE(f.price) OVER (PARTITION BY f.product_id ORDER BY f.date_id) AS first_price,
           FIRST_VALUE(f.price) OVER (PARTITION BY f.product_id ORDER BY f.date_id DESC) AS last_price
    FROM fact_price_history f
    JOIN dim_product p ON f.product_id = p.product_id
)
SELECT DISTINCT sku, product_name, first_price, last_price,
       ROUND(last_price - first_price, 2) AS abs_change,
       ROUND(100.0 * (last_price - first_price) / first_price, 1) AS pct_change
FROM price_window
ORDER BY ABS(last_price - first_price) DESC
LIMIT 15;

-- Q3. Average price and promo frequency by category
--     "Where is discounting concentrated?"
SELECT c.category, c.subcategory,
       COUNT(DISTINCT p.product_id) AS n_products,
       ROUND(AVG(f.price), 2)       AS avg_price,
       ROUND(100.0 * AVG(f.on_sale), 1) AS pct_observations_on_sale
FROM fact_price_history f
JOIN dim_product  p ON f.product_id = p.product_id
JOIN dim_category c ON p.category_id = c.category_id
GROUP BY c.category, c.subcategory
ORDER BY pct_observations_on_sale DESC;

-- Q4. Stock-out rate by brand
--     "Which brands have the worst availability?"
SELECT b.brand_name,
       ROUND(100.0 * (1 - AVG(f.in_stock)), 1) AS stockout_rate_pct,
       COUNT(*) AS observations
FROM fact_price_history f
JOIN dim_product p ON f.product_id = p.product_id
JOIN dim_brand   b ON p.brand_id   = b.brand_id
GROUP BY b.brand_name
ORDER BY stockout_rate_pct DESC;

-- Q5. Daily average catalog price trend (the time series for the dashboard)
--     "Is our overall pricing drifting up or down?"
SELECT f.date_id,
       ROUND(AVG(f.price), 2)            AS avg_price,
       ROUND(100.0 * AVG(f.on_sale), 1)  AS pct_on_sale
FROM fact_price_history f
GROUP BY f.date_id
ORDER BY f.date_id;
