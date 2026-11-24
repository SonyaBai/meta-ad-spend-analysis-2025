-- Spend concentration among page-and-disclaimer pairs with positive weekly spend.
-- Rank is spend descending, then page_id, then disclaimer.
-- The top 1% is the first ceil(n / 100) rows, computed as integer (n + 99) / 100.
-- n_for_50 and n_for_80 are the smallest ranks whose cumulative spend reaches
-- 50% and 80% of positive-spend dollars. The comparison is integer:
-- cumulative * 2 >= total, and cumulative * 5 >= total * 4.

WITH advertiser AS (
    SELECT page_id,
           disclaimer,
           SUM(amount_spent_usd) AS spend_usd
    FROM advertisers
    WHERE window = 'last_7_days'
    GROUP BY page_id, disclaimer
    HAVING SUM(amount_spent_usd) > 0
),
ranked AS (
    SELECT spend_usd,
           SUM(spend_usd) OVER () AS total_spend,
           COUNT(*) OVER () AS n_advertisers,
           ROW_NUMBER() OVER (
               ORDER BY spend_usd DESC, page_id, disclaimer
           ) AS rk
    FROM advertiser
),
marked AS (
    SELECT spend_usd,
           total_spend,
           n_advertisers,
           rk,
           (n_advertisers + 99) / 100 AS top_1pct_n,
           SUM(spend_usd) OVER (ORDER BY rk) AS cumulative_spend
    FROM ranked
)
SELECT MAX(n_advertisers) AS n_advertisers,
       MAX(total_spend) AS total_spend,
       MAX(top_1pct_n) AS top_1pct_n,
       SUM(CASE WHEN rk <= 10 THEN spend_usd ELSE 0 END) AS top10_spend,
       SUM(CASE WHEN rk <= top_1pct_n THEN spend_usd ELSE 0 END) AS top1pct_spend,
       MIN(CASE WHEN cumulative_spend * 2 >= total_spend THEN rk END) AS n_for_50,
       MIN(CASE WHEN cumulative_spend * 5 >= total_spend * 4 THEN rk END) AS n_for_80
FROM marked;
