import csv
import subprocess
import sys
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_NAMES = ["policies.csv", "claims.csv", "premiums.csv"]


def _read_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def _run_generator() -> None:
    subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_synthetic_data.py")],
        check=True,
        cwd=DATA_DIR.parent,
    )


@pytest.fixture(scope="module")
def generated_data():
    _run_generator()
    return {
        "policies": _read_csv(DATA_DIR / "policies.csv"),
        "claims": _read_csv(DATA_DIR / "claims.csv"),
        "premiums": _read_csv(DATA_DIR / "premiums.csv"),
    }


def test_generator_produces_expected_files_and_columns(generated_data):
    policies = generated_data["policies"]
    claims = generated_data["claims"]
    premiums = generated_data["premiums"]

    assert len(policies) > 0
    assert len(claims) > 0
    assert len(premiums) > 0

    assert set(policies[0].keys()) == {
        "policy_id",
        "customer_id",
        "product_line",
        "start_date",
        "end_date",
        "sum_insured",
        "region",
        "status",
    }
    assert set(claims[0].keys()) == {
        "claim_id",
        "policy_id",
        "incident_date",
        "claim_date",
        "claim_type",
        "claim_amount",
        "status",
    }
    assert set(premiums[0].keys()) == {
        "premium_id",
        "policy_id",
        "period_start",
        "period_end",
        "payment_frequency",
        "premium_amount",
        "collected_date",
    }


def test_generator_is_reproducible(generated_data):
    first = {name: (DATA_DIR / name).read_bytes() for name in CSV_NAMES}

    _run_generator()
    second = {name: (DATA_DIR / name).read_bytes() for name in CSV_NAMES}

    assert first == second


def test_claim_amounts_never_exceed_sum_insured(generated_data):
    policies = {p["policy_id"]: p for p in generated_data["policies"]}
    claims = generated_data["claims"]

    for claim in claims:
        sum_insured = float(policies[claim["policy_id"]]["sum_insured"])
        assert float(claim["claim_amount"]) <= sum_insured


def test_premiums_cover_the_full_policy_term(generated_data):
    from datetime import date

    policies = {p["policy_id"]: p for p in generated_data["policies"]}
    premiums_by_policy: dict[str, list[dict]] = {}
    for premium in generated_data["premiums"]:
        premiums_by_policy.setdefault(premium["policy_id"], []).append(premium)

    for policy_id, premiums in premiums_by_policy.items():
        policy_end = date.fromisoformat(policies[policy_id]["end_date"])
        last_period_end = max(date.fromisoformat(p["period_end"]) for p in premiums)
        assert last_period_end == policy_end
