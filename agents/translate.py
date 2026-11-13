"""Translation agent: given a legacy job and its lineage JSON, asks Claude
to write an equivalent PySpark job.

The generated job must expose `def run(spark, data_dir: str) -> DataFrame`
so the reconciliation engine (and tests) can call it directly, and a
`__main__` block that writes its output to reconciliation/outputs/<job>.csv.

Usage:
    python -m agents.translate <job_name>
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from agents.common import (
    AgentOutputError,
    call_claude,
    extract_code_block,
    legacy_job_path,
)

OUTPUT_DIR = Path(__file__).parent.parent / "pyspark_jobs"
LINEAGE_DIR = Path(__file__).parent / "output" / "lineage"


def build_prompt(job_name: str, source: str, lineage: dict) -> str:
    return f"""You are migrating a legacy insurance data job to PySpark.
Respond with ONLY Python code (one ```python fenced block, no other prose).

Requirements for the generated module:
- A function `run(spark, data_dir: str)` (no type hint on `spark` -- don't
  import pyspark.sql.SparkSession just to annotate it) that reads
  `policies.csv`, `claims.csv`, `premiums.csv` from `data_dir` with
  `spark.read.csv(..., header=True, inferSchema=True)` as needed, implements
  the SAME logic as the legacy job below -- including any quirks listed
  below, which must be preserved exactly, not "fixed" -- and returns a
  PySpark DataFrame with the same columns as the legacy job's output.
- A `if __name__ == "__main__":` block that builds a local SparkSession
  (`SparkSession.builder.master("local[1]").appName("{job_name}").getOrCreate()`),
  calls `run(spark, sys.argv[1] if len(sys.argv) > 1 else "data")`, and
  writes the result with `.toPandas().to_csv(sys.argv[2] if len(sys.argv) > 2 else "out.csv", index=False)`
  (pandas CSV output keeps row order and formatting easy to reconcile
  against the legacy baseline CSV -- do not use `.write.csv`, which
  shards output across multiple part-files).
- No PySpark SQL functions that require Hive; stick to pyspark.sql.functions.

Known quirks to preserve exactly: {json.dumps(lineage.get("quirks", []))}

Job name: {job_name}

Legacy source:
```
{source}
```
"""


def validate(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise AgentOutputError(f"Generated code has a syntax error: {e}") from e

    has_run = any(
        isinstance(node, ast.FunctionDef) and node.name == "run"
        for node in ast.walk(tree)
    )
    if not has_run:
        raise AgentOutputError("Generated code has no top-level `run` function")


def run(job_name: str) -> Path:
    source = legacy_job_path(job_name).read_text()
    lineage_path = LINEAGE_DIR / f"{job_name}.json"
    lineage = json.loads(lineage_path.read_text()) if lineage_path.exists() else {}

    prompt = build_prompt(job_name, source, lineage)
    response = call_claude(prompt)
    code = extract_code_block(response)
    validate(code)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{job_name}.py"
    out_path.write_text(code + "\n" if not code.endswith("\n") else code)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    path = run(sys.argv[1])
    print(f"Wrote PySpark job to {path}")
