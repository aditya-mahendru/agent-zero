import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs.high_value_claims_review import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = str(REPO_ROOT / "data")


@pytest.fixture(scope="module")
def spark():
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("test_high_value_claims_review")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture(scope="module", autouse=True)
def synthetic_data():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "generate_synthetic_data.py")],
        cwd=REPO_ROOT,
        check=True,
    )


@pytest.fixture(scope="module")
def result_df(spark, synthetic_data):
    return run(spark, DATA_DIR)


def test_result_is_non_empty(result_df):
    assert result_df.count() > 0


def test_columns_are_non_empty_and_unique(result_df):
    columns = result_df.columns
    assert len(columns) > 0
    assert len(columns) == len(set(columns))


def test_no_fully_null_rows(result_df):
    pdf = result_df.toPandas()
    assert not pdf.isnull().all(axis=1).any()


def test_review_flag_values_are_valid(result_df):
    pdf = result_df.toPandas()
    allowed = {"REVIEW REQUIRED", "WATCH", "STANDARD"}
    assert set(pdf["review_flag"].unique()).issubset(allowed)


def test_excludes_rejected_claims(result_df):
    joined = result_df.toPandas()
    assert "claim_id" in joined.columns
    assert joined["claim_id"].notnull().all()
