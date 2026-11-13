# Time / effort saved vs. manual migration

A simple, honest measurement — not a controlled study. Figures are
grouped by exactly where they come from, so none is overstated:

- **(git)** — independently verifiable from this repo's own commit history
  (`git log --format="%ad %s"`, merge commits only).
- **(session)** — timestamps this session observed while doing the work
  (e.g. when a batch of agent calls started), not separately recorded in
  git, so treat as a recollection, not an independently-checkable figure.
- **(estimate)** — a stated assumption, not a measurement at all.

## Measured (git): wall-clock per story, from this project's merge history

| Merge | Time (git) | Branch covers |
|---|---|---|
| `setup` → main | 18:55:23 | Project scaffolding (not migration work) |
| `1-synthetic-data` → main | 19:30:49 | Synthetic data generator |
| `2-legacy-jobs` → main | 19:47:25 | 10 legacy jobs + baselines (incl. a ~20-min SQL Server Docker attempt — the attempt itself isn't separately timestamped in git, so treat that sub-figure as **(session)**, not (git)) |
| `3-agent-pipeline` → main | 20:12:46 | Build the 3-agent framework; validate end-to-end on 1 job |
| `4-scale-to-all-jobs` → main | 20:34:44 | Scale the framework to the remaining 9 jobs, incl. 2 real bug fixes and 2 rounds of code review |

**End-to-end, git-verified, marginal cost per job once the framework
existed:** this session pipelines work (the next branch is often started
before the previous one's MR has merged), so a merge-to-merge window
between *different* branches overlaps with work on the earlier one and
overstates the gap. The clean, non-overlapping figure instead uses
`4-scale-to-all-jobs`'s own first commit to its own merge: 19:59:44 →
20:34:44 = **35 min for 9 jobs ≈ 3.9 min/job**, discovery through
translation, test generation, bug-fixing and two rounds of code review —
the full cost of adding one more migrated-and-reconciled job, not just
the agent calls. (This still slightly understates true elapsed time: work
on a branch — writing and testing code — typically starts a little before
its first commit.)

## Measured (session): the agent calls alone, excluding review/fix time

Within that same `4-scale-to-all-jobs` story, this session's own timing
(not separately recorded in git, since all 9 jobs' work landed in commits
after the fact): the **27 real `claude -p` calls** (discovery + translate
+ testgen × 9 jobs) ran start-to-finish in **about 10 minutes (≈1.1
min/job)**. The remaining ~25 minutes of that story's 35 was finding and
fixing 2 genuine bugs and responding to 2 rounds of Claude Reviewer
findings — real engineering work, just not "agent compute time."

## Estimated (assumption, not measured): manual migration

No manual migration was actually performed tonight to compare against —
there was no time for a controlled A/B. The figures below are a stated
engineering-judgement assumption for a legacy T-SQL/SAS job with
**undocumented** logic (the brief's actual premise): understanding the
existing code, hand-writing the PySpark translation, hand-writing unit
tests, and manually verifying reconciliation.

| Job complexity | Estimated manual effort (assumption) | Example from this project |
|---|---|---|
| Simple (single table, filter + group-by) | 1–2 hours | `policy_renewal_candidates.sql` |
| Moderate (multi-table join, CASE logic, date handling) | 2–4 hours | `claims_monthly_summary.sql`, `premium_collection_aging.sql` |
| Complex (SAS DATA step, BY-group/RETAIN, subtotal rows) | 4–8 hours | `policy_portfolio_rollup.sas`, `premium_aging_report.sas` |

## The comparison, computed on a consistent basis

Comparing like with like — end-to-end manual estimate (60–480 min/job)
against end-to-end agent-assisted measured cost (3.9 min/job,
git-verified, including bug-fixing and review):

- 60 min ÷ 3.9 min/job ≈ **15×**
- 480 min ÷ 3.9 min/job ≈ **123×**

That **~15×–123×** range uses the same end-to-end basis on both sides. A
second, narrower figure — agent compute time only (≈1.1 min/job,
session-observed, excluding review/fix) against the same manual
estimate — gives roughly 55×–440×, but that one is **not** apples-to-
apples: it excludes the review/fix time real engineering work needs on
both sides. Treat 15×–123× as the honest headline number, and the wider
range as upper-bound/illustrative only.
