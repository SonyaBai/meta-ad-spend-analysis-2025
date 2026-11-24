-- State and territory spend from the location report, observed weeks only.
-- This is the geographic rollup Meta published. It is not the sum of the
-- region file. See sql/09_reconciliation.sql.
-- 'unknown' is spend the location report did not assign to a geography.

SELECT location_name,
       SUM(amount_spent_usd) AS spend_usd
FROM locations
WHERE window = 'last_7_days'
GROUP BY location_name
ORDER BY spend_usd DESC, location_name;
