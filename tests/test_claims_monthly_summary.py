import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs import claims_monthly_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def spark():
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("test_claims_monthly_summary")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture(scope="module")
def generated_data():
    subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_synthetic_data.py")],
        cwd=str(REPO_ROOT),
        check=True,
    )
    return str(DATA_DIR)


@pytest.fixture(scope="module")
def result_df(spark, generated_data):
    return claims_monthly_summary.run(spark, generated_data)


def test_result_is_non_empty(result_df):
    assert result_df.count() > 0


def test_columns_are_present_and_unique(result_df):
    columns = result_df.columns
    assert len(columns) > 0
    assert len(columns) == len(set(columns))


def test_expected_columns_exist(result_df):
    expected = {
        "product_line",
        "claim_month",
        "status_group",
        "claim_count",
        "total_claim_amount",
    }
    assert expected.issubset(set(result_df.columns))


def test_no_fully_null_rows(result_df):
    pdf = result_df.toPandas()
    assert not pdf.isnull().all(axis=1).any()


def test_claim_count_is_positive(result_df):
    pdf = result_df.toPandas()
    assert (pdf["claim_count"] > 0).all()
