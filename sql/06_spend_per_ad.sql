-- Inputs for average spend per ad-listing.
-- Summing num_ads across weeks counts an ad once per week it is reported.
-- The write-up divides these sums in Python and rounds half-up to the cent.
-- SQLite ROUND is not used, because it is not half-up.
--
-- zero_row_ads is the ad count on weekly rows whose reported spend is $0.
-- This file does not say whether that zero is a true zero or a threshold.

SELECT SUM(amount_spent_usd) AS spend_usd,
       SUM(num_ads) AS num_ads,
       SUM(CASE WHEN amount_spent_usd = 0 THEN 1 ELSE 0 END) AS zero_rows,
       SUM(CASE WHEN amount_spent_usd = 0 THEN num_ads ELSE 0 END) AS zero_row_ads,
       SUM(CASE WHEN amount_spent_usd > 0 THEN amount_spent_usd ELSE 0 END) AS positive_row_spend,
       SUM(CASE WHEN amount_spent_usd > 0 THEN num_ads ELSE 0 END) AS positive_row_ads,
       COUNT(*) AS advertiser_rows
FROM advertisers
WHERE window = 'last_7_days';
