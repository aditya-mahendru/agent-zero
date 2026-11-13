-- premium_collection_aging.sql
-- Business purpose: ageing of premium collection delay (days between the
-- start of the billing period and the date it was actually collected),
-- bucketed for a finance aged-debtors style report.
-- Legacy quirks: DATEDIFF-based bucketing via nested CASE, COALESCE for a
-- possible NULL region, join to policies for product_line.

SELECT
    pol.product_line,
    COALESCE(pol.region, 'UNKNOWN') AS region,
    pr.premium_id,
    pr.policy_id,
    DATEDIFF(DAY, pr.period_start, pr.collected_date) AS collection_delay_days,
    CASE
        WHEN DATEDIFF(DAY, pr.period_start, pr.collected_date) <= 0 THEN 'On Time'
        WHEN DATEDIFF(DAY, pr.period_start, pr.collected_date) BETWEEN 1 AND 30 THEN '1-30 Days'
        WHEN DATEDIFF(DAY, pr.period_start, pr.collected_date) BETWEEN 31 AND 60 THEN '31-60 Days'
        ELSE '60+ Days'
    END AS aging_bucket,
    pr.premium_amount
FROM premiums pr
INNER JOIN policies pol
    ON pol.policy_id = pr.policy_id;
