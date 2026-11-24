-- Largest page-and-disclaimer pairs by observed weekly spend.
-- Requires classified_weekly, which python analysis.py fills after the load.
-- The category is the keyword rule in src/classify.py, not a Meta field.

SELECT page_name,
       disclaimer,
       category,
       spend_usd,
       num_ads,
       weeks_observed,
       post_snapshot_spend_usd,
       lifelong_spend_usd,
       page_lifelong_spend_usd
FROM classified_weekly
ORDER BY spend_usd DESC, page_id, disclaimer
LIMIT 25;
