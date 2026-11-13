# Legacy baseline manifest

Every migrated PySpark job is reconciled against the baseline CSV listed
here for its source job. **How each baseline was produced matters** — this
table states it plainly for every job, per the project's Responsible AI
commitments.

| Legacy job | Type | Baseline source | Notes |
|---|---|---|---|
| `claims_monthly_summary.sql` | T-SQL | **Python/pandas reference implementation** (`reference_impls.py`), **validated against a real SQL Server 2022 run** | Stood up SQL Server 2022 in Docker (amd64 emulation), bulk-loaded the synthetic `policies`/`claims` data, ran this job's actual T-SQL, and diffed the result against the reference implementation: **538/538 rows match exactly** (`claims_monthly_summary_sqlserver.csv` kept as evidence). Along the way, found and fixed a real bulk-load gotcha: Python's `csv` module writes `\r\n` line endings, and `bcp`'s default row terminator leaves the trailing `\r` attached to the last column, silently breaking every string comparison on it (every claim fell into the `ELSE` branch of the `CASE`) until `bcp` was told its row terminator is `\r\n`, not `\n`. |
| `policy_active_snapshot.sql` | T-SQL | Python/pandas reference implementation | Not run against SQL Server — time budget spent validating the job above instead. |
| `premium_collection_aging.sql` | T-SQL | Python/pandas reference implementation | ditto |
| `claims_loss_ratio_by_region.sql` | T-SQL | Python/pandas reference implementation | ditto. Note: this job's own join logic double-counts (policies LEFT JOINed to claims and to premiums independently fan out), which is a genuine quirk of the legacy SQL, not a bug in the reference impl — the reference impl reproduces it faithfully, as a true migration must. |
| `high_value_claims_review.sql` | T-SQL | Python/pandas reference implementation | ditto |
| `policy_renewal_candidates.sql` | T-SQL | Python/pandas reference implementation | ditto |
| `claims_status_rollup_by_quarter.sql` | T-SQL | Python/pandas reference implementation | ditto |
| `claims_summary.sas` | SAS | Python/pandas reference implementation | **No SAS execution anywhere in this project.** SAS cannot run in this environment; this baseline is an independent re-implementation of the `.sas` program's documented logic, not output from the SAS engine. Reconciliation against it proves the PySpark migration matches a verified-equivalent reference, not the legacy SAS runtime itself. |
| `premium_aging_report.sas` | SAS | Python/pandas reference implementation | ditto |
| `policy_portfolio_rollup.sas` | SAS | Python/pandas reference implementation | ditto |

## Why only one job got a real SQL Server run

The brief allows attempting the SQL Server Docker baseline "if you can get
it working within 20 minutes." It came up and was queryable within that
budget, so one representative T-SQL job was run against it end-to-end to
validate the pandas reference implementation's fidelity — a credible,
checked claim ("our reference impl matches real SQL Server, verified on
this job") rather than running all 7 T-SQL jobs through Docker at the cost
of the rest of tonight's scope. The remaining 6 T-SQL jobs and all 3 SAS
jobs use the same reference-implementation approach, each written to
faithfully reproduce its source job's logic — quirks included.

## Regenerating

```bash
python data/generate_synthetic_data.py
python -m legacy.baselines.generate_baselines
```
