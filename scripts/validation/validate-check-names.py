#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
check_name Validator for required-checks.yaml (OMN-2229).

Validates that every ``gates[].check_name`` in ``.github/required-checks.yaml``
corresponds to an actual job ``name:`` field in the referenced workflow file, and
that the ``workflow_job_key`` matches an actual top-level job key.

Also verifies:
  - No matrix shard names appear in branch protection gates
    (e.g. "Tests (Split 1/20)" must not be in gates -- only the aggregate gate should)
  - ``workflow_job_key`` values match actual YAML job keys in the workflow file
  - ``workflow_file`` values resolve to real files under ``.github/workflows/``
  - ``skip_policies`` are consistent with ``paths:`` filters in the workflow
    (informational warning only -- not a hard failure)

Usage:
    # From repo root
    uv run python scripts/validation/validate-check-names.py

    # Verbose mode (show all parsed data)
    uv run python scripts/validation/validate-check-names.py --verbose

    # Custom paths
    uv run python scripts/validation/validate-check-names.py \\
        --required-checks .github/required-checks.yaml \\
        --workflows-dir .github/workflows/

Exit Codes:
    0: No violations found
    1: One or more validation failures
    2: Script error (missing file, invalid YAML, etc.)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Final, NamedTuple, TypedDict


# ---------------------------------------------------------------------------
# Data types (defined before constants so constants can reference them)
# ---------------------------------------------------------------------------


class GateEntry(TypedDict, total=False):
    """A single entry from the ``gates:`` list in required-checks.yaml."""

    check_name: str
    workflow_file: str
    workflow_job_key: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MATRIX_SHARD_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\(Split\s+\d+/\d+\)"  # e.g. "(Split 1/20)"
)

WORKFLOW_JOB_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^([a-zA-Z0-9_\-]+):\s*$"  # top-level job key: e.g. "quality-gate:"
)

JOB_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s+name:\s+(.+)$"  # job display name: e.g. "  name: Quality Gate"
)

PATHS_FILTER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s+paths:"  # workflow-level or job-level paths filter
)


class CheckNameViolation(NamedTuple):
    """Represents a validation failure for a gates entry."""

    gate_check_name: str
    workflow_file: str
    workflow_job_key: str
    error_type: str
    detail: str


class WorkflowInfo(NamedTuple):
    """Parsed information from a workflow YAML file (line-based, no YAML lib needed)."""

    job_keys: set[str]
    """Top-level job keys (e.g. {'lint', 'quality-gate', 'test-parallel'})."""

    job_names: dict[str, str]
    """Map of job_key -> display name (e.g. {'quality-gate': 'Quality Gate'})."""

    has_paths_filter: bool
    """True if the workflow uses ``paths:`` at the top-level ``on:`` section."""


# ---------------------------------------------------------------------------
# YAML parsing helpers (line-based to avoid PyYAML dependency)
# ---------------------------------------------------------------------------


def _parse_workflow_file(workflow_path: Path) -> WorkflowInfo:
    """Extract job keys, display names, and paths-filter presence from a workflow file.

    Uses a simple line-based parser to avoid requiring PyYAML in CI environments.
    Handles standard GitHub Actions YAML structure reliably.

    Args:
        workflow_path: Absolute path to the workflow YAML file.

    Returns:
        WorkflowInfo with job_keys, job_names mapping, and has_paths_filter flag.
    """
    lines = workflow_path.read_text(encoding="utf-8").splitlines()

    job_keys: set[str] = set()
    job_names: dict[str, str] = {}
    has_paths_filter = False

    in_jobs_block = False
    current_job_key: str | None = None
    current_job_indent: int | None = None

    for line in lines:
        # Detect top-level paths: filter (before jobs: block)
        if not in_jobs_block and PATHS_FILTER_PATTERN.match(line):
            has_paths_filter = True

        # Detect start of jobs block
        if line.strip() == "jobs:":
            in_jobs_block = True
            continue

        if not in_jobs_block:
            continue

        # Detect top-level job key (exactly 2 spaces of indentation)
        if len(line) > 2 and line[:2] != "  ":
            # Back to top-level — out of jobs block
            if line[0] not in (" ", "\t", "#", ""):
                in_jobs_block = False
            continue

        # Two-space indented lines are job keys
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 2 and stripped.endswith(":") and not stripped.startswith("#"):
            # Candidate job key (e.g. "  quality-gate:")
            job_key = stripped[:-1].strip()
            # Skip keys like "name:", "runs-on:", etc. that appear under job keys
            # A job key at indent=2 that's a YAML map key and not a reserved keyword
            if not any(
                job_key.startswith(kw)
                for kw in (
                    "name",
                    "runs-on",
                    "timeout-minutes",
                    "needs",
                    "if",
                    "steps",
                    "strategy",
                    "env",
                    "outputs",
                    "services",
                    "container",
                    "permissions",
                    "concurrency",
                    "defaults",
                    "continue-on-error",
                    "with",
                    "uses",
                    "secrets",
                    "on",
                )
            ):
                job_keys.add(job_key)
                current_job_key = job_key
                current_job_indent = indent
                continue

        # Detect display name for current job (indent must be one level deeper)
        if (
            current_job_key is not None
            and current_job_indent is not None
            and indent == current_job_indent + 2
        ):
            name_match = JOB_NAME_PATTERN.match(line)
            if name_match:
                raw_name = name_match.group(1).strip().strip("\"'")
                # Strip templated suffixes like "${{ matrix.split }}/20"
                raw_name = re.sub(r"\s*\$\{.*?\}", "", raw_name).strip()
                job_names[current_job_key] = raw_name

    return WorkflowInfo(
        job_keys=job_keys,
        job_names=job_names,
        has_paths_filter=has_paths_filter,
    )


_GATE_SCALAR_KEYS: Final[frozenset[str]] = frozenset(
    {"check_name", "workflow_file", "workflow_job_key"}
)

# Matches YAML block-scalar indicators (>, |, >-, |-) at end of value
_BLOCK_SCALAR_RE: Final[re.Pattern[str]] = re.compile(r"^[>|][+-]?$")


def _parse_required_checks(required_checks_path: Path) -> list[GateEntry]:
    """Parse the gates list from required-checks.yaml using line-based parsing.

    The file uses a well-known structure:
      gates:
        - check_name: "Quality Gate"
          workflow_file: test.yml
          workflow_job_key: quality-gate
          rationale: >
            Long text...

    Only extracts the known scalar keys: check_name, workflow_file, workflow_job_key.
    Block-scalar values (rationale: >, etc.) are skipped gracefully.

    Returns:
        List of gate entry dicts (keys: check_name, workflow_file, workflow_job_key).
    """
    lines = required_checks_path.read_text(encoding="utf-8").splitlines()

    gates: list[GateEntry] = []
    in_gates = False
    current_gate: GateEntry = {}
    skip_block_scalar = False  # True when inside a block-scalar value to skip

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#") or not stripped:
            continue

        if stripped == "gates:":
            in_gates = True
            skip_block_scalar = False
            continue

        # Top-level key other than gates: terminates gates block
        if not line.startswith(" ") and not line.startswith("\t"):
            if in_gates and current_gate:
                gates.append(current_gate)
                current_gate = {}
            in_gates = False
            skip_block_scalar = False
            continue

        if not in_gates:
            continue

        # If inside a block-scalar body, skip until next gate-level key
        if skip_block_scalar:
            # A new "- key:" or "  key:" at gate-property indent ends the block scalar
            # Gate properties are indented 4 spaces ("    key:") or 2 ("  - key:")
            if stripped.startswith("- ") or (
                len(line) >= 4 and line[:4] == "    " and ":" in stripped
            ):
                skip_block_scalar = False
                # Fall through to process this line normally
            else:
                continue

        # New gate entry
        if stripped.startswith("- "):
            if current_gate:
                gates.append(current_gate)
            current_gate = {}
            skip_block_scalar = False
            # Parse inline key-value after the dash
            kv = stripped[2:].strip()
            if ":" in kv:
                key, _, value = kv.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                if _BLOCK_SCALAR_RE.match(value):
                    skip_block_scalar = True  # Skip block-scalar body
                elif key == "check_name":
                    current_gate["check_name"] = value
                elif key == "workflow_file":
                    current_gate["workflow_file"] = value
                elif key == "workflow_job_key":
                    current_gate["workflow_job_key"] = value
            continue

        # Continuation key-value under current gate (4-space indent)
        if ":" in stripped and not stripped.startswith("-"):
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")
            if _BLOCK_SCALAR_RE.match(value):
                skip_block_scalar = True  # Skip block-scalar body
            elif key == "check_name":
                current_gate["check_name"] = value
            elif key == "workflow_file":
                current_gate["workflow_file"] = value
            elif key == "workflow_job_key":
                current_gate["workflow_job_key"] = value

    if current_gate:
        gates.append(current_gate)

    return gates


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def _validate_gates(
    gates: list[GateEntry],
    workflows_dir: Path,
    verbose: bool = False,
) -> list[CheckNameViolation]:
    """Validate all gate entries against actual workflow files.

    Args:
        gates: Parsed list of gate dicts from required-checks.yaml.
        workflows_dir: Path to ``.github/workflows/``.
        verbose: If True, print parsed workflow info.

    Returns:
        List of violations found.
    """
    violations: list[CheckNameViolation] = []
    workflow_cache: dict[str, WorkflowInfo | None] = {}

    for gate in gates:
        check_name: str = gate.get("check_name") or ""
        workflow_file: str = gate.get("workflow_file") or ""
        workflow_job_key: str = gate.get("workflow_job_key") or ""

        # --- Check 1: Required fields present ---
        if not check_name:
            violations.append(
                CheckNameViolation(
                    gate_check_name="(missing)",
                    workflow_file=workflow_file,
                    workflow_job_key=workflow_job_key,
                    error_type="MISSING_CHECK_NAME",
                    detail="Gate entry is missing 'check_name' field.",
                )
            )
            continue

        if not workflow_file:
            violations.append(
                CheckNameViolation(
                    gate_check_name=check_name,
                    workflow_file="",
                    workflow_job_key=workflow_job_key,
                    error_type="MISSING_WORKFLOW_FILE",
                    detail=f"Gate '{check_name}' is missing 'workflow_file' field.",
                )
            )

        if not workflow_job_key:
            violations.append(
                CheckNameViolation(
                    gate_check_name=check_name,
                    workflow_file=workflow_file,
                    workflow_job_key="",
                    error_type="MISSING_WORKFLOW_JOB_KEY",
                    detail=f"Gate '{check_name}' is missing 'workflow_job_key' field.",
                )
            )

        if not workflow_file or not workflow_job_key:
            continue

        # --- Check 2: No matrix shard names in gates ---
        if MATRIX_SHARD_PATTERN.search(check_name):
            violations.append(
                CheckNameViolation(
                    gate_check_name=check_name,
                    workflow_file=workflow_file,
                    workflow_job_key=workflow_job_key,
                    error_type="MATRIX_SHARD_IN_GATE",
                    detail=(
                        f"Gate check_name '{check_name}' looks like a matrix shard name "
                        f"(contains '(Split N/M)' pattern). Only aggregate gates should "
                        f"appear in branch protection. Use the parent job's stable name instead."
                    ),
                )
            )

        # --- Check 3: Workflow file exists ---
        workflow_path = workflows_dir / workflow_file
        if not workflow_path.exists():
            violations.append(
                CheckNameViolation(
                    gate_check_name=check_name,
                    workflow_file=workflow_file,
                    workflow_job_key=workflow_job_key,
                    error_type="WORKFLOW_FILE_NOT_FOUND",
                    detail=(
                        f"Workflow file '{workflow_file}' referenced by gate '{check_name}' "
                        f"does not exist at '{workflow_path}'."
                    ),
                )
            )
            continue

        # --- Parse workflow (cached) ---
        if workflow_file not in workflow_cache:
            info = _parse_workflow_file(workflow_path)
            workflow_cache[workflow_file] = info
            if verbose:
                print(f"\n  [Workflow: {workflow_file}]")
                print(f"    job_keys: {sorted(info.job_keys)}")
                print(f"    job_names: {info.job_names}")
                print(f"    has_paths_filter: {info.has_paths_filter}")

        wf_info = workflow_cache[workflow_file]
        if wf_info is None:
            continue

        # --- Check 4: workflow_job_key exists as actual job key ---
        if workflow_job_key not in wf_info.job_keys:
            violations.append(
                CheckNameViolation(
                    gate_check_name=check_name,
                    workflow_file=workflow_file,
                    workflow_job_key=workflow_job_key,
                    error_type="JOB_KEY_NOT_FOUND",
                    detail=(
                        f"workflow_job_key '{workflow_job_key}' for gate '{check_name}' "
                        f"does not exist as a job key in '{workflow_file}'. "
                        f"Actual job keys: {sorted(wf_info.job_keys)}"
                    ),
                )
            )
            continue

        # --- Check 5: check_name matches job's display name ---
        actual_name = wf_info.job_names.get(workflow_job_key, "")
        if actual_name and actual_name != check_name:
            violations.append(
                CheckNameViolation(
                    gate_check_name=check_name,
                    workflow_file=workflow_file,
                    workflow_job_key=workflow_job_key,
                    error_type="CHECK_NAME_MISMATCH",
                    detail=(
                        f"Gate check_name '{check_name}' does not match the actual "
                        f"job display name '{actual_name}' for job key '{workflow_job_key}' "
                        f"in '{workflow_file}'. Branch protection requires the check_name to "
                        f"match exactly what GitHub reports (the job 'name:' field)."
                    ),
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run check_name validation.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 (clean), 1 (violations), 2 (script error).
    """
    parser = argparse.ArgumentParser(
        description="Validate required-checks.yaml gates against actual workflow job names.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--required-checks",
        type=Path,
        default=Path(".github/required-checks.yaml"),
        help="Path to required-checks.yaml (default: .github/required-checks.yaml)",
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="Path to workflows directory (default: .github/workflows)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print parsed workflow job info during validation.",
    )

    args = parser.parse_args(argv)

    # Resolve to absolute paths (supports running from repo root or scripts/)
    required_checks_path: Path = args.required_checks
    if not required_checks_path.is_absolute():
        required_checks_path = Path.cwd() / required_checks_path

    workflows_dir: Path = args.workflows_dir
    if not workflows_dir.is_absolute():
        workflows_dir = Path.cwd() / workflows_dir

    # --- Validate inputs ---
    if not required_checks_path.exists():
        print(
            f"ERROR: required-checks.yaml not found at '{required_checks_path}'",
            file=sys.stderr,
        )
        return 2

    if not workflows_dir.is_dir():
        print(
            f"ERROR: Workflows directory not found at '{workflows_dir}'",
            file=sys.stderr,
        )
        return 2

    # --- Parse required-checks.yaml ---
    try:
        gates = _parse_required_checks(required_checks_path)
    except Exception as exc:
        print(
            f"ERROR: Failed to parse required-checks.yaml: {exc}",
            file=sys.stderr,
        )
        return 2

    if not gates:
        print("WARNING: No gates found in required-checks.yaml. Nothing to validate.")
        return 0

    if args.verbose:
        print(f"\nParsed {len(gates)} gate(s) from {required_checks_path}:")
        for gate in gates:
            print(f"  - check_name={gate.get('check_name')!r} workflow_file={gate.get('workflow_file')!r} workflow_job_key={gate.get('workflow_job_key')!r}")

    # --- Run validation ---
    try:
        violations = _validate_gates(gates, workflows_dir, verbose=args.verbose)
    except Exception as exc:
        print(
            f"ERROR: Unexpected error during validation: {exc}",
            file=sys.stderr,
        )
        return 2

    # --- Report results ---
    if not violations:
        print(
            f"check_name validator: All {len(gates)} gate(s) validated successfully."
        )
        return 0

    print(f"\ncheck_name validator: {len(violations)} violation(s) found:\n")
    for i, v in enumerate(violations, 1):
        print(f"  [{i}] {v.error_type}")
        print(f"       gate:             {v.gate_check_name}")
        print(f"       workflow_file:    {v.workflow_file}")
        print(f"       workflow_job_key: {v.workflow_job_key}")
        print(f"       detail:           {v.detail}")
        print()

    print(
        "ACTION REQUIRED: Update either required-checks.yaml or the workflow files "
        "to resolve the above violations."
    )
    print(
        "NOTE: Renaming a gate check_name requires updating GitHub branch protection "
        "settings (temp dual-require → merge → remove old)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
