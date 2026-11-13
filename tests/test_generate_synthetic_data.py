import csv
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _read_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def test_generator_produces_expected_files_and_columns():
    subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_synthetic_data.py")],
        check=True,
        cwd=DATA_DIR.parent,
    )

    policies = _read_csv(DATA_DIR / "policies.csv")
    claims = _read_csv(DATA_DIR / "claims.csv")
    premiums = _read_csv(DATA_DIR / "premiums.csv")

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


def test_generator_is_reproducible():
    subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_synthetic_data.py")],
        check=True,
        cwd=DATA_DIR.parent,
    )
    first = (DATA_DIR / "policies.csv").read_bytes()

    subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_synthetic_data.py")],
        check=True,
        cwd=DATA_DIR.parent,
    )
    second = (DATA_DIR / "policies.csv").read_bytes()

    assert first == second


def test_claim_amounts_never_exceed_sum_insured():
    policies = {p["policy_id"]: p for p in _read_csv(DATA_DIR / "policies.csv")}
    claims = _read_csv(DATA_DIR / "claims.csv")

    for claim in claims:
        sum_insured = float(policies[claim["policy_id"]]["sum_insured"])
        assert float(claim["claim_amount"]) <= sum_insured
