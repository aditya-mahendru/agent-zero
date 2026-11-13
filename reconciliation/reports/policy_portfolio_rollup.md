# Reconciliation report: policy_portfolio_rollup

**Overall: PASS**

**Baseline provenance:** pandas reference implementation of the legacy job's logic -- **not** output from the original SQL Server/SAS engine. See legacy/baselines/MANIFEST.md.

- Baseline rows: 42
- Migrated rows: 42
- Row count match: True
- Record-level match (full row equality after sort): True
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): none

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| total_sum_insured | 989683208.64 | 989683208.64 | ✅ |
| policy_count | 4000.0 | 4000.0 | ✅ |
