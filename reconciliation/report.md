# Reconciliation rollup

Every baseline below is an independent pandas reference implementation of the legacy job's logic, not output from the original SQL Server/SAS engine, except where noted -- see legacy/baselines/MANIFEST.md.

| Job | Status | Baseline provenance | Notes |
|---|---|---|---|
| claims_loss_ratio_by_region | PASS | pandas reference impl |  |
| claims_monthly_summary | PASS | SQL Server-validated |  |
| claims_status_rollup_by_quarter | PASS | pandas reference impl |  |
| claims_summary | PASS | pandas reference impl |  |
| high_value_claims_review | PASS | pandas reference impl |  |
| policy_active_snapshot | PASS | pandas reference impl |  |
| policy_portfolio_rollup | PASS | pandas reference impl |  |
| policy_renewal_candidates | PASS | pandas reference impl |  |
| premium_aging_report | PASS | pandas reference impl |  |
| premium_collection_aging | PASS | pandas reference impl |  |
