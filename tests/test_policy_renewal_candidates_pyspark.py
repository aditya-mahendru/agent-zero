import subprocess
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs import policy_renewal_candidates

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .appName("test_policy_renewal_candidates")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module")
def synthetic_data():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "generate_synthetic_data.py")],
        cwd=REPO_ROOT,
        check=True,
    )
    return str(DATA_DIR)


@pytest.fixture(scope="module")
def result_df(spark, synthetic_data):
    return policy_renewal_candidates.run(spark, synthetic_data)


def test_result_is_non_empty(result_df):
    assert result_df.count() > 0


def test_columns_are_unique_and_non_empty(result_df):
    columns = result_df.columns
    assert len(columns) > 0
    assert len(columns) == len(set(columns))


def test_expected_columns_present(result_df):
    assert set(result_df.columns) == {
        "product_line",
        "renewal_candidate_count",
        "total_sum_insured_up_for_renewal",
    }


def test_no_fully_null_rows(result_df):
    pdf = result_df.toPandas()
    assert not pdf.isnull().all(axis=1).any()


def test_renewal_candidate_count_is_positive(result_df):
    pdf = result_df.toPandas()
    assert (pdf["renewal_candidate_count"] > 0).all()
