import sys

import pyspark.sql.functions as F


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    claims = spark.read.csv(f"{data_dir}/claims.csv", header=True, inferSchema=True)
    premiums = spark.read.csv(f"{data_dir}/premiums.csv", header=True, inferSchema=True)

    pol = policies.select(
        "policy_id",
        F.coalesce(F.col("region"), F.lit("UNKNOWN")).alias("region"),
        "product_line",
    )

    pol_claims = pol.join(
        claims.select("policy_id", "claim_amount"), on="policy_id", how="left"
    )

    pol_premiums = policies.select("policy_id").join(
        premiums.select("policy_id", "premium_amount"), on="policy_id", how="left"
    )

    fanned = pol_claims.join(pol_premiums, on="policy_id", how="left")

    grouped = fanned.groupBy("region", "product_line").agg(
        F.sum("claim_amount").alias("claim_sum"),
        F.sum("premium_amount").alias("premium_sum"),
    )

    result = grouped.select(
        "region",
        "product_line",
        F.round(F.col("claim_sum"), 2).alias("total_claims"),
        F.round(F.col("premium_sum"), 2).alias("total_premium"),
        F.round(
            F.col("claim_sum")
            / F.when(F.col("premium_sum") == 0, F.lit(None)).otherwise(
                F.col("premium_sum")
            ),
            4,
        ).alias("loss_ratio"),
    )

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("claims_loss_ratio_by_region")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
