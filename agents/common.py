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
from pathlib import Path

CLAUDE_TIMEOUT_SECONDS = 180


class AgentOutputError(Exception):
    """Raised when the model's output fails validation -- never written to disk."""


def call_claude(prompt: str) -> str:
    """Run `claude -p <prompt>` headlessly and return its stdout."""
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise AgentOutputError(
            f"claude -p exited {result.returncode}: {result.stderr[:500]}"
        )
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
    root = Path(__file__).parent.parent / "legacy"
    for ext in (".sql", ".sas"):
        candidate = root / f"{job_name}{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No legacy job named {job_name} under legacy/")
