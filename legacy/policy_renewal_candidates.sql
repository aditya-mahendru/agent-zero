-- policy_renewal_candidates.sql
-- Business purpose: count of active policies due for renewal within the
-- next 60 days of a reporting date, by product line -- feeds the renewals
-- team's weekly workload forecast.
-- Legacy quirks: DATEADD-based window, hardcoded reference date, status
-- filter combined with a date-range filter.

DECLARE @AsOfDate DATE = '2024-09-01';

SELECT
    p.product_line,
    COUNT(*) AS renewal_candidate_count,
    ROUND(SUM(p.sum_insured), 2) AS total_sum_insured_up_for_renewal
FROM policies p
WHERE p.status = 'Active'
    AND p.end_date BETWEEN @AsOfDate AND DATEADD(DAY, 60, @AsOfDate)
GROUP BY p.product_line
ORDER BY renewal_candidate_count DESC;
