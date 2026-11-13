# Reconciliation report: policy_active_snapshot

**Overall: PASS**

**Baseline provenance:** pandas reference implementation of the legacy job's logic -- **not** output from the original SQL Server/SAS engine. See legacy/baselines/MANIFEST.md.

- Baseline rows: 1652
- Migrated rows: 1652
- Row count match: True
- Record-level match (full row equality after sort): True
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): none

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| sum_insured | 406511065.31 | 406511065.31 | ✅ |
| latest_premium_amount | 6558285.95 | 6558285.95 | ✅ |
