# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerCiRepositoryJobs — repositories of the same type inherit the same CI.

RULING 2026-10-14T19:54:41Z (OMN-17427): "Everything should be this exact
same for repositories similar type" and RULING 2026-10-14T20:01:09Z:
"all CI should be in core and everything should essentially inherit from that".
New inline jobs are refused unless they live in a reusable workflow in the
host repository. Existing repository-specific jobs are reported as one WARN
per file. Jobs calling reusable workflows are judged by HandlerCiInheritance.

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
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="ERROR",
                        location=file.path,
                        message=(
                            f"{file.path}: workflow is not valid YAML: "
                            f"{str(error).splitlines()[0]}"
                        ),
                        remediation=None,
                    )
                )
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

        embedded = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for finding in findings
        )
        return ModelValidationReport.from_findings(
            findings=embedded,
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
