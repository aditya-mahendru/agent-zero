import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs.claims_status_rollup_by_quarter import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def spark():
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("test_claims_status_rollup_by_quarter")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture(scope="module")
def generated_data():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "generate_synthetic_data.py")],
        cwd=REPO_ROOT,
        check=True,
    )
    return str(DATA_DIR)


@pytest.fixture(scope="module")
def result_df(spark, generated_data):
    return run(spark, generated_data)


def test_result_is_non_empty(result_df):
    assert result_df.count() > 0


def test_columns_are_non_empty_and_unique(result_df):
    columns = result_df.columns
    assert len(columns) > 0
    assert len(columns) == len(set(columns))


def test_expected_columns_present(result_df):
    expected = {
        "product_line",
        "claim_year",
        "claim_quarter",
        "open_count",
        "approved_count",
        "rejected_count",
        "paid_count",
        "total_claims",
    }
    assert expected.issubset(set(result_df.columns))


def test_no_fully_null_rows(result_df):
    pdf = result_df.toPandas()
    assert not pdf.isnull().all(axis=1).any()


def test_status_counts_sum_to_total(result_df):
    pdf = result_df.toPandas()
    summed = (
        pdf["open_count"]
        + pdf["approved_count"]
        + pdf["rejected_count"]
        + pdf["paid_count"]
    )
    assert (summed == pdf["total_claims"]).all()
