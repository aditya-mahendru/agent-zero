import sys

from pyspark.sql.functions import col, count, lit, quarter, sum as spark_sum, when, year


def run(spark, data_dir: str):
    policies = spark.read.csv(f"{data_dir}/policies.csv", header=True, inferSchema=True)
    claims = spark.read.csv(f"{data_dir}/claims.csv", header=True, inferSchema=True)

    joined = claims.join(
        policies, policies["policy_id"] == claims["policy_id"], "inner"
    )

    result = (
        joined.groupBy(
            col("product_line"),
            year(col("claim_date")).alias("claim_year"),
            quarter(col("claim_date")).alias("claim_quarter"),
        )
        .agg(
            spark_sum(when(claims["status"] == "Open", lit(1)).otherwise(lit(0))).alias(
                "open_count"
            ),
            spark_sum(
                when(claims["status"] == "Approved", lit(1)).otherwise(lit(0))
            ).alias("approved_count"),
            spark_sum(
                when(claims["status"] == "Rejected", lit(1)).otherwise(lit(0))
            ).alias("rejected_count"),
            spark_sum(when(claims["status"] == "Paid", lit(1)).otherwise(lit(0))).alias(
                "paid_count"
            ),
            count(lit(1)).alias("total_claims"),
        )
        .orderBy("claim_year", "claim_quarter", "product_line")
        .select(
            "product_line",
            "claim_year",
            "claim_quarter",
            "open_count",
            "approved_count",
            "rejected_count",
            "paid_count",
            "total_claims",
        )
    )

    return result


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .appName("claims_status_rollup_by_quarter")
        .getOrCreate()
    )
    df = run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")
    df.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)
