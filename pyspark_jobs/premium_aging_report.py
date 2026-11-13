import sys

from pyspark.sql import Window
from pyspark.sql import functions as F


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    premiums = spark.read.csv(f"{data_dir}/premiums.csv", header=True, inferSchema=True)

    pol = policies.select(
        F.col("policy_id").alias("pol_policy_id"),
        F.col("product_line"),
        F.col("region"),
    )

    joined = premiums.join(pol, premiums.policy_id == pol.pol_policy_id, "inner").drop(
        "pol_policy_id"
    )

    delay = F.datediff(F.col("collected_date"), F.col("period_start"))

    with_bucket = joined.select(
        "premium_id",
        "policy_id",
        "period_start",
        "period_end",
        "payment_frequency",
        "premium_amount",
        "collected_date",
        "product_line",
        "region",
        delay.alias("collection_delay_days"),
    ).withColumn(
        "aging_bucket",
        F.when(
            F.col("collection_delay_days").isNull()
            | (F.col("collection_delay_days") <= 0),
            F.lit("On Time"),
        )
        .when(F.col("collection_delay_days") <= 30, F.lit("1-30 Days"))
        .when(F.col("collection_delay_days") <= 60, F.lit("31-60 Days"))
        .otherwise(F.lit("60+ Days")),
    )

    running_window = (
        Window.partitionBy("product_line")
        .orderBy("policy_id")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )

    result = (
        with_bucket.withColumn(
            "overdue_increment",
            F.when(
                F.col("aging_bucket") != F.lit("On Time"), F.col("premium_amount")
            ).otherwise(F.lit(0.0)),
        )
        .withColumn(
            "running_overdue_total", F.sum("overdue_increment").over(running_window)
        )
        .drop("overdue_increment")
    )

    result = result.orderBy("product_line", "policy_id")

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("premium_aging_report")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
