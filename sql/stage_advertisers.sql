-- Staged weekly advertiser grain. sql/extract_advertisers.sql reads these
-- temp tables. Running the whole aggregation as one statement makes SQLite
-- rebuild lookup indexes in a loop on this file; the stages below finish
-- in a few seconds.
-- python analysis.py runs this script, then the extract query.

DROP TABLE IF EXISTS weekly_agg;
DROP TABLE IF EXISTS weekly_names;
DROP TABLE IF EXISTS best_name;
DROP TABLE IF EXISTS life_pair;
DROP TABLE IF EXISTS life_page;

CREATE TEMP TABLE weekly_agg AS
SELECT page_id,
       disclaimer,
       SUM(amount_spent_usd) AS spend_usd,
       SUM(num_ads) AS num_ads,
       COUNT(DISTINCT date_start) AS weeks_observed,
       SUM(CASE WHEN date_start >= '2025-10-27' THEN amount_spent_usd ELSE 0 END)
           AS post_snapshot_spend_usd,
       SUM(CASE WHEN date_start >= '2025-10-27' THEN num_ads ELSE 0 END)
           AS post_snapshot_num_ads
FROM advertisers
WHERE window = 'last_7_days'
GROUP BY page_id, disclaimer;

CREATE INDEX idx_weekly_agg ON weekly_agg (page_id, disclaimer);

CREATE TEMP TABLE weekly_names AS
SELECT page_id,
       disclaimer,
       page_name,
       SUM(amount_spent_usd) AS name_spend
FROM advertisers
WHERE window = 'last_7_days'
GROUP BY page_id, disclaimer, page_name;

CREATE TEMP TABLE best_name AS
SELECT page_id, disclaimer, page_name
FROM (
    SELECT page_id,
           disclaimer,
           page_name,
           ROW_NUMBER() OVER (
               PARTITION BY page_id, disclaimer
               ORDER BY name_spend DESC, page_name
           ) AS rk
    FROM weekly_names
)
WHERE rk = 1;

CREATE INDEX idx_best_name ON best_name (page_id, disclaimer);

CREATE TEMP TABLE life_pair AS
SELECT page_id,
       disclaimer,
       SUM(amount_spent_usd) AS lifelong_spend_usd,
       SUM(num_ads) AS lifelong_num_ads
FROM advertisers
WHERE window = 'lifelong'
GROUP BY page_id, disclaimer;

CREATE INDEX idx_life_pair ON life_pair (page_id, disclaimer);

CREATE TEMP TABLE life_page AS
SELECT page_id,
       SUM(amount_spent_usd) AS page_lifelong_spend_usd
FROM advertisers
WHERE window = 'lifelong'
GROUP BY page_id;

CREATE INDEX idx_life_page ON life_page (page_id);
