# Time / effort saved vs. manual migration

A simple, honest measurement — not a controlled study. Figures below are
either **measured** (pulled from this repo's own git history, which this
session generated in real time tonight) or **estimated** (a stated
assumption, clearly labelled as such, not a measurement).

## Measured: agent-assisted migration, this project, tonight

| Phase | Wall-clock (git merge timestamps) | What it covers |
|---|---|---|
| Write 10 legacy jobs + baselines | 19:30 → 19:47 (~17 min, on top of ~36 min total branch time incl. a 20-min SQL Server Docker attempt) | Hand-written legacy T-SQL/SAS + pandas reference baselines (not agent work — this is the legacy estate being migrated) |
| Build 3-agent pipeline + reconciliation engine, validate on 1 job | 19:37 → 20:12 (~35 min) | First-time framework build: discovery/translate/testgen agents, reconciliation engine, proven end-to-end on 1 job |
| Scale to remaining 9 jobs | 19:49 (branch start) → 19:59 (all 27 `claude -p` calls done and committed) → 20:34 (merged) | **27 real `claude -p` calls** (discovery+translate+testgen × 9 jobs) completed in **~10 minutes**; the remaining ~35 minutes was finding/fixing 2 genuine bugs (one in generated PySpark, one in a reference baseline) and 2 rounds of Claude Reviewer findings on the reconciliation engine itself |

**Headline measured number:** once the 3-agent framework existed, the
actual agent calls to discover lineage, translate to PySpark, and generate
tests for **9 legacy jobs took about 10 minutes (~1 minute/job)**. The
framework itself (built once, reused for every job) took ~35 minutes.
Bug-fixing and code review across both phases added the rest of the time
in each story — this is normal engineering overhead, not a per-job cost
that scales with job count.

## Estimated: manual migration (assumption, not measured)

No manual migration was actually performed in this project to compare
against — there was no time for a controlled A/B tonight. The figures
below are a stated engineering-judgement assumption for a legacy
T-SQL/SAS job with **undocumented** logic (the brief's actual premise):
understanding the existing code, hand-writing the PySpark translation,
hand-writing unit tests, and manually verifying reconciliation.

| Job complexity | Estimated manual effort (assumption) | Example from this project |
|---|---|---|
| Simple (single table, filter + group-by) | 1–2 hours | `policy_renewal_candidates.sql` |
| Moderate (multi-table join, CASE logic, date handling) | 2–4 hours | `claims_monthly_summary.sql`, `premium_collection_aging.sql` |
| Complex (SAS DATA step, BY-group/RETAIN, subtotal rows) | 4–8 hours | `policy_portfolio_rollup.sas`, `premium_aging_report.sas` |

## The comparison, honestly

- Agent-assisted (measured): ~1 minute/job for discovery+translation+test-gen,
  once the framework exists, plus review/fix time that doesn't scale
  linearly with job count.
- Manual (estimated assumption): 1–8 hours/job depending on complexity.
- This implies something like a **60×–500× reduction in hands-on effort
  per additional job** once the agent framework is built — but that range
  is driven entirely by the manual-effort assumption above, which is
  **not measured**. Treat the ratio as illustrative, not a verified claim.
  The one number in this document that is actually measured and verified
  is the ~10 minutes for 27 real agent calls across 9 jobs.
