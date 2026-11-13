-- claims_loss_ratio_by_region.sql
-- Business purpose: loss ratio (total claims paid out / total premium
-- collected) by region and product line -- a core actuarial reporting
-- metric. Legacy quirks: three-way join, NULLIF to avoid divide-by-zero,
-- ISNULL for the ~2% of policies with a missing region.

SELECT
    ISNULL(pol.region, 'UNKNOWN') AS region,
    pol.product_line,
    ROUND(SUM(c.claim_amount), 2) AS total_claims,
    ROUND(SUM(pr.premium_amount), 2) AS total_premium,
    ROUND(
        SUM(c.claim_amount) / NULLIF(SUM(pr.premium_amount), 0),
        4
    ) AS loss_ratio
FROM policies pol
LEFT JOIN claims c
    ON c.policy_id = pol.policy_id
LEFT JOIN premiums pr
    ON pr.policy_id = pol.policy_id
GROUP BY
    ISNULL(pol.region, 'UNKNOWN'),
    pol.product_line
ORDER BY
    region,
    product_line;
