"""Reconciliation engine: runs a migrated PySpark job and diffs its output
against the legacy baseline for the same job -- row counts, per-column
numeric totals, and a full record-level comparison -- then writes a
pass/fail markdown report.

Usage:
    python -m reconciliation.engine <job_name>
    python -m reconciliation.run_all              # every job with both a
                                                    # baseline and a migrated job
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
BASELINE_DIR = ROOT / "legacy" / "baselines"
REPORT_DIR = Path(__file__).parent / "reports"
NUMERIC_TOLERANCE = 0.01

# Every baseline is an independent pandas reference implementation of the
# legacy job's logic, not output from the original engine -- see
# legacy/baselines/MANIFEST.md. This one job is the exception: its baseline
# was additionally validated against a real SQL Server 2022 run (538/538
# rows matched exactly). Reports must say which case applies -- never let a
# PASS read as "verified against the legacy engine" when it wasn't.
SQL_SERVER_VALIDATED_JOBS = {"claims_monthly_summary"}


def _get_spark():
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.master("local[1]")
        .appName("reconciliation")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def run_migrated_job(job_name: str, spark) -> pd.DataFrame:
    module = importlib.import_module(f"pyspark_jobs.{job_name}")
    df = module.run(spark, str(DATA_DIR))
    return df.toPandas()


def load_baseline(job_name: str) -> pd.DataFrame:
    path = BASELINE_DIR / f"{job_name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"No baseline for {job_name} -- run legacy/baselines/generate_baselines.py"
        )
    return pd.read_csv(path)


def reconcile(job_name: str, baseline: pd.DataFrame, migrated: pd.DataFrame) -> dict:
    result: dict = {"job": job_name}

    result["baseline_rows"] = len(baseline)
    result["migrated_rows"] = len(migrated)
    result["row_count_match"] = len(baseline) == len(migrated)

    common_cols = [c for c in baseline.columns if c in migrated.columns]
    result["missing_columns"] = sorted(set(baseline.columns) - set(migrated.columns))
    result["extra_columns"] = sorted(set(migrated.columns) - set(baseline.columns))

    numeric_checks = {}
    for col in common_cols:
        if pd.api.types.is_numeric_dtype(baseline[col]):
            b_sum = baseline[col].sum()
            m_sum = migrated[col].sum() if col in migrated else float("nan")
            numeric_checks[col] = {
                "baseline_sum": round(float(b_sum), 2),
                "migrated_sum": round(float(m_sum), 2),
                "match": bool(abs(b_sum - m_sum) <= NUMERIC_TOLERANCE),
            }
    result["numeric_column_totals"] = numeric_checks

    record_level_match = False
    if result["row_count_match"] and not result["missing_columns"]:
        sort_cols = [
            c for c in common_cols if baseline[c].dtype == object
        ] or common_cols
        try:
            b_cmp = baseline[common_cols].copy()
            m_cmp = migrated[common_cols].copy()
            for col in common_cols:
                if pd.api.types.is_numeric_dtype(b_cmp[col]):
                    # Round before comparing -- otherwise float32 vs float64
                    # or trailing-digit formatting differences between pandas
                    # and toPandas() would fail an otherwise-correct match.
                    b_cmp[col] = b_cmp[col].astype(float).round(2)
                    m_cmp[col] = m_cmp[col].astype(float).round(2)
                else:
                    # fillna before astype(str): a missing value stringifies
                    # as "nan" from pandas but "None" from a PySpark-sourced
                    # column, which would fail an otherwise-correct match.
                    # Use a sentinel distinct from any real value (not "")
                    # so a genuine null-vs-empty-string mismatch still fails.
                    b_cmp[col] = b_cmp[col].fillna("<NULL>").astype(str)
                    m_cmp[col] = m_cmp[col].fillna("<NULL>").astype(str)
            b_sorted = b_cmp.sort_values(sort_cols).reset_index(drop=True)
            m_sorted = m_cmp.sort_values(sort_cols).reset_index(drop=True)
            record_level_match = b_sorted.equals(m_sorted)
        except Exception:
            record_level_match = False
    result["record_level_match"] = record_level_match

    # A PASS requires every check, including record-level equality: matching
    # row counts and column totals alone can't rule out values shuffled
    # between rows in a way that preserves both.
    result["overall_pass"] = (
        result["row_count_match"]
        and not result["missing_columns"]
        and all(c["match"] for c in numeric_checks.values())
        and record_level_match
    )
    return result


def write_report(result: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if result["job"] in SQL_SERVER_VALIDATED_JOBS:
        provenance = (
            "pandas reference implementation of the legacy job's logic, "
            "additionally validated against a real SQL Server 2022 run for "
            "this job (538/538 rows matched exactly) -- see "
            "legacy/baselines/MANIFEST.md."
        )
    else:
        provenance = (
            "pandas reference implementation of the legacy job's logic -- "
            "**not** output from the original SQL Server/SAS engine. See "
            "legacy/baselines/MANIFEST.md."
        )
    lines = [
        f"# Reconciliation report: {result['job']}",
        "",
        f"**Overall: {'PASS' if result['overall_pass'] else 'FAIL'}**",
        "",
        f"**Baseline provenance:** {provenance}",
        "",
        f"- Baseline rows: {result['baseline_rows']}",
        f"- Migrated rows: {result['migrated_rows']}",
        f"- Row count match: {result['row_count_match']}",
        f"- Record-level match (full row equality after sort): {result['record_level_match']}",
        f"- Missing columns (in baseline, not migrated): {result['missing_columns'] or 'none'}",
        f"- Extra columns (in migrated, not baseline): {result['extra_columns'] or 'none'}",
        "",
        "## Numeric column totals",
        "",
        "| Column | Baseline sum | Migrated sum | Match |",
        "|---|---|---|---|",
    ]
    for col, check in result["numeric_column_totals"].items():
        lines.append(
            f"| {col} | {check['baseline_sum']} | {check['migrated_sum']} | {'✅' if check['match'] else '❌'} |"
        )
    lines.append("")

    out_path = REPORT_DIR / f"{result['job']}.md"
    out_path.write_text("\n".join(lines))
    return out_path


def run(job_name: str, spark=None) -> dict:
    own_spark = spark is None
    if own_spark:
        spark = _get_spark()
    try:
        baseline = load_baseline(job_name)
        migrated = run_migrated_job(job_name, spark)
        result = reconcile(job_name, baseline, migrated)
        write_report(result)
        return result
    finally:
        if own_spark:
            spark.stop()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    outcome = run(sys.argv[1])
    print(f"{outcome['job']}: {'PASS' if outcome['overall_pass'] else 'FAIL'}")
