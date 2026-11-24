-- Three published totals for the observed weeks. They are not the same cut.
-- Advertisers: one row per page and disclaimer per week.
-- Locations: one row per geography per week, including 'unknown'.
-- Regions: one row per page and region per week. The compiler notes that the
-- lifelong download had no region file. The weekly region sum runs below the
-- location sum; small geographic slices look like they were dropped.

SELECT 'advertisers' AS source,
       SUM(amount_spent_usd) AS spend_usd,
       COUNT(*) AS rows
FROM advertisers
WHERE window = 'last_7_days'
UNION ALL
SELECT 'locations',
       SUM(amount_spent_usd),
       COUNT(*)
FROM locations
WHERE window = 'last_7_days'
UNION ALL
SELECT 'regions',
       SUM(amount_spent_usd),
       COUNT(*)
FROM regions
UNION ALL
SELECT 'lifelong_advertisers',
       SUM(amount_spent_usd),
       COUNT(*)
FROM advertisers
WHERE window = 'lifelong'
UNION ALL
SELECT 'lifelong_locations',
       SUM(amount_spent_usd),
       COUNT(*)
FROM locations
WHERE window = 'lifelong';
