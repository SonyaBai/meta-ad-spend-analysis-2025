-- One row per weekly page id and disclaimer.
-- Requires sql/stage_advertisers.sql on the same connection.
-- page_name is the weekly name with the most spend for that pair.
-- post_snapshot_* sums weeks that start on or after 2025-10-27.
-- A missing lifelong row is zero here, not unknown.

SELECT w.page_id,
       n.page_name,
       w.disclaimer,
       w.spend_usd,
       w.num_ads,
       w.weeks_observed,
       w.post_snapshot_spend_usd,
       w.post_snapshot_num_ads,
       COALESCE(life_pair.lifelong_spend_usd, 0) AS lifelong_spend_usd,
       COALESCE(life_pair.lifelong_num_ads, 0) AS lifelong_num_ads,
       COALESCE(life_page.page_lifelong_spend_usd, 0) AS page_lifelong_spend_usd
FROM weekly_agg AS w
JOIN best_name AS n
    ON n.page_id = w.page_id
   AND n.disclaimer = w.disclaimer
LEFT JOIN life_pair
    ON life_pair.page_id = w.page_id
   AND life_pair.disclaimer = w.disclaimer
LEFT JOIN life_page
    ON life_page.page_id = w.page_id;
