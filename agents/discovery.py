"""Discovery/lineage agent: reads a legacy job and asks Claude for its
column-level lineage (source columns -> target columns, with the
transformation applied) plus a migration-wave assignment.

Usage:
    python -m agents.discovery <job_name>   # e.g. policy_renewal_candidates
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agents.common import (
    AgentOutputError,
    call_claude,
    extract_json,
    legacy_job_path,
    log,
)

OUTPUT_DIR = Path(__file__).parent / "output" / "lineage"

REQUIRED_KEYS = {"source_tables", "target_columns", "migration_wave", "quirks"}
REQUIRED_TARGET_COLUMN_KEYS = {"name", "source_columns", "transformation"}


def build_prompt(job_name: str, source: str) -> str:
    return f"""You are a data lineage analyst migrating a legacy insurance data
platform. Analyse the following legacy job and respond with ONLY a single
JSON object (no prose, no markdown fences) with this exact shape:

{{
  "source_tables": ["policies", "claims"],
  "target_columns": [
    {{"name": "<output column name>", "source_columns": ["<table>.<column>", ...], "transformation": "<one-line description of how it's derived>"}}
  ],
  "migration_wave": <1, 2 or 3 -- 1 = simplest/no dependencies, 3 = most complex>,
  "quirks": ["<any legacy-specific gotcha a migration engineer must preserve, e.g. hardcoded dates, implicit fan-out joins, null-handling>"]
}}

Job name: {job_name}

Source code:
```
{source}
```
"""


def validate(lineage: dict) -> None:
    missing = REQUIRED_KEYS - lineage.keys()
    if missing:
        raise AgentOutputError(f"Lineage output missing keys: {missing}")
    if not isinstance(lineage["target_columns"], list) or not lineage["target_columns"]:
        raise AgentOutputError(
            "Lineage output must have a non-empty target_columns list"
        )
    for col in lineage["target_columns"]:
        missing_col_keys = REQUIRED_TARGET_COLUMN_KEYS - col.keys()
        if missing_col_keys:
            raise AgentOutputError(
                f"target_columns entry missing keys: {missing_col_keys}"
            )
    if not isinstance(lineage["quirks"], list):
        raise AgentOutputError("Lineage output's quirks must be a list")
    if lineage["migration_wave"] not in (1, 2, 3):
        raise AgentOutputError("migration_wave must be 1, 2 or 3")


def run(job_name: str) -> Path:
    log(f"discovery[{job_name}]: starting")
    job_path = legacy_job_path(job_name)
    log(
        f"discovery[{job_name}]: reading {job_path.relative_to(job_path.parent.parent)}"
    )
    source = job_path.read_text()

    prompt = build_prompt(job_name, source)
    log(
        f"discovery[{job_name}]: asking Claude for column-level lineage + migration wave"
    )
    response = call_claude(prompt)

    log(f"discovery[{job_name}]: extracting and validating lineage JSON")
    lineage = extract_json(response)
    validate(lineage)
    log(
        f"discovery[{job_name}]: valid -- {len(lineage['target_columns'])} target "
        f"columns, wave {lineage['migration_wave']}, {len(lineage['quirks'])} quirks flagged"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{job_name}.json"
    out_path.write_text(json.dumps(lineage, indent=2) + "\n")
    log(
        f"discovery[{job_name}]: wrote {out_path.relative_to(out_path.parent.parent.parent)}"
    )
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    path = run(sys.argv[1])
    print(f"Wrote lineage to {path}")
