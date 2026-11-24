-- Lifelong snapshot versus weeks that start on or after 2025-10-27.
-- The week of 2025-10-20 is excluded here because it overlaps the snapshot
-- through 2025-10-25. Lifelong dollars are not added to weekly dollars.
-- Grain is page id plus the exact disclaimer string. "facebook, inc." and
-- "facebook inc." do not collapse.
--
-- Keys are a UNION of the two aggregates, then left joins. A FULL OUTER JOIN
-- of these aggregates makes SQLite build the lookup in a way that does not
-- finish on this file.

WITH life AS (
    SELECT page_id,
           disclaimer,
           SUM(amount_spent_usd) AS lifelong_spend_usd
    FROM advertisers
    WHERE window = 'lifelong'
    GROUP BY page_id, disclaimer
),
post AS (
    SELECT page_id,
           disclaimer,
           SUM(amount_spent_usd) AS post_spend_usd
    FROM advertisers
    WHERE window = 'last_7_days'
      AND date_start >= '2025-10-27'
    GROUP BY page_id, disclaimer
),
keys AS (
    SELECT page_id, disclaimer FROM life
    UNION
    SELECT page_id, disclaimer FROM post
),
joined AS (
    SELECT COALESCE(life.lifelong_spend_usd, 0) AS lifelong_spend_usd,
           COALESCE(post.post_spend_usd, 0) AS post_spend_usd
    FROM keys
    LEFT JOIN life
        ON life.page_id = keys.page_id
       AND life.disclaimer = keys.disclaimer
    LEFT JOIN post
        ON post.page_id = keys.page_id
       AND post.disclaimer = keys.disclaimer
)
SELECT COUNT(*) AS pairs,
       SUM(lifelong_spend_usd) AS lifelong_spend_usd,
       SUM(post_spend_usd) AS post_spend_usd,
       SUM(CASE WHEN lifelong_spend_usd > 0 THEN 1 ELSE 0 END) AS pairs_with_lifelong_spend,
       SUM(CASE WHEN post_spend_usd > 0 AND lifelong_spend_usd = 0 THEN 1 ELSE 0 END)
           AS new_pairs,
       SUM(CASE WHEN post_spend_usd > 0 AND lifelong_spend_usd = 0 THEN post_spend_usd ELSE 0 END)
           AS new_pair_spend,
       SUM(CASE WHEN lifelong_spend_usd > 0 AND post_spend_usd = 0 THEN lifelong_spend_usd ELSE 0 END)
           AS lifelong_spend_with_no_post_activity
FROM joined;
