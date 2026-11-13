# Reconciliation report: claims_status_rollup_by_quarter

**Overall: PASS**

**Baseline provenance:** pandas reference implementation of the legacy job's logic -- **not** output from the original SQL Server/SAS engine. See legacy/baselines/MANIFEST.md.

- Baseline rows: 84
- Migrated rows: 84
- Row count match: True
- Record-level match (full row equality after sort): True
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): none

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| claim_year | 169988.0 | 169988.0 | ✅ |
| claim_quarter | 204.0 | 204.0 | ✅ |
| open_count | 264.0 | 264.0 | ✅ |
| approved_count | 364.0 | 364.0 | ✅ |
| rejected_count | 267.0 | 267.0 | ✅ |
| paid_count | 885.0 | 885.0 | ✅ |
| total_claims | 1780.0 | 1780.0 | ✅ |
