import sys

import pyspark.sql.functions as F

AS_OF_DATE = "2024-09-01"
WINDOW_DAYS = 60


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    # claims.csv and premiums.csv are not used by this legacy job's logic,
    # but are read here for interface parity with other migrated jobs.
    spark.read.csv(f"{data_dir}/claims.csv", header=True, inferSchema=True)
    spark.read.csv(f"{data_dir}/premiums.csv", header=True, inferSchema=True)

    as_of_date = F.to_date(F.lit(AS_OF_DATE))
    window_end = F.date_add(as_of_date, WINDOW_DAYS)

    end_date = F.to_date(F.col("end_date"))

    filtered = policies.filter(
        (F.col("status") == "Active")
        & end_date.isNotNull()
        & (end_date >= as_of_date)
        & (end_date <= window_end)
    )

    result = (
        filtered.groupBy("product_line")
        .agg(
            F.count(F.lit(1)).alias("renewal_candidate_count"),
            F.round(F.sum("sum_insured"), 2).alias("total_sum_insured_up_for_renewal"),
        )
        .orderBy(F.col("renewal_candidate_count").desc())
    )

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("policy_renewal_candidates")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
