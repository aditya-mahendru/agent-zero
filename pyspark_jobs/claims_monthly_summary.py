import sys

from pyspark.sql import functions as F


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    claims = spark.read.csv(f"{data_dir}/claims.csv", header=True, inferSchema=True)

    joined = claims.join(policies, claims.policy_id == policies.policy_id, "inner")

    claim_month = F.when(claims.claim_date.isNull(), F.lit(None)).otherwise(
        F.trunc(claims.claim_date, "month")
    )

    status_group = (
        F.when(claims.status.isin("Approved", "Paid"), F.lit("Settled"))
        .when(claims.status == "Rejected", F.lit("Declined"))
        .otherwise(F.lit("Pending"))
    )

    result = (
        joined.withColumn("claim_month", claim_month)
        .withColumn("status_group", status_group)
        .groupBy(policies.product_line, "claim_month", "status_group")
        .agg(
            F.count(F.lit(1)).alias("claim_count"),
            F.round(F.sum(claims.claim_amount), 2).alias("total_claim_amount"),
        )
        .orderBy("claim_month", "product_line")
    )

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("claims_monthly_summary")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
