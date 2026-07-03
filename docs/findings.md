# Pricing & Availability — Findings Summary

*Golf equipment catalog · 120 SKUs · 30-day tracking window*
*(Template — numbers refresh automatically as the pipeline collects more data.)*

---

## Headline

Catalog pricing has been **broadly stable** over the tracked window
(average list ≈ flat, +0.9%), but discounting and availability vary
sharply by category and brand — pointing to a few specific, actionable
levers.

---

## Key findings & recommendations

**1. Discounting is concentrated in Fairway Woods (~28% of observations on sale).**
This subcategory is promoted far more heavily than the catalog average.
*Recommendation:* confirm this is intentional clearance vs. a margin
leak; if unintentional, tighten promo rules on this line.

**2. Mizuno shows the highest stock-out rate (~6%).**
Availability gaps cost sales and erode buyer trust.
*Recommendation:* review replenishment cadence with this brand; flag
SKUs that repeatedly go out of stock.

**3. Fairway Woods are also the most price-volatile products.**
High volatility + high promo frequency in the same subcategory suggests
inconsistent pricing discipline rather than a deliberate strategy.
*Recommendation:* set price floors/guardrails for the most volatile SKUs.

**4. Overall catalog pricing is stable — no systemic drift.**
The aggregate trend is essentially flat, so issues are
**category-specific, not catalog-wide** — meaning targeted fixes, not a
broad repricing.

---

## How to read this

Each finding is backed by a chart in the Power BI dashboard:
catalog price trend, promo intensity by category, stock-out rate by
brand, and per-SKU volatility. The dashboard refreshes as the pipeline
adds each day's snapshot.

---

## Method (one line)

Daily price + availability snapshots are captured by a scheduled
pipeline into a star-schema database; Python computes volatility, promo
intensity, and availability; results surface in Power BI. Full
reproducibility in the README.
