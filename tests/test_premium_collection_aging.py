import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs.premium_collection_aging import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .appName("test_premium_collection_aging")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module", autouse=True)
def synthetic_data():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "generate_synthetic_data.py")],
        cwd=str(REPO_ROOT),
        check=True,
    )


@pytest.fixture(scope="module")
def result_df(spark):
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
        "product_line",
        "region",
        "premium_id",
        "policy_id",
        "collection_delay_days",
        "aging_bucket",
        "premium_amount",
    }
    assert expected.issubset(set(result_df.columns))


def test_aging_bucket_values_are_valid(result_df):
    valid_buckets = {"On Time", "1-30 Days", "31-60 Days", "60+ Days"}
    pdf = result_df.select("aging_bucket").toPandas()
    assert set(pdf["aging_bucket"].unique()).issubset(valid_buckets)
