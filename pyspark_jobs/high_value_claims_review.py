import sys

from pyspark.sql import functions as F


def run(spark, data_dir: str):
    claims = spark.read.csv(f"{data_dir}/claims.csv", header=True, inferSchema=True)
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)

    joined = claims.alias("c").join(
        policies.alias("p"),
        F.col("p.policy_id") == F.col("c.policy_id"),
        "inner",
    )

    filtered = joined.filter(
        (F.col("c.status") != "Rejected") & F.col("c.status").isNotNull()
    )

    raw_ratio = F.col("c.claim_amount") / F.col("p.sum_insured")

    result = filtered.select(
        F.col("c.claim_id").alias("claim_id"),
        F.col("c.policy_id").alias("policy_id"),
        F.col("p.product_line").alias("product_line"),
        F.col("c.claim_amount").alias("claim_amount"),
        F.col("p.sum_insured").alias("sum_insured"),
        F.round(raw_ratio, 4).alias("claim_to_sum_insured_ratio"),
        F.when(raw_ratio >= 0.5, F.lit("REVIEW REQUIRED"))
        .when(raw_ratio >= 0.25, F.lit("WATCH"))
        .otherwise(F.lit("STANDARD"))
        .alias("review_flag"),
    )

    result = result.orderBy(F.col("claim_to_sum_insured_ratio").desc())

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("high_value_claims_review")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
