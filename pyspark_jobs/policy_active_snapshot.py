import sys

from pyspark.sql import functions as F
from pyspark.sql.window import Window

SNAPSHOT_DATE = "2024-06-30"


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    premiums = spark.read.csv(f"{data_dir}/premiums.csv", header=True, inferSchema=True)

    premiums = premiums.withColumn("_tiebreak_id", F.monotonically_increasing_id())

    latest_prem_window = Window.partitionBy("policy_id").orderBy(
        F.col("collected_date").desc(), F.col("_tiebreak_id").desc()
    )

    latest_prem = (
        premiums.withColumn("rn", F.row_number().over(latest_prem_window))
        .filter(F.col("rn") == 1)
        .select(
            F.col("policy_id").alias("_latest_policy_id"),
            F.col("premium_amount").alias("latest_premium_amount"),
            F.col("collected_date").alias("latest_premium_collected_date"),
        )
    )

    joined = policies.join(
        latest_prem,
        policies.policy_id == latest_prem._latest_policy_id,
        "left",
    ).filter(F.col("start_date") <= F.lit(SNAPSHOT_DATE))

    result = joined.select(
        "policy_id",
        "customer_id",
        "product_line",
        "region",
        "sum_insured",
        F.when(F.col("status") == "Cancelled", F.lit("Cancelled"))
        .when(F.col("end_date") < F.lit(SNAPSHOT_DATE), F.lit("Expired"))
        .when(F.col("start_date") > F.lit(SNAPSHOT_DATE), F.lit("Not Yet Active"))
        .otherwise(F.lit("Active"))
        .alias("effective_status"),
        "latest_premium_amount",
        "latest_premium_collected_date",
    )

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("policy_active_snapshot")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
