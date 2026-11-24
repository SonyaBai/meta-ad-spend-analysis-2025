-- Spend and ad-weeks by the keyword category on classified_weekly.
-- python analysis.py assigns category from the page name and the disclaimer
-- (src/classify.py) and reloads this table. Pairs with zero weekly spend are
-- included in advertisers and excluded from spend, which is already zero.

SELECT category,
       COUNT(*) AS advertisers,
       SUM(CASE WHEN spend_usd > 0 THEN 1 ELSE 0 END) AS positive_advertisers,
       SUM(spend_usd) AS spend_usd,
       SUM(num_ads) AS num_ads
FROM classified_weekly
GROUP BY category
ORDER BY spend_usd DESC, category;
