"""Run the reconciliation engine for every legacy job that has both a
baseline CSV and a migrated PySpark job, and write a single rollup table
to reconciliation/report.md.

Usage:
    python -m reconciliation.run_all
"""

from __future__ import annotations

from pathlib import Path

from reconciliation import engine

PYSPARK_DIR = Path(__file__).parent.parent / "pyspark_jobs"
BASELINE_DIR = Path(__file__).parent.parent / "legacy" / "baselines"
REPORT_PATH = Path(__file__).parent / "report.md"


def discover_jobs() -> list[str]:
    migrated = {p.stem for p in PYSPARK_DIR.glob("*.py") if p.stem != "__init__"}
    baselined = {
        p.stem for p in BASELINE_DIR.glob("*.csv") if "_sqlserver" not in p.stem
    }
    return sorted(migrated & baselined)


def main() -> None:
    jobs = discover_jobs()
    if not jobs:
        print("No jobs with both a baseline and a migrated PySpark job yet.")
        return

    spark = engine._get_spark()
    results = []
    try:
        for job in jobs:
            try:
                results.append(engine.run(job, spark=spark))
            except Exception as e:  # noqa: BLE001 -- a failed job stays FAIL, not a crash
                results.append({"job": job, "overall_pass": False, "error": str(e)})
    finally:
        spark.stop()

    lines = ["# Reconciliation rollup", "", "| Job | Status | Notes |", "|---|---|---|"]
    for r in results:
        status = "PASS" if r.get("overall_pass") else "FAIL"
        note = r.get("error", "")
        if not note and not r.get("overall_pass"):
            note = (
                f"row_count_match={r.get('row_count_match')}, "
                f"record_level_match={r.get('record_level_match')}, "
                f"missing_columns={r.get('missing_columns')}"
            )
        lines.append(f"| {r['job']} | {status} | {note} |")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"Wrote rollup to {REPORT_PATH}")
    for r in results:
        print(f"  {r['job']}: {'PASS' if r.get('overall_pass') else 'FAIL'}")


if __name__ == "__main__":
    main()
