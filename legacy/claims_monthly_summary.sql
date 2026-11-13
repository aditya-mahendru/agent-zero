-- claims_monthly_summary.sql
-- Business purpose: monthly claims volume and total claim amount by product
-- line, with claims bucketed into a simplified status group for finance
-- reporting. Legacy quirks: CASE-based status regrouping, DATEFROMPARTS
-- month truncation, join + GROUP BY, implicit float rounding.

SELECT
    p.product_line,
    DATEFROMPARTS(YEAR(c.claim_date), MONTH(c.claim_date), 1) AS claim_month,
    CASE
        WHEN c.status IN ('Approved', 'Paid') THEN 'Settled'
        WHEN c.status = 'Rejected' THEN 'Declined'
        ELSE 'Pending'
    END AS status_group,
    COUNT(*) AS claim_count,
    ROUND(SUM(c.claim_amount), 2) AS total_claim_amount
FROM claims c
INNER JOIN policies p
    ON p.policy_id = c.policy_id
GROUP BY
    p.product_line,
    DATEFROMPARTS(YEAR(c.claim_date), MONTH(c.claim_date), 1),
    CASE
        WHEN c.status IN ('Approved', 'Paid') THEN 'Settled'
        WHEN c.status = 'Rejected' THEN 'Declined'
        ELSE 'Pending'
    END
ORDER BY
    claim_month,
    p.product_line;
