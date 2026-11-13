import pandas as pd
import pytest

from reconciliation import engine


def test_reconcile_passes_on_identical_frames():
    baseline = pd.DataFrame({"product_line": ["Motor", "Home"], "count": [2, 3]})
    migrated = baseline.copy()

    result = engine.reconcile("fake_job", baseline, migrated)

    assert result["overall_pass"] is True
    assert result["row_count_match"] is True
    assert result["record_level_match"] is True
    assert result["numeric_column_totals"]["count"]["match"] is True


def test_reconcile_fails_on_row_count_mismatch():
    baseline = pd.DataFrame({"product_line": ["Motor", "Home"], "count": [2, 3]})
    migrated = pd.DataFrame({"product_line": ["Motor"], "count": [2]})

    result = engine.reconcile("fake_job", baseline, migrated)

    assert result["overall_pass"] is False
    assert result["row_count_match"] is False


def test_reconcile_fails_on_numeric_total_mismatch():
    baseline = pd.DataFrame({"product_line": ["Motor", "Home"], "count": [2, 3]})
    migrated = pd.DataFrame({"product_line": ["Motor", "Home"], "count": [2, 4]})

    result = engine.reconcile("fake_job", baseline, migrated)

    assert result["overall_pass"] is False
    assert result["numeric_column_totals"]["count"]["match"] is False


def test_reconcile_fails_on_shuffled_records_with_matching_totals():
    """Matching row counts and column totals alone must not be enough for
    a PASS -- values can be shuffled between rows in a way that preserves
    both while the actual records are wrong."""
    baseline = pd.DataFrame({"policy_id": ["A", "B"], "amount": [10.0, 20.0]})
    migrated = pd.DataFrame({"policy_id": ["A", "B"], "amount": [20.0, 10.0]})

    result = engine.reconcile("fake_job", baseline, migrated)

    assert result["numeric_column_totals"]["amount"]["match"] is True
    assert result["row_count_match"] is True
    assert result["record_level_match"] is False
    assert result["overall_pass"] is False


def test_reconcile_treats_nan_and_none_as_the_same_missing_value():
    """A pandas-sourced baseline stringifies a missing value as "nan"; a
    PySpark-sourced (toPandas()) frame stringifies it as "None". Both mean
    the same thing and must not cause a spurious record-level mismatch."""
    baseline = pd.DataFrame({"policy_id": ["A"], "region": [float("nan")]})
    migrated = pd.DataFrame({"policy_id": ["A"], "region": [None]})

    result = engine.reconcile("fake_job", baseline, migrated)

    assert result["record_level_match"] is True


def test_reconcile_fails_on_missing_column():
    baseline = pd.DataFrame({"product_line": ["Motor"], "count": [2], "total": [10.0]})
    migrated = pd.DataFrame({"product_line": ["Motor"], "count": [2]})

    result = engine.reconcile("fake_job", baseline, migrated)

    assert result["overall_pass"] is False
    assert result["missing_columns"] == ["total"]


@pytest.mark.integration
def test_engine_runs_end_to_end_on_policy_renewal_candidates():
    pyspark_job = pytest.importorskip("pyspark_jobs.policy_renewal_candidates")  # noqa: F841
    outcome = engine.run("policy_renewal_candidates")
    assert outcome["overall_pass"] is True
