-- Weekly spend in calendar order, advertiser file, observed weeks only.
-- The minimum and maximum are the lowest and highest observed weeks.
-- They are not interpolated across the missing November weeks.

WITH weekly AS (
    SELECT date_start,
           date_end,
           SUM(amount_spent_usd) AS spend_usd
    FROM advertisers
    WHERE window = 'last_7_days'
    GROUP BY date_start, date_end
)
SELECT date_start,
       date_end,
       spend_usd,
       SUM(spend_usd) OVER () AS period_spend,
       MIN(spend_usd) OVER () AS min_spend,
       MAX(spend_usd) OVER () AS max_spend
FROM weekly
ORDER BY date_start;
