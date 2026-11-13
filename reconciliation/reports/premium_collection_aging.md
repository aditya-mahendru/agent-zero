# Reconciliation report: premium_collection_aging

**Overall: PASS**

**Baseline provenance:** pandas reference implementation of the legacy job's logic -- **not** output from the original SQL Server/SAS engine. See legacy/baselines/MANIFEST.md.

- Baseline rows: 19805
- Migrated rows: 19805
- Row count match: True
- Record-level match (full row equality after sort): True
- Missing columns (in baseline, not migrated): none
- Extra columns (in migrated, not baseline): none

## Numeric column totals

| Column | Baseline sum | Migrated sum | Match |
|---|---|---|---|
| collection_delay_days | 49808.0 | 49808.0 | ✅ |
| premium_amount | 19793666.27 | 19793666.27 | ✅ |
