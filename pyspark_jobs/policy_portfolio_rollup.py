import sys

import pyspark.sql.functions as F


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)

    policies_clean = policies.withColumn(
        "region",
        F.when(
            policies["region"].isNull() | (policies["region"] == ""), F.lit("UNKNOWN")
        ).otherwise(policies["region"]),
    )

    # PROC MEANS nway: class region, product_line; var sum_insured;
    # sum= ignores missing sum_insured, n= counts rows (not just non-missing sum_insured).
    portfolio_agg = policies_clean.groupBy("region", "product_line").agg(
        F.sum("sum_insured").alias("total_sum_insured"),
        F.count(F.lit(1)).alias("policy_count"),
    )

    # BY-group subtotal per region, injected as product_line = "ALL".
    region_totals = (
        portfolio_agg.groupBy("region")
        .agg(
            F.sum("total_sum_insured").alias("total_sum_insured"),
            F.sum("policy_count").alias("policy_count"),
        )
        .withColumn("product_line", F.lit("ALL"))
        .select("region", "product_line", "total_sum_insured", "policy_count")
    )

    detail = portfolio_agg.select(
        "region", "product_line", "total_sum_insured", "policy_count"
    )

    # Final sort by region, product_line only -- relies on "ALL" sorting after
    # real product_line values, matching the legacy proc sort BY statement exactly.
    result = detail.unionByName(region_totals).orderBy("region", "product_line")

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("policy_portfolio_rollup")
        .getOrCreate()
    )
    result_df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    result_df.toPandas().to_csv(
        sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False
    )
