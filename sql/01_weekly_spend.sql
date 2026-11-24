-- Observed weekly spend from the advertiser file.
-- Each row is one Monday–Sunday last_7_days window. The three missing
-- November weeks are absent. Do not treat a missing week as zero, and do
-- not add the lifelong snapshot to this total.
-- num_ads is a sum of weekly ad counts (ad-weeks), not a count of distinct ads.

SELECT date_start,
       date_end,
       SUM(amount_spent_usd) AS spend_usd,
       SUM(num_ads) AS num_ads,
       COUNT(*) AS advertiser_rows,
       SUM(CASE WHEN amount_spent_usd > 0 THEN 1 ELSE 0 END) AS positive_rows,
       SUM(CASE WHEN amount_spent_usd = 0 THEN num_ads ELSE 0 END) AS zero_row_ads
FROM advertisers
WHERE window = 'last_7_days'
GROUP BY date_start, date_end
ORDER BY date_start;
