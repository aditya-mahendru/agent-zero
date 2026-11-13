# Reconciliation report: claims_summary

**Overall: PASS**

- Baseline rows: 2000
- Migrated rows: 2000
- Row count match: True
- Record-level match (full row equality after sort): False
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): ['customer_id', 'end_date', 'high_severity_count', 'region', 'start_date', 'status']

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| sum_insured | 494841604.32 | 494841604.32 | ✅ |
| claim_count | 1780.0 | 1780.0 | ✅ |
| total_claim_amount | 43636508.96 | 43636508.96 | ✅ |
| max_claim_amount | 29776106.97 | 29776106.97 | ✅ |
| severity_ratio | 230.53 | 230.53 | ✅ |
