import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs.policy_active_snapshot import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def spark():
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("test_policy_active_snapshot")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture(scope="module", autouse=True)
def synthetic_data():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "generate_synthetic_data.py")],
        cwd=str(REPO_ROOT),
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
    expected = {
        "policy_id",
        "customer_id",
        "product_line",
        "region",
        "sum_insured",
        "effective_status",
        "latest_premium_amount",
        "latest_premium_collected_date",
    }
    assert expected.issubset(set(result_df.columns))


def test_effective_status_has_valid_values(result_df):
    pdf = result_df.toPandas()
    valid_statuses = {"Cancelled", "Expired", "Not Yet Active", "Active"}
    assert set(pdf["effective_status"].dropna().unique()).issubset(valid_statuses)
