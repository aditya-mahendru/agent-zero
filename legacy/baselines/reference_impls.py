"""Independent pandas reference implementations of each legacy job's logic.

These are the "legacy baseline" outputs that migrated PySpark jobs must
reconcile against. For the 3 SAS jobs, and for any T-SQL job where the SQL
Server Docker baseline wasn't available in time (see MANIFEST.md), this is
the *only* baseline -- it stands in for the legacy engine, and every
reconciliation report built from it says so explicitly.

Each function takes the raw policies/claims/premiums DataFrames and returns
a DataFrame matching the corresponding legacy job's output, replicating the
job's logic -- quirks, implicit bugs and all -- rather than a "corrected"
version of it. A faithful migration reconciles against what the legacy job
actually produces, not what it should have produced.
"""

from __future__ import annotations

import pandas as pd


def claims_monthly_summary(
    policies: pd.DataFrame, claims: pd.DataFrame
) -> pd.DataFrame:
    df = claims.merge(
        policies[["policy_id", "product_line"]], on="policy_id", how="inner"
    )
    df["claim_month"] = pd.to_datetime(df["claim_date"]).values.astype("datetime64[M]")

    def status_group(status: str) -> str:
        if status in ("Approved", "Paid"):
            return "Settled"
        if status == "Rejected":
            return "Declined"
        return "Pending"

    df["status_group"] = df["status"].map(status_group)
    out = (
        df.groupby(["product_line", "claim_month", "status_group"])
        .agg(
            claim_count=("claim_id", "count"),
            total_claim_amount=("claim_amount", "sum"),
        )
        .reset_index()
    )
    out["total_claim_amount"] = out["total_claim_amount"].round(2)
    return out.sort_values(["claim_month", "product_line"]).reset_index(drop=True)


def policy_active_snapshot(
    policies: pd.DataFrame, premiums: pd.DataFrame, snapshot_date: str = "2024-06-30"
) -> pd.DataFrame:
    snap = pd.Timestamp(snapshot_date)
    df = policies[pd.to_datetime(policies["start_date"]) <= snap].copy()

    def effective_status(row) -> str:
        if row["status"] == "Cancelled":
            return "Cancelled"
        if pd.to_datetime(row["end_date"]) < snap:
            return "Expired"
        if pd.to_datetime(row["start_date"]) > snap:
            return "Not Yet Active"
        return "Active"

    df["effective_status"] = df.apply(effective_status, axis=1)

    prem_sorted = premiums.sort_values(["policy_id", "collected_date"])
    latest = prem_sorted.groupby("policy_id", as_index=False).last()[
        ["policy_id", "premium_amount", "collected_date"]
    ]
    latest = latest.rename(
        columns={
            "premium_amount": "latest_premium_amount",
            "collected_date": "latest_premium_collected_date",
        }
    )

    out = df.merge(latest, on="policy_id", how="left")
    return out[
        [
            "policy_id",
            "customer_id",
            "product_line",
            "region",
            "sum_insured",
            "effective_status",
            "latest_premium_amount",
            "latest_premium_collected_date",
        ]
    ]


def premium_collection_aging(
    policies: pd.DataFrame, premiums: pd.DataFrame
) -> pd.DataFrame:
    df = premiums.merge(
        policies[["policy_id", "product_line", "region"]], on="policy_id", how="inner"
    )
    df["region"] = df["region"].fillna("UNKNOWN").replace("", "UNKNOWN")
    delay = (
        pd.to_datetime(df["collected_date"]) - pd.to_datetime(df["period_start"])
    ).dt.days
    df["collection_delay_days"] = delay

    def bucket(days: int) -> str:
        if days <= 0:
            return "On Time"
        if days <= 30:
            return "1-30 Days"
        if days <= 60:
            return "31-60 Days"
        return "60+ Days"

    df["aging_bucket"] = df["collection_delay_days"].map(bucket)
    return df[
        [
            "product_line",
            "region",
            "premium_id",
            "policy_id",
            "collection_delay_days",
            "aging_bucket",
            "premium_amount",
        ]
    ]


def claims_loss_ratio_by_region(
    policies: pd.DataFrame, claims: pd.DataFrame, premiums: pd.DataFrame
) -> pd.DataFrame:
    # Deliberately mirrors the legacy SQL's double LEFT JOIN fan-out: a
    # policy's claims and premiums are joined independently, so a policy
    # with M claims and N premium rows contributes M*N rows to the
    # aggregate below -- a genuine quirk of the legacy job, not a bug we
    # introduced, and one the migrated PySpark job must reproduce exactly.
    df = policies.merge(
        claims[["policy_id", "claim_amount"]], on="policy_id", how="left"
    )
    df = df.merge(premiums[["policy_id", "premium_amount"]], on="policy_id", how="left")
    df["region"] = df["region"].fillna("UNKNOWN").replace("", "UNKNOWN")

    out = (
        df.groupby(["region", "product_line"])
        .agg(
            total_claims=("claim_amount", "sum"),
            total_premium=("premium_amount", "sum"),
        )
        .reset_index()
    )
    out["total_claims"] = out["total_claims"].fillna(0).round(2)
    out["total_premium"] = out["total_premium"].fillna(0).round(2)
    out["loss_ratio"] = (
        out["total_claims"] / out["total_premium"].replace(0, pd.NA)
    ).round(4)
    return out.sort_values(["region", "product_line"]).reset_index(drop=True)


def high_value_claims_review(
    policies: pd.DataFrame, claims: pd.DataFrame
) -> pd.DataFrame:
    df = claims[claims["status"] != "Rejected"].merge(
        policies[["policy_id", "product_line", "sum_insured"]],
        on="policy_id",
        how="inner",
    )
    # The legacy SQL's CASE compares the unrounded ratio; only the selected
    # column is rounded for display. The flag must use the unrounded value,
    # or a ratio like 0.49996 would round to 0.5 and get the wrong flag.
    raw_ratio = df["claim_amount"] / df["sum_insured"]

    def flag(ratio: float) -> str:
        if ratio >= 0.5:
            return "REVIEW REQUIRED"
        if ratio >= 0.25:
            return "WATCH"
        return "STANDARD"

    df["review_flag"] = raw_ratio.map(flag)
    df["claim_to_sum_insured_ratio"] = raw_ratio.round(4)
    out = df[
        [
            "claim_id",
            "policy_id",
            "product_line",
            "claim_amount",
            "sum_insured",
            "claim_to_sum_insured_ratio",
            "review_flag",
        ]
    ]
    return out.sort_values("claim_to_sum_insured_ratio", ascending=False).reset_index(
        drop=True
    )


def policy_renewal_candidates(
    policies: pd.DataFrame, as_of_date: str = "2024-09-01"
) -> pd.DataFrame:
    as_of = pd.Timestamp(as_of_date)
    window_end = as_of + pd.Timedelta(days=60)
    df = policies[
        (policies["status"] == "Active")
        & (pd.to_datetime(policies["end_date"]) >= as_of)
        & (pd.to_datetime(policies["end_date"]) <= window_end)
    ]
    out = (
        df.groupby("product_line")
        .agg(
            renewal_candidate_count=("policy_id", "count"),
            total_sum_insured_up_for_renewal=("sum_insured", "sum"),
        )
        .reset_index()
    )
    out["total_sum_insured_up_for_renewal"] = out[
        "total_sum_insured_up_for_renewal"
    ].round(2)
    return out.sort_values("renewal_candidate_count", ascending=False).reset_index(
        drop=True
    )


def claims_status_rollup_by_quarter(
    policies: pd.DataFrame, claims: pd.DataFrame
) -> pd.DataFrame:
    df = claims.merge(
        policies[["policy_id", "product_line"]], on="policy_id", how="inner"
    )
    claim_date = pd.to_datetime(df["claim_date"])
    df["claim_year"] = claim_date.dt.year
    df["claim_quarter"] = claim_date.dt.quarter

    def status_counts(group: pd.DataFrame) -> pd.Series:
        counts = group["status"].value_counts()
        return pd.Series(
            {
                "open_count": counts.get("Open", 0),
                "approved_count": counts.get("Approved", 0),
                "rejected_count": counts.get("Rejected", 0),
                "paid_count": counts.get("Paid", 0),
                "total_claims": len(group),
            }
        )

    out = (
        df.groupby(["product_line", "claim_year", "claim_quarter"])
        .apply(status_counts, include_groups=False)
        .reset_index()
    )
    return out.sort_values(["claim_year", "claim_quarter", "product_line"]).reset_index(
        drop=True
    )


def claims_summary(policies: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    agg = (
        claims.groupby("policy_id")
        .agg(
            claim_count=("claim_id", "count"),
            total_claim_amount=("claim_amount", "sum"),
            max_claim_amount=("claim_amount", "max"),
        )
        .reset_index()
    )
    df = policies.merge(agg, on="policy_id", how="left")
    for col in ("claim_count", "total_claim_amount", "max_claim_amount"):
        df[col] = df[col].fillna(0)

    df["severity_ratio"] = (
        df["max_claim_amount"] / df["sum_insured"].replace(0, pd.NA)
    ).fillna(0)

    def severity_flag(ratio: float) -> str:
        if ratio >= 0.5:
            return "HIGH"
        if ratio >= 0.25:
            return "MEDIUM"
        return "LOW"

    df["severity_flag"] = df["severity_ratio"].map(severity_flag)
    cols = [
        "policy_id",
        "product_line",
        "sum_insured",
        "claim_count",
        "total_claim_amount",
        "max_claim_amount",
        "severity_ratio",
        "severity_flag",
    ]
    return df[cols].sort_values(["product_line", "policy_id"]).reset_index(drop=True)


def premium_aging_report(
    policies: pd.DataFrame, premiums: pd.DataFrame
) -> pd.DataFrame:
    df = premiums.merge(
        policies[["policy_id", "product_line", "region"]], on="policy_id", how="inner"
    )
    delay = (
        pd.to_datetime(df["collected_date"]) - pd.to_datetime(df["period_start"])
    ).dt.days
    df["collection_delay_days"] = delay

    def bucket(days: int) -> str:
        if days <= 0:
            return "On Time"
        if days <= 30:
            return "1-30 Days"
        if days <= 60:
            return "31-60 Days"
        return "60+ Days"

    df["aging_bucket"] = df["collection_delay_days"].map(bucket)
    df = df.sort_values(["product_line", "policy_id"]).reset_index(drop=True)

    # RETAIN running_overdue_total, reset at each product_line BY-group.
    running_total = 0.0
    totals = []
    current_group = None
    for _, row in df.iterrows():
        if row["product_line"] != current_group:
            running_total = 0.0
            current_group = row["product_line"]
        if row["aging_bucket"] != "On Time":
            running_total += row["premium_amount"]
        totals.append(round(running_total, 2))
    df["running_overdue_total"] = totals

    return df[
        [
            "product_line",
            "policy_id",
            "collection_delay_days",
            "aging_bucket",
            "premium_amount",
            "running_overdue_total",
        ]
    ]


def policy_portfolio_rollup(policies: pd.DataFrame) -> pd.DataFrame:
    df = policies.copy()
    # fillna first: pandas reads a blank CSV field as NaN, not "", and a plain
    # .replace("", ...) would miss it -- leaving those rows with a real NaN
    # region, which pandas' groupby silently drops instead of bucketing as
    # UNKNOWN (the SAS job's actual behaviour, since SAS has no empty-char
    # vs. missing distinction: `if region = ""` catches both).
    df["region"] = df["region"].fillna("UNKNOWN").replace("", "UNKNOWN")

    agg = (
        df.groupby(["region", "product_line"])
        .agg(
            total_sum_insured=("sum_insured", "sum"),
            policy_count=("policy_id", "count"),
        )
        .reset_index()
        .sort_values(["region", "product_line"])
    )

    rows = []
    for region, group in agg.groupby("region", sort=False):
        region_total_sum_insured = 0.0
        region_total_policy_count = 0
        for _, row in group.iterrows():
            region_total_sum_insured += row["total_sum_insured"]
            region_total_policy_count += row["policy_count"]
            rows.append(
                {
                    "region": region,
                    "product_line": row["product_line"],
                    "total_sum_insured": round(row["total_sum_insured"], 2),
                    "policy_count": row["policy_count"],
                }
            )
        rows.append(
            {
                "region": region,
                "product_line": "ALL",
                "total_sum_insured": round(region_total_sum_insured, 2),
                "policy_count": region_total_policy_count,
            }
        )

    return pd.DataFrame(rows)
