import sys

from pyspark.sql import functions as F


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    premiums = spark.read.csv(f"{data_dir}/premiums.csv", header=True, inferSchema=True)

    pol = policies.select(
        F.col("policy_id").alias("pol_policy_id"),
        F.col("product_line"),
        F.coalesce(F.col("region"), F.lit("UNKNOWN")).alias("region"),
    )

    joined = premiums.join(pol, premiums.policy_id == pol.pol_policy_id, "inner")

    delay = F.datediff(F.col("collected_date"), F.col("period_start"))

    result = joined.select(
        F.col("product_line"),
        F.col("region"),
        F.col("premium_id"),
        F.col("policy_id"),
        delay.alias("collection_delay_days"),
        F.when(delay <= 0, F.lit("On Time"))
        .when(delay.between(1, 30), F.lit("1-30 Days"))
        .when(delay.between(31, 60), F.lit("31-60 Days"))
        .otherwise(F.lit("60+ Days"))
        .alias("aging_bucket"),
        F.col("premium_amount"),
    )

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("premium_collection_aging")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
