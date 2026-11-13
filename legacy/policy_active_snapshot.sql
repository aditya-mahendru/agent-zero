-- policy_active_snapshot.sql
-- Business purpose: point-in-time view of which policies are "effectively
-- active" as of a reporting snapshot date, reclassifying anything the
-- source `status` column got wrong relative to its own start/end dates.
-- Legacy quirks: CASE-based status override, a hardcoded snapshot date
-- (a classic legacy anti-pattern we deliberately preserve), LEFT JOIN to
-- pull each policy's most recent premium row.

DECLARE @SnapshotDate DATE = '2024-06-30';

SELECT
    p.policy_id,
    p.customer_id,
    p.product_line,
    p.region,
    p.sum_insured,
    CASE
        WHEN p.status = 'Cancelled' THEN 'Cancelled'
        WHEN p.end_date < @SnapshotDate THEN 'Expired'
        WHEN p.start_date > @SnapshotDate THEN 'Not Yet Active'
        ELSE 'Active'
    END AS effective_status,
    latest_prem.premium_amount AS latest_premium_amount,
    latest_prem.collected_date AS latest_premium_collected_date
FROM policies p
LEFT JOIN (
    SELECT
        pr.policy_id,
        pr.premium_amount,
        pr.collected_date,
        ROW_NUMBER() OVER (
            PARTITION BY pr.policy_id ORDER BY pr.collected_date DESC
        ) AS rn
    FROM premiums pr
) latest_prem
    ON latest_prem.policy_id = p.policy_id AND latest_prem.rn = 1
WHERE p.start_date <= @SnapshotDate;
