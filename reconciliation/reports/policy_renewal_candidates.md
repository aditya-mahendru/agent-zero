# Reconciliation report: policy_renewal_candidates

**Overall: PASS**

**Baseline provenance:** pandas reference implementation of the legacy job's logic -- **not** output from the original SQL Server/SAS engine. See legacy/baselines/MANIFEST.md.

- Baseline rows: 5
- Migrated rows: 5
- Row count match: True
- Record-level match (full row equality after sort): True
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): none

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| renewal_candidate_count | 60.0 | 60.0 | ✅ |
| total_sum_insured_up_for_renewal | 15796596.0 | 15796596.0 | ✅ |
