# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A shape-gate detector must run on every PR, whatever the preflight says (OMN-20298).

Every shape-gate failure in the 30 days before 2026-10-01 was the change-control
preflight failing first: the detector job was either skipped behind
``needs: occ-preflight`` or began with a step that exits 1 when the preflight
result is not success. The detector never ran, so no PR carried a detector
result. This guard refuses both shapes in ``.github/workflows``.

A job is a shape-gate detector when its id, name, called workflow, or any step
(name, ``uses``, ``with``, ``run``) names one of the shape detectors in
``DETECTOR_PATTERN``. Aggregator jobs that only read ``needs.<job>.result`` do
not count: those references are stripped before matching.

A detector job is refused when:

* it transitively needs a preflight job and its ``if`` does not run it
  regardless (``always()``), because the job is skipped when the preflight
  fails; or
* any of its steps reads the preflight job's result or outputs.

The guard has no baseline, no allowlist and no suppression comment.

Usage::

    python -m omnibase_core.handlers.handler_shape_gate_independence [workflow.yml ...]

With no paths, every file under ``.github/workflows`` is scanned.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

from omnibase_core.models.validation.model_shape_gate_independence_finding import (
    ModelShapeGateIndependenceFinding,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

DEFAULT_WORKFLOW_DIR = Path(".github/workflows")

DETECTOR_PATTERN = re.compile(
    r"canonical[_-]inference|check-canonical-inference"
    r"|url[_-]authority"
    r"|plugin[_-]daemon"
    r"|hardcoded[_-]model[_-]config|validate_hardcoded_model"
    r"|canon[_-]shape"
    r"|noncanonical|non[_-]canonical"
    r"|imperative[_-]contract|imperative[_-]skills"
    r"|hardcoded[_-]topic|no-hardcoded-topics"
    r"|hardcoded[_-]ip|runner-ip"
    r"|plan-canonical-scripts|skill-backing-node"
    r"|deterministic-skills|instructional-skills"
    r"|no-functional-code|tutorial-canon-shape"
    r"|shape[_-]ratchet|shape[_-]gate|no[_-]new[_-](?:script|plugin)",
    re.IGNORECASE,
)
_RESULT_REF = re.compile(r"needs\.[\w-]+\.(?:result|outputs\.[\w-]+)")


def validate_paths(paths: Sequence[Path]) -> list[ModelShapeGateIndependenceFinding]:
    """Validate workflow files under the provided paths."""
    findings: list[ModelShapeGateIndependenceFinding] = []
    for path in _iter_workflow_files(paths):
        findings.extend(validate_file(path))
    return findings


def validate_file(path: Path) -> list[ModelShapeGateIndependenceFinding]:
    """Validate one workflow file."""
    try:
        document = load_yaml_mapping_no_duplicates(
            path.read_text(encoding="utf-8"), source=str(path)
        )
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        return [
            ModelShapeGateIndependenceFinding(
                path=path, job="<file>", reason=f"could not parse workflow: {exc}"
            )
        ]
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return []

    preflight = {
        job_id for job_id, job in jobs.items() if _is_preflight(str(job_id), job)
    }
    findings: list[ModelShapeGateIndependenceFinding] = []
    for job_id, job in jobs.items():
        if job_id in preflight or not isinstance(job, dict):
            continue
        if not _is_detector(str(job_id), job):
            continue
        findings.extend(_check_job(path, str(job_id), job, jobs, preflight))
    return findings


def _check_job(
    path: Path,
    job_id: str,
    job: Mapping[str, object],
    jobs: Mapping[str, object],
    preflight: set[str],
) -> list[ModelShapeGateIndependenceFinding]:
    findings: list[ModelShapeGateIndependenceFinding] = []
    blocking = _transitive_needs(job_id, jobs) & preflight
    runs_regardless = "always()" in str(job.get("if", ""))
    if blocking and not runs_regardless:
        findings.append(
            ModelShapeGateIndependenceFinding(
                path=path,
                job=job_id,
                reason=(
                    "is a shape-gate detector that needs "
                    f"{sorted(blocking)} and is skipped when the preflight fails; "
                    "remove the dependency so the detector always runs"
                ),
            )
        )
    for step in _steps(job):
        for ref in _preflight_refs(step, preflight):
            label = step.get("name") or step.get("run", "<step>")
            findings.append(
                ModelShapeGateIndependenceFinding(
                    path=path,
                    job=job_id,
                    reason=(
                        f"step '{str(label)[:60]}' reads {ref}; a detector never "
                        "branches on the preflight result"
                    ),
                )
            )
    return findings


def _is_preflight(job_id: str, job: object) -> bool:
    uses = job.get("uses", "") if isinstance(job, dict) else ""
    return "preflight" in job_id.lower() or "occ-preflight" in str(uses)


def _is_detector(job_id: str, job: Mapping[str, object]) -> bool:
    haystack = " ".join(
        [job_id, str(job.get("name", "")), str(job.get("uses", ""))]
        + [str(step) for step in _steps(job)]
    )
    return DETECTOR_PATTERN.search(_RESULT_REF.sub("", haystack)) is not None


def _steps(job: Mapping[str, object]) -> list[dict[str, object]]:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _preflight_refs(step: Mapping[str, object], preflight: set[str]) -> list[str]:
    refs: list[str] = []
    text = " ".join(str(value) for value in step.values())
    for match in _RESULT_REF.finditer(text):
        needed = match.group(0).split(".")[1]
        if needed in preflight and match.group(0) not in refs:
            refs.append(match.group(0))
    return refs


def _transitive_needs(job_id: str, jobs: Mapping[str, object]) -> set[str]:
    seen: set[str] = set()
    stack = [job_id]
    while stack:
        current = jobs.get(stack.pop())
        if not isinstance(current, dict):
            continue
        needs = current.get("needs", [])
        for needed in [needs] if isinstance(needs, str) else list(needs):
            if needed not in seen:
                seen.add(needed)
                stack.append(needed)
    return seen


def _iter_workflow_files(paths: Sequence[Path]) -> list[Path]:
    scan_paths = tuple(paths) or (DEFAULT_WORKFLOW_DIR,)
    files: list[Path] = []
    for path in scan_paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted([*path.glob("*.yml"), *path.glob("*.yaml")]))
    return files


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse shape-gate detector jobs that depend on the OCC preflight."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    findings = validate_paths(args.paths)
    for finding in findings:
        sys.stderr.write(f"{finding.format()}\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
