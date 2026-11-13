import subprocess
import sys

import pytest
from pyspark.sql import SparkSession

from pyspark_jobs.claims_loss_ratio_by_region import run

DATA_DIR = "data"


@pytest.fixture(scope="module")
def spark():
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("test_claims_loss_ratio_by_region")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture(scope="module")
def synthetic_data():
    subprocess.run(
        [sys.executable, "data/generate_synthetic_data.py"],
        check=True,
        cwd=".",
    )
    return DATA_DIR


def test_result_is_non_empty(spark, synthetic_data):
    df = run(spark, synthetic_data)
    assert df.count() > 0


def test_columns_are_present_and_unique(spark, synthetic_data):
    df = run(spark, synthetic_data)
    columns = df.columns
    assert len(columns) > 0
    assert len(columns) == len(set(columns))


def test_expected_columns_present(spark, synthetic_data):
    df = run(spark, synthetic_data)
    expected = {
        "region",
        "product_line",
        "total_claims",
        "total_premium",
        "loss_ratio",
    }
    assert expected.issubset(set(df.columns))


def test_no_fully_null_rows(spark, synthetic_data):
    df = run(spark, synthetic_data)
    pdf = df.toPandas()
    assert not pdf.isnull().all(axis=1).any()


def test_region_has_no_nulls(spark, synthetic_data):
    df = run(spark, synthetic_data)
    pdf = df.toPandas()
    assert pdf["region"].notnull().all()
