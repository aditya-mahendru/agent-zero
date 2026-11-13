-- claims_status_rollup_by_quarter.sql
-- Business purpose: quarterly claims status rollup (classic "pivot via
-- SUM(CASE WHEN ...)" pattern, since the original job predates any
-- native PIVOT usage at this insurer) by product line.
-- Legacy quirks: DATEPART-based quarter bucketing, SUM(CASE WHEN) pivot,
-- GROUP BY on a derived expression repeated in the SELECT list.

SELECT
    p.product_line,
    YEAR(c.claim_date) AS claim_year,
    DATEPART(QUARTER, c.claim_date) AS claim_quarter,
    SUM(CASE WHEN c.status = 'Open' THEN 1 ELSE 0 END) AS open_count,
    SUM(CASE WHEN c.status = 'Approved' THEN 1 ELSE 0 END) AS approved_count,
    SUM(CASE WHEN c.status = 'Rejected' THEN 1 ELSE 0 END) AS rejected_count,
    SUM(CASE WHEN c.status = 'Paid' THEN 1 ELSE 0 END) AS paid_count,
    COUNT(*) AS total_claims
FROM claims c
INNER JOIN policies p
    ON p.policy_id = c.policy_id
GROUP BY
    p.product_line,
    YEAR(c.claim_date),
    DATEPART(QUARTER, c.claim_date)
ORDER BY
    claim_year,
    claim_quarter,
    p.product_line;
