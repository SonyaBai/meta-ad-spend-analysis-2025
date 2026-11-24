-- Largest lifelong page-and-disclaimer pairs, with spend in the weeks that
-- start on or after 2025-10-27.
-- page_post_snapshot_spend_usd sums every disclaimer on the same page, so a
-- new committee on an old page is visible next to the historical disclaimer.
-- The top 15 are chosen before the name and recent-spend lookups.

WITH life AS (
    SELECT page_id,
           disclaimer,
           SUM(amount_spent_usd) AS lifelong_spend_usd
    FROM advertisers
    WHERE window = 'lifelong'
    GROUP BY page_id, disclaimer
),
top AS (
    SELECT page_id,
           disclaimer,
           lifelong_spend_usd
    FROM life
    ORDER BY lifelong_spend_usd DESC, page_id, disclaimer
    LIMIT 15
),
names AS (
    SELECT page_id,
           disclaimer,
           page_name,
           SUM(amount_spent_usd) AS name_spend
    FROM advertisers
    WHERE window = 'lifelong'
      AND (page_id, disclaimer) IN (SELECT page_id, disclaimer FROM top)
    GROUP BY page_id, disclaimer, page_name
),
best AS (
    SELECT page_id, disclaimer, page_name
    FROM (
        SELECT page_id,
               disclaimer,
               page_name,
               ROW_NUMBER() OVER (
                   PARTITION BY page_id, disclaimer
                   ORDER BY name_spend DESC, page_name
               ) AS rk
        FROM names
    )
    WHERE rk = 1
),
post_pair AS (
    SELECT page_id,
           disclaimer,
           SUM(amount_spent_usd) AS post_snapshot_spend_usd
    FROM advertisers
    WHERE window = 'last_7_days'
      AND date_start >= '2025-10-27'
      AND (page_id, disclaimer) IN (SELECT page_id, disclaimer FROM top)
    GROUP BY page_id, disclaimer
),
post_page AS (
    SELECT page_id,
           SUM(amount_spent_usd) AS page_post_snapshot_spend_usd
    FROM advertisers
    WHERE window = 'last_7_days'
      AND date_start >= '2025-10-27'
      AND page_id IN (SELECT page_id FROM top)
    GROUP BY page_id
)
SELECT best.page_name,
       top.disclaimer,
       top.lifelong_spend_usd,
       COALESCE(post_pair.post_snapshot_spend_usd, 0) AS post_snapshot_spend_usd,
       COALESCE(post_page.page_post_snapshot_spend_usd, 0) AS page_post_snapshot_spend_usd
FROM top
JOIN best
    ON best.page_id = top.page_id
   AND best.disclaimer = top.disclaimer
LEFT JOIN post_pair
    ON post_pair.page_id = top.page_id
   AND post_pair.disclaimer = top.disclaimer
LEFT JOIN post_page
    ON post_page.page_id = top.page_id
ORDER BY top.lifelong_spend_usd DESC, top.page_id, top.disclaimer;
