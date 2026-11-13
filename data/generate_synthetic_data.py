"""Generate synthetic UK & Ireland insurer data: policies, claims, premiums.

Synthetic only -- no real or personal data. Fixed seed makes every run
byte-identical, so legacy jobs, migrated PySpark jobs and reconciliation
reports are all comparing against the same fixture.

Usage:
    python data/generate_synthetic_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
N_POLICIES = 2000
OUT_DIR = Path(__file__).parent

PRODUCT_LINES = ["Motor", "Home", "Life", "Travel", "Commercial"]
REGIONS = ["Dublin", "Cork", "Belfast", "London", "Manchester", "Edinburgh"]
POLICY_STATUSES = ["Active", "Lapsed", "Cancelled"]
CLAIM_TYPES = {
    "Motor": ["Collision", "Theft", "Windscreen", "Fire"],
    "Home": ["Flood", "Fire", "Theft", "Storm Damage"],
    "Life": ["Death Benefit", "Critical Illness"],
    "Travel": ["Medical", "Lost Baggage", "Trip Cancellation"],
    "Commercial": ["Liability", "Property Damage", "Business Interruption"],
}
CLAIM_STATUSES = ["Open", "Approved", "Rejected", "Paid"]
PAYMENT_FREQUENCIES = ["Monthly", "Annual"]

POLICY_START = date(2022, 1, 1)
POLICY_END = date(2025, 12, 31)


def _random_date(rng: random.Random, start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=rng.randint(0, span))


def generate_policies(rng: random.Random) -> list[dict]:
    policies = []
    for i in range(1, N_POLICIES + 1):
        policy_id = f"POL{i:06d}"
        product_line = rng.choice(PRODUCT_LINES)
        start_date = _random_date(rng, POLICY_START, POLICY_END - timedelta(days=365))
        term_days = rng.choice([365, 730])
        end_date = start_date + timedelta(days=term_days)
        status = rng.choices(POLICY_STATUSES, weights=[0.75, 0.15, 0.10])[0]
        sum_insured = round(rng.uniform(5_000, 500_000), 2)
        # A deliberate sprinkling of nulls -- legacy jobs have to cope with this.
        region = rng.choice(REGIONS) if rng.random() > 0.02 else ""
        policies.append(
            {
                "policy_id": policy_id,
                "customer_id": f"CUST{rng.randint(1, N_POLICIES // 2):06d}",
                "product_line": product_line,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "sum_insured": sum_insured,
                "region": region,
                "status": status,
            }
        )
    return policies


def generate_claims(rng: random.Random, policies: list[dict]) -> list[dict]:
    claims = []
    claim_seq = 1
    for policy in policies:
        n_claims = rng.choices([0, 1, 2, 3, 4], weights=[0.5, 0.25, 0.15, 0.07, 0.03])[
            0
        ]
        start_date = date.fromisoformat(policy["start_date"])
        end_date = date.fromisoformat(policy["end_date"])
        for _ in range(n_claims):
            incident_date = _random_date(rng, start_date, min(end_date, POLICY_END))
            claim_date = incident_date + timedelta(days=rng.randint(0, 30))
            claim_type = rng.choice(CLAIM_TYPES[policy["product_line"]])
            claim_amount = round(
                min(rng.uniform(100, 50_000), float(policy["sum_insured"])), 2
            )
            claims.append(
                {
                    "claim_id": f"CLM{claim_seq:07d}",
                    "policy_id": policy["policy_id"],
                    "incident_date": incident_date.isoformat(),
                    "claim_date": claim_date.isoformat(),
                    "claim_type": claim_type,
                    "claim_amount": claim_amount,
                    "status": rng.choices(
                        CLAIM_STATUSES, weights=[0.15, 0.20, 0.15, 0.50]
                    )[0],
                }
            )
            claim_seq += 1
    return claims


def generate_premiums(rng: random.Random, policies: list[dict]) -> list[dict]:
    premiums = []
    premium_seq = 1
    for policy in policies:
        start_date = date.fromisoformat(policy["start_date"])
        end_date = date.fromisoformat(policy["end_date"])
        frequency = rng.choice(PAYMENT_FREQUENCIES)
        step_days = 30 if frequency == "Monthly" else 365
        term_days = (end_date - start_date).days
        installments = max(1, -(-term_days // step_days))  # ceil division
        installment_amount = round(
            float(policy["sum_insured"]) * 0.04 / installments, 2
        )
        period_start = start_date
        for _ in range(installments):
            period_end = min(period_start + timedelta(days=step_days), end_date)
            premiums.append(
                {
                    "premium_id": f"PRM{premium_seq:07d}",
                    "policy_id": policy["policy_id"],
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "payment_frequency": frequency,
                    "premium_amount": installment_amount,
                    "collected_date": (
                        period_start + timedelta(days=rng.randint(0, 5))
                    ).isoformat(),
                }
            )
            premium_seq += 1
            period_start = period_end
            if period_start >= end_date:
                break
    return premiums


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    policies = generate_policies(rng)
    claims = generate_claims(rng, policies)
    premiums = generate_premiums(rng, policies)

    write_csv(policies, OUT_DIR / "policies.csv")
    write_csv(claims, OUT_DIR / "claims.csv")
    write_csv(premiums, OUT_DIR / "premiums.csv")

    print(f"policies: {len(policies)} rows")
    print(f"claims:   {len(claims)} rows")
    print(f"premiums: {len(premiums)} rows")


if __name__ == "__main__":
    main()
