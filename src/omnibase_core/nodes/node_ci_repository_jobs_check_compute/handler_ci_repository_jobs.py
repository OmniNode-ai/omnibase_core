# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerCiRepositoryJobs — repositories of the same type inherit the same CI.

RULING 2026-10-14T19:54:41Z (OMN-17427): "Everything should be this exact
same for repositories similar type" and RULING 2026-10-14T20:01:09Z:
"all CI should be in core and everything should essentially inherit from that".
New inline jobs are refused unless they live in a reusable workflow in the
host repository. Existing repository-specific jobs are reported as one WARN
per file. Jobs calling reusable workflows are judged by HandlerCiInheritance.

With a baseline (OMN-21277) the base no longer excuses a job: a typed
repository's inline job passes only when its shrink-only baseline lists it.
An entry the base baseline did not list (new or re-added) fails, an entry
naming no inline job is stale and fails, and a first baseline may list only
inline jobs the base workflows already carry.

Architecture: pure COMPUTE handler — deterministic, no I/O, no clock. Workflow
text arrives as explicit (path, source) pairs; YAML parsing operates only on
those strings. The CLI owns filesystem reads and output.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Literal

import yaml

from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = [
    "VALIDATOR_ID",
    "HandlerCiRepositoryJobs",
    "repository_specific_jobs",
]

VALIDATOR_ID: Final[str] = "ci_repository_jobs_check"

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


def repository_specific_jobs(
    source: str, path: str, repository: str, host: str
) -> list[str]:
    """Return repository-specific job locations; invalid YAML raises YAMLError."""
    # A workflow is GitHub's schema, not an ONEX contract: read it as plain data.
    document: object = yaml.load(source, Loader=yaml.SafeLoader)
    if not isinstance(document, Mapping):
        return []
    jobs = document.get("jobs")
    if not isinstance(jobs, Mapping):
        return []

    # PyYAML's YAML 1.1 resolver reads an unquoted `on` key as boolean True.
    trigger = document.get("on", document.get(True))
    reusable = trigger == "workflow_call" or (
        isinstance(trigger, (list, Mapping)) and "workflow_call" in trigger
    )
    if repository.casefold() == host.casefold() and reusable:
        return []

    return [
        f"{path}:jobs.{job_id}"
        for job_id, job in jobs.items()
        if not (isinstance(job, Mapping) and "uses" in job)
    ]


class HandlerCiRepositoryJobs:
    """Refuse new repository-specific jobs outside the host's reusable workflows."""

    def handle(self, request: ModelCiInheritanceCheckInput) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355). Pure, no I/O, no clock."""
        if request.baseline is not None:
            return _report(self._baseline_findings(request))
        host = request.host_repository
        repository = host if request.repository is None else request.repository
        base_jobs: set[tuple[str, str]] = set()
        for file in request.base_files:
            try:
                locations = repository_specific_jobs(
                    file.source, file.path, repository, host
                )
            except yaml.YAMLError:
                continue
            base_jobs.update(
                (file.path, location.removeprefix(f"{file.path}:jobs."))
                for location in locations
            )

        findings: list[ModelValidationFinding] = []
        for file in sorted(request.head_files, key=lambda f: f.path):
            try:
                locations = repository_specific_jobs(
                    file.source, file.path, repository, host
                )
            except yaml.YAMLError as error:
                findings.append(_invalid_yaml(file.path, error))
                continue

            existing = 0
            for location in locations:
                job_id = location.removeprefix(f"{file.path}:jobs.")
                if (file.path, job_id) in base_jobs:
                    existing += 1
                    continue
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location=location,
                        message=(
                            f"{location}: new repository-specific CI job '{job_id}' "
                            f"(defined inline in {repository}, not inherited from {host})"
                        ),
                        remediation=(
                            "Add the job to a reusable workflow (on: workflow_call) in "
                            f"{request.organization}/{host} and call it from this "
                            "repository with uses:, so every repository of the same "
                            "type runs the same CI (RULINGs 2026-10-14T19:54:41Z and "
                            "2026-10-14T20:01:09Z, OMN-17427)."
                        ),
                    )
                )
            if existing:
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="WARN",
                        location=file.path,
                        message=(
                            f"{file.path}: {existing} existing repository-specific "
                            f"job(s) not inherited from {host}"
                        ),
                        remediation=None,
                    )
                )

        return _report(findings)

    def _baseline_findings(
        self, request: ModelCiInheritanceCheckInput
    ) -> list[ModelValidationFinding]:
        """Judge the head against the shrink-only baseline (OMN-21277)."""
        baseline = request.baseline
        if baseline is None:
            return []
        host = request.host_repository
        repository = host if request.repository is None else request.repository
        if baseline.repository.casefold() != repository.casefold():
            return [
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    location="baseline",
                    message=(
                        f"baseline names repository {baseline.repository}, "
                        f"not the checked repository {repository}"
                    ),
                    remediation=None,
                )
            ]
        listed = set(baseline.entries)
        findings: list[ModelValidationFinding] = []
        head_jobs: set[str] = set()
        for file in sorted(request.head_files, key=lambda f: f.path):
            try:
                locations = repository_specific_jobs(
                    file.source, file.path, repository, host
                )
            except yaml.YAMLError as error:
                findings.append(_invalid_yaml(file.path, error))
                continue
            head_jobs.update(locations)
            carried = 0
            for location in locations:
                if location in listed:
                    carried += 1
                    continue
                job_id = location.removeprefix(f"{file.path}:jobs.")
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location=location,
                        message=(
                            f"{location}: repository-specific CI job '{job_id}' of "
                            f"{baseline.repository_type} repository {repository} is "
                            "not in its CI inheritance baseline"
                        ),
                        remediation=(
                            "Run the job from a reusable workflow (on: workflow_call) "
                            f"in {request.organization}/{host} called with uses:; the "
                            "baseline only shrinks (RULINGs 2026-10-14T19:54:41Z and "
                            "2026-10-14T20:01:09Z, OMN-21277)."
                        ),
                    )
                )
            if carried:
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="WARN",
                        location=file.path,
                        message=(
                            f"{file.path}: {carried} baselined repository-specific "
                            f"job(s) not inherited from {host}"
                        ),
                        remediation=None,
                    )
                )

        allowed: set[str] | None = None
        if request.compare_base:
            if request.base_baseline is not None:
                allowed = set(request.base_baseline.entries)
            else:
                allowed = set()
                for file in request.base_files:
                    try:
                        allowed.update(
                            repository_specific_jobs(
                                file.source, file.path, repository, host
                            )
                        )
                    except yaml.YAMLError:
                        continue
        for entry in baseline.entries:
            if entry not in head_jobs:
                findings.append(
                    _entry_fail(entry, "names no inline job of the head; delete it")
                )
            elif allowed is not None and entry not in allowed:
                reason = (
                    "is not in the base baseline; the baseline only shrinks"
                    if request.base_baseline is not None
                    else "names no inline job of the base; a first baseline "
                    "lists only jobs the base already carries"
                )
                findings.append(_entry_fail(entry, reason))
        return findings


def _invalid_yaml(path: str, error: yaml.YAMLError) -> ModelValidationFinding:
    return ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity="ERROR",
        location=path,
        message=f"{path}: workflow is not valid YAML: {str(error).splitlines()[0]}",
        remediation=None,
    )


def _entry_fail(entry: str, reason: str) -> ModelValidationFinding:
    return ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity="FAIL",
        location=f"baseline:{entry}",
        message=f"CI inheritance baseline entry {entry} {reason}",
        remediation=(
            "Remove the entry; a job leaves the baseline by moving into a reusable "
            "omnibase_core workflow and never comes back (OMN-21277)."
        ),
    )


def _report(findings: list[ModelValidationFinding]) -> ModelValidationReport:
    embedded = tuple(
        ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
        for finding in findings
    )
    return ModelValidationReport.from_findings(
        findings=embedded,
        request=ModelValidationRequestRef(profile=_PROFILE),
        validators_run=(VALIDATOR_ID,),
    )
