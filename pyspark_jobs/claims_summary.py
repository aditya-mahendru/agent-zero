import sys

import pyspark.sql.functions as F
from pyspark.sql import Window


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    claims = spark.read.csv(f"{data_dir}/claims.csv", header=True, inferSchema=True)

    claims_agg = claims.groupBy("policy_id").agg(
        F.count(F.lit(1)).alias("claim_count"),
        F.sum("claim_amount").alias("total_claim_amount"),
        F.max("claim_amount").alias("max_claim_amount"),
    )

    # Left-outer merge keyed on policy_id: every policy row is kept (claims
    # zero-filled if absent); unmatched claim rows are silently dropped.
    merged = policies.join(claims_agg, on="policy_id", how="left")

    merged = (
        merged.withColumn("claim_count", F.coalesce(F.col("claim_count"), F.lit(0)))
        .withColumn(
            "total_claim_amount", F.coalesce(F.col("total_claim_amount"), F.lit(0))
        )
        .withColumn("max_claim_amount", F.coalesce(F.col("max_claim_amount"), F.lit(0)))
    )

    merged = merged.withColumn(
        "severity_ratio",
        F.when(
            F.col("sum_insured") > 0,
            F.col("max_claim_amount") / F.col("sum_insured"),
        ).otherwise(F.lit(0.0)),
    )

    merged = merged.withColumn(
        "severity_flag",
        F.when(F.col("severity_ratio") >= 0.5, F.lit("HIGH"))
        .when(F.col("severity_ratio") >= 0.25, F.lit("MEDIUM"))
        .otherwise(F.lit("LOW")),
    )

    # RETAIN high_severity_count: a running tally accumulated during the
    # policy_id-sorted merge pass (not a per-row/per-policy aggregate). It
    # must be computed in policy_id order before the final re-sort.
    merge_order_window = Window.orderBy("policy_id").rowsBetween(
        Window.unboundedPreceding, Window.currentRow
    )
    merged = merged.withColumn(
        "high_severity_count",
        F.sum(
            F.when(F.col("severity_flag") == "HIGH", F.lit(1)).otherwise(F.lit(0))
        ).over(merge_order_window),
    )

    output_cols = policies.columns + [
        "claim_count",
        "total_claim_amount",
        "max_claim_amount",
        "severity_ratio",
        "severity_flag",
        "high_severity_count",
    ]
    result = merged.select(*output_cols).orderBy("product_line", "policy_id")

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]").appName("claims_summary").getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
