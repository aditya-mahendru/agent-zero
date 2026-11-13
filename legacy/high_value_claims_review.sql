-- high_value_claims_review.sql
-- Business purpose: flag claims that consume a large share of the policy's
-- sum insured, for manual underwriting review.
-- Legacy quirks: a magic-number threshold (0.5) embedded in the query
-- (never parameterised in the original job -- preserved as-is), CASE for
-- the review flag, join to policies.

SELECT
    c.claim_id,
    c.policy_id,
    p.product_line,
    c.claim_amount,
    p.sum_insured,
    ROUND(c.claim_amount / p.sum_insured, 4) AS claim_to_sum_insured_ratio,
    CASE
        WHEN c.claim_amount / p.sum_insured >= 0.5 THEN 'REVIEW REQUIRED'
        WHEN c.claim_amount / p.sum_insured >= 0.25 THEN 'WATCH'
        ELSE 'STANDARD'
    END AS review_flag
FROM claims c
INNER JOIN policies p
    ON p.policy_id = c.policy_id
WHERE c.status <> 'Rejected'
ORDER BY
    claim_to_sum_insured_ratio DESC;
