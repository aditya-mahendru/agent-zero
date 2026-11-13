import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs.claims_summary import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .appName("test_claims_summary")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module", autouse=True)
def synthetic_data():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "generate_synthetic_data.py")],
        cwd=REPO_ROOT,
        check=True,
    )


@pytest.fixture(scope="module")
def result_df(spark, synthetic_data):
    return run(spark, str(DATA_DIR))


def test_result_is_non_empty(result_df):
    assert result_df.count() > 0


def test_columns_are_non_empty_and_unique(result_df):
    columns = result_df.columns
    assert len(columns) > 0
    assert len(columns) == len(set(columns))


def test_no_fully_null_rows(result_df):
    pdf = result_df.toPandas()
    assert not pdf.isnull().all(axis=1).any()


def test_expected_columns_present(result_df):
    for col in (
        "claim_count",
        "total_claim_amount",
        "max_claim_amount",
        "severity_ratio",
        "severity_flag",
        "high_severity_count",
    ):
        assert col in result_df.columns


def test_severity_flag_values_are_valid(result_df):
    pdf = result_df.toPandas()
    assert set(pdf["severity_flag"].unique()).issubset({"HIGH", "MEDIUM", "LOW"})
