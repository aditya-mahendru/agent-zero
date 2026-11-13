"""Test-generation agent: given a migrated PySpark job, asks Claude to
write a pytest test module for it.

Usage:
    python -m agents.testgen <job_name>
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from agents.common import (
    AgentOutputError,
    call_claude,
    extract_code_block,
    validate_job_name,
)

PYSPARK_DIR = Path(__file__).parent.parent / "pyspark_jobs"
OUTPUT_DIR = Path(__file__).parent.parent / "tests"


def build_prompt(job_name: str, code: str) -> str:
    return f"""You are writing pytest tests for a PySpark migration job.
Respond with ONLY Python code (one ```python fenced block, no other prose).

The module under test is `pyspark_jobs.{job_name}`, exposing
`run(spark, data_dir: str) -> DataFrame`. Write a pytest module that:
- Has a module-scoped `spark` fixture: `SparkSession.builder.master("local[1]").appName("test_{job_name}").getOrCreate()`,
  and stops it at the end of the session.
- Calls `generate_synthetic_data.main()`-equivalent by running the
  repo's `data/generate_synthetic_data.py` script via `subprocess` once
  (module-scoped fixture), pointed at a temp directory is NOT needed --
  just use the repo's `data/` directory directly as `data_dir`.
- Asserts the returned DataFrame is non-empty (`df.count() > 0`).
- Asserts the DataFrame's column list is non-empty and has no duplicate
  column names.
- Converts the result `.toPandas()` and asserts there are no fully-null
  rows.

Keep it short -- 3-5 focused test functions, no reconciliation-against-
baseline logic (that's handled by a separate reconciliation engine).

PySpark job source:
```python
{code}
```
"""


def validate(code: str) -> None:
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise AgentOutputError(f"Generated test code has a syntax error: {e}") from e
    if "def test_" not in code:
        raise AgentOutputError("Generated test code has no test_ function")


def run(job_name: str) -> Path:
    validate_job_name(job_name)
    job_path = PYSPARK_DIR / f"{job_name}.py"
    code = job_path.read_text()

    prompt = build_prompt(job_name, code)
    response = call_claude(prompt)
    test_code = extract_code_block(response)
    validate(test_code)

    out_path = OUTPUT_DIR / f"test_{job_name}.py"
    out_path.write_text(test_code + "\n" if not test_code.endswith("\n") else test_code)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    path = run(sys.argv[1])
    print(f"Wrote test module to {path}")
