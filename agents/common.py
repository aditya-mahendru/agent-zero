"""Shared helpers for the discovery/translation/test-gen agents.

Every agent follows the same shape: build a prompt, call the real `claude`
CLI headlessly (`claude -p`), extract structured output from the response,
validate it against an explicit contract, and only then write it to disk.
Nothing the model returns is trusted until it passes validation.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

CLAUDE_TIMEOUT_SECONDS = 180
_JOB_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class AgentOutputError(Exception):
    """Raised when the model's output fails validation -- never written to disk."""


def log(message: str) -> None:
    """Print a timestamped, immediately-flushed progress line to stderr.

    `claude -p` is otherwise silent for 10-60s while it thinks -- this is
    what lets a human watching the agent run see each stage happen live,
    instead of a blank terminal followed by a single final line.
    """
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def validate_job_name(job_name: str) -> str:
    """job_name becomes a file path component (legacy/<job_name>.sql,
    pyspark_jobs/<job_name>.py, ...) -- reject anything that isn't a plain
    identifier before it reaches any path."""
    if not _JOB_NAME_RE.match(job_name):
        raise ValueError(
            f"Invalid job name {job_name!r}: must match {_JOB_NAME_RE.pattern}"
        )
    return job_name


def call_claude(prompt: str) -> str:
    """Run `claude -p <prompt>` headlessly and return its stdout."""
    log(f"Calling claude -p ({len(prompt)} chars of prompt)...")
    started = time.monotonic()
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT_SECONDS,
    )
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        log(f"claude -p failed after {elapsed:.1f}s")
        raise AgentOutputError(
            f"claude -p exited {result.returncode}: {result.stderr[:500]}"
        )
    log(f"claude -p responded in {elapsed:.1f}s ({len(result.stdout)} chars)")
    return result.stdout


_CODE_FENCE_RE = re.compile(r"```(?:[a-zA-Z]*)\n(.*?)```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_code_block(text: str) -> str:
    """Pull the first fenced code block out of a model response, or return
    the raw text if there's no fence (some responses are plain code)."""
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response (handling a
    fenced ```json block or bare JSON) and parse it."""
    fenced = _CODE_FENCE_RE.search(text)
    candidate = fenced.group(1).strip() if fenced else text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJECT_RE.search(candidate)
    if not match:
        raise AgentOutputError("No JSON object found in model output")
    return json.loads(match.group(0))


def legacy_job_path(job_name: str) -> Path:
    validate_job_name(job_name)
    root = Path(__file__).parent.parent / "legacy"
    for ext in (".sql", ".sas"):
        candidate = root / f"{job_name}{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No legacy job named {job_name} under legacy/")
