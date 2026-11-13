"""Run every legacy-job reference implementation against the synthetic data
and write its "legacy baseline" output CSV to legacy/baselines/.

These CSVs are what every migrated PySpark job is reconciled against. See
MANIFEST.md for which jobs' baselines come from this reference
implementation vs. an actual SQL Server run.

Usage:
    python -m legacy.baselines.generate_baselines
"""

from pathlib import Path

import pandas as pd

from legacy.baselines import reference_impls as ref

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUT_DIR = Path(__file__).parent


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    policies = pd.read_csv(DATA_DIR / "policies.csv")
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    premiums = pd.read_csv(DATA_DIR / "premiums.csv")
    return policies, claims, premiums


def main() -> None:
    policies, claims, premiums = load_data()

    jobs = {
        "claims_monthly_summary": ref.claims_monthly_summary(policies, claims),
        "policy_active_snapshot": ref.policy_active_snapshot(policies, premiums),
        "premium_collection_aging": ref.premium_collection_aging(policies, premiums),
        "claims_loss_ratio_by_region": ref.claims_loss_ratio_by_region(
            policies, claims, premiums
        ),
        "high_value_claims_review": ref.high_value_claims_review(policies, claims),
        "policy_renewal_candidates": ref.policy_renewal_candidates(policies),
        "claims_status_rollup_by_quarter": ref.claims_status_rollup_by_quarter(
            policies, claims
        ),
        "claims_summary": ref.claims_summary(policies, claims),
        "premium_aging_report": ref.premium_aging_report(policies, premiums),
        "policy_portfolio_rollup": ref.policy_portfolio_rollup(policies),
    }

    for name, df in jobs.items():
        out_path = OUT_DIR / f"{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"{name}: {len(df)} rows -> {out_path.name}")


if __name__ == "__main__":
    main()
