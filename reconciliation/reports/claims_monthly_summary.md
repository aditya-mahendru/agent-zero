# Reconciliation report: claims_monthly_summary

**Overall: PASS**

**Baseline provenance:** pandas reference implementation of the legacy job's logic, additionally validated against a real SQL Server 2022 run for this job (538/538 rows matched exactly) -- see legacy/baselines/MANIFEST.md.

- Baseline rows: 538
- Migrated rows: 538
- Row count match: True
- Record-level match (full row equality after sort): True
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): none

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| claim_count | 1780.0 | 1780.0 | ✅ |
| total_claim_amount | 43636508.96 | 43636508.96 | ✅ |
