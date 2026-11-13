import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from legacy.baselines import reference_impls as ref

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
BASELINE_DIR = ROOT / "legacy" / "baselines"


@pytest.fixture(scope="module")
def synthetic_data():
    subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_synthetic_data.py")],
        check=True,
        cwd=ROOT,
    )
    policies = pd.read_csv(DATA_DIR / "policies.csv")
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    premiums = pd.read_csv(DATA_DIR / "premiums.csv")
    return policies, claims, premiums


def test_all_ten_reference_impls_produce_rows(synthetic_data):
    policies, claims, premiums = synthetic_data

    outputs = {
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

    assert len(outputs) == 10
    for name, df in outputs.items():
        assert len(df) > 0, f"{name} produced no rows"


def test_claims_summary_row_count_matches_policy_count(synthetic_data):
    policies, claims, _ = synthetic_data
    out = ref.claims_summary(policies, claims)
    assert len(out) == len(policies)


def test_sqlserver_validated_baseline_matches_reference_impl():
    sqlserver_path = BASELINE_DIR / "claims_monthly_summary_sqlserver.csv"
    if not sqlserver_path.exists():
        pytest.skip("SQL Server validation CSV not present in this checkout")

    sql = pd.read_csv(
        sqlserver_path,
        names=[
            "product_line",
            "claim_month",
            "status_group",
            "claim_count",
            "total_claim_amount",
        ],
    )
    sql["claim_month"] = pd.to_datetime(sql["claim_month"]).dt.date.astype(str)
    sql["total_claim_amount"] = sql["total_claim_amount"].round(2)
    sql = sql.sort_values(["claim_month", "product_line", "status_group"]).reset_index(
        drop=True
    )

    ref_csv = BASELINE_DIR / "claims_monthly_summary.csv"
    if not ref_csv.exists():
        pytest.skip("Run legacy/baselines/generate_baselines.py first")
    reference = pd.read_csv(ref_csv)
    reference["claim_month"] = pd.to_datetime(reference["claim_month"]).dt.date.astype(
        str
    )
    reference["total_claim_amount"] = reference["total_claim_amount"].round(2)
    reference = reference.sort_values(
        ["claim_month", "product_line", "status_group"]
    ).reset_index(drop=True)

    merged = sql.merge(
        reference,
        on=["product_line", "claim_month", "status_group"],
        suffixes=("_sql", "_ref"),
    )
    assert len(merged) == len(sql) == len(reference)
    assert (merged["claim_count_sql"] == merged["claim_count_ref"]).all()
    assert (
        (merged["total_claim_amount_sql"] - merged["total_claim_amount_ref"]).abs()
        <= 0.01
    ).all()
