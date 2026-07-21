# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Standalone-workflow validator classification gate (OMN-14430).

``test_live_ci_rollup_is_airtight`` (``test_validator_rollup_coverage.py``) proves
the Model-B rollup is airtight for the small set of validators governed by
``architecture-handshakes/validator-requirements.yaml``. It structurally cannot
say anything about a ``.github/workflows/validator-*.yml`` file that is NOT part
of that governed spec — and most of omnibase_core's standalone validator
workflows are not: they are point checks that predate or sit outside the Model-B
pilot. A file in that class which independently triggers on ``pull_request`` gets
its own ``github.run_id``, structurally invisible to ``ci.yml``'s ``ci-summary``
poller (``scripts/ci/ci_summary_gate.py`` queries only its own run's jobs) —
regardless of anything in the governed spec.

This module closes that residual: EVERY ``validator-*.yml`` workflow file is
classified into exactly one bucket in
``architecture-handshakes/standalone-validator-debt.yaml`` —
``migrated_into_ci_yml`` (preferred fix), ``natively_required_contexts`` (gated by
branch protection independent of ci-summary), or ``decorative_debt`` (confirmed
gate-nothing, tracked). A NEW standalone validator workflow that triggers on
``pull_request`` without being classified fails this gate CLOSED. A classified
entry that no longer matches the live file (renamed, retired, re-triggered) is
flagged as stale rather than silently ignored.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from omnibase_core.models.validation.model_standalone_validator_gap import (
    ModelStandaloneValidatorGap,
)

__all__ = ["verify_standalone_validator_registry"]


def _load_yaml(
    path: Path,
) -> dict[str, Any]:  # ONEX_EXCLUDE: dict_str_any — raw YAML document
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(  # error-ok: shape validation at load boundary
            f"{path} must parse to a mapping"
        )
    return data


def _triggers_on_pull_request(  # ONEX_EXCLUDE: dict_str_any — raw workflow YAML document
    workflow: dict[str, Any],
) -> bool:
    # PyYAML parses the bare `on:` key as the boolean-True key in YAML 1.1.
    untyped_workflow: dict[Any, Any] = workflow
    on = untyped_workflow.get("on", untyped_workflow.get(True))
    if isinstance(on, dict):
        return "pull_request" in on
    if isinstance(on, list):
        return "pull_request" in on
    return on == "pull_request"


def _job_context_names(  # ONEX_EXCLUDE: dict_str_any — raw workflow YAML document
    workflow: dict[str, Any],
) -> set[str]:
    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, dict):
        return set()
    names: set[str] = set()
    for job_id, job in jobs.items():
        if job_id == "occ-preflight" or not isinstance(job, dict):
            continue
        name = job.get("name")
        names.add(str(name) if name else str(job_id))
    return names


def verify_standalone_validator_registry(
    *, repo_root: Path, debt_manifest_path: Path
) -> list[ModelStandaloneValidatorGap]:
    """Return classification gaps. Empty list means every standalone validator
    workflow that gates on ``pull_request`` is accounted for, and every registry
    entry still matches a live file.

    Raises:
        ValueError: If the debt manifest is malformed (fail loud, never silent).
    """
    manifest = _load_yaml(debt_manifest_path)

    migrated = manifest.get("migrated_into_ci_yml", [])
    natively_required = manifest.get("natively_required_contexts", [])
    decorative = manifest.get("decorative_debt", [])
    for label, bucket in (
        ("migrated_into_ci_yml", migrated),
        ("natively_required_contexts", natively_required),
        ("decorative_debt", decorative),
    ):
        if not isinstance(bucket, list):
            raise ValueError(  # error-ok: manifest shape validation
                f"{label} must be a list, got {type(bucket).__name__}"
            )

    # workflow_file -> declared context(s)/status, built from every bucket.
    declared_by_file: dict[str, dict[str, Any]] = {}  # ONEX_EXCLUDE: dict_str_any
    for entry in natively_required:
        declared_by_file.setdefault(entry["workflow_file"], {"bucket": "native"})
        declared_by_file[entry["workflow_file"]].setdefault("contexts", set()).add(
            entry["context"]
        )
    for entry in decorative:
        declared_by_file.setdefault(entry["workflow_file"], {"bucket": "decorative"})
        declared_by_file[entry["workflow_file"]].setdefault("contexts", set()).add(
            entry["context"]
        )
    migrated_files = {entry["workflow_file"] for entry in migrated}

    workflows_dir = repo_root / ".github" / "workflows"
    gaps: list[ModelStandaloneValidatorGap] = []

    live_files = sorted(p.name for p in workflows_dir.glob("validator-*.yml"))

    for filename in live_files:
        workflow = _load_yaml(workflows_dir / filename)
        gates_on_pr = _triggers_on_pull_request(workflow)
        contexts = _job_context_names(workflow)

        if filename in migrated_files:
            if gates_on_pr:
                gaps.append(
                    ModelStandaloneValidatorGap(
                        workflow_file=filename,
                        detail=(
                            "listed in migrated_into_ci_yml but still triggers on "
                            "pull_request — either the ci.yml migration regressed "
                            "or this file must be reclassified"
                        ),
                    )
                )
            continue

        if not gates_on_pr:
            # Not an independent-run_id producer (workflow_dispatch-only, or
            # push-only) — nothing to classify. If it is stale-declared as
            # decorative/native below, flag that instead.
            declared = declared_by_file.get(filename)
            if declared is not None:
                gaps.append(
                    ModelStandaloneValidatorGap(
                        workflow_file=filename,
                        detail=(
                            f"declared in {declared['bucket']}_* but no longer "
                            "triggers on pull_request — move it to "
                            "migrated_into_ci_yml or remove the stale entry"
                        ),
                    )
                )
            continue

        declared = declared_by_file.get(filename)
        if declared is None:
            gaps.append(
                ModelStandaloneValidatorGap(
                    workflow_file=filename,
                    detail=(
                        f"triggers on pull_request with context(s) {sorted(contexts)} "
                        "but is not classified in "
                        "architecture-handshakes/standalone-validator-debt.yaml — "
                        "add it to migrated_into_ci_yml, natively_required_contexts, "
                        "or decorative_debt"
                    ),
                )
            )
            continue

        declared_contexts = declared.get("contexts", set())
        if not declared_contexts.issubset(contexts):
            gaps.append(
                ModelStandaloneValidatorGap(
                    workflow_file=filename,
                    detail=(
                        f"declared context(s) {sorted(declared_contexts)} do not "
                        f"match live job context(s) {sorted(contexts)} — stale entry"
                    ),
                )
            )

    live_file_set = set(live_files)
    for label, entries in (
        ("migrated_into_ci_yml", migrated),
        ("natively_required_contexts", natively_required),
        ("decorative_debt", decorative),
    ):
        for entry in entries:
            wf = entry["workflow_file"]
            if wf not in live_file_set:
                gaps.append(
                    ModelStandaloneValidatorGap(
                        workflow_file=wf,
                        detail=(
                            f"declared in {label} but no matching file exists at "
                            f"{workflows_dir / wf} — remove the stale entry"
                        ),
                    )
                )

    return gaps
