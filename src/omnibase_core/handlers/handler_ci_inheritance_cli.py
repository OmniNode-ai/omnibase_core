# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI for CI reference inheritance and repository-specific jobs (OMN-17427).

The pre-commit hook and the ci.yml job both run the same pure handlers
(:class:`HandlerCiInheritance` and :class:`HandlerCiRepositoryJobs`); this
module owns the filesystem read through the ``node_source_file_gather_effect``
EFFECT node, report merging, and output for both rules.

The caller materializes the base workflows in a directory (CI: ``git archive``
of the pull request's base; pre-commit: of ``HEAD``) and passes it with
``--base-dir``; ``--head-dir`` is the working tree's workflow directory. This
module runs no git command.

Usage::

    python -m omnibase_core.handlers.handler_ci_inheritance_cli \\
        --base-dir /tmp/base/.github/workflows --head-dir .github/workflows

Exit codes: 0 — no FAIL or ERROR finding; 1 — otherwise.

Ticket: OMN-17427 (RULING 2026-10-14T20:01:09Z: all CI lives in core).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.handlers.handler_ci_inheritance import (
    VALIDATOR_ID,
    HandlerCiInheritance,
)
from omnibase_core.handlers.handler_ci_repository_jobs import (
    VALIDATOR_ID as JOBS_VALIDATOR_ID,
)
from omnibase_core.handlers.handler_ci_repository_jobs import (
    HandlerCiRepositoryJobs,
    repository_specific_jobs,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

__all__ = ["main"]

_DEFAULT_HEAD_DIR: Final[str] = ".github/workflows"
_DEFAULT_ORGANIZATION: Final[str] = "OmniNode-ai"
_DEFAULT_HOST: Final[str] = "omnibase_core"
_WORKFLOW_PATTERNS: Final[list[str]] = ["*.yml", "*.yaml"]


def _gather(directory: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Read the workflow files directly under ``directory`` (EFFECT boundary)."""
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(root=directory, include_patterns=_WORKFLOW_PATTERNS)
    )
    errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if skipped.reason.startswith(("read error:", "error checking file size:"))
    ]
    files = [
        ModelSourceFile(path=Path(f.path).name, source=f.source) for f in output.files
    ]
    return files, errors


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 when no FAIL or ERROR finding, else 1."""
    parser = argparse.ArgumentParser(
        prog="check-ci-inheritance",
        description=(
            "Refuse a change that adds a reusable workflow or action reference to an "
            "organization repository other than the CI host, or adds a "
            "repository-specific CI job (OMN-17427)."
        ),
    )
    parser.add_argument("--base-dir", required=True, help="Base workflow directory.")
    parser.add_argument(
        "--head-dir", default=_DEFAULT_HEAD_DIR, help="Head workflow directory."
    )
    parser.add_argument("--organization", default=_DEFAULT_ORGANIZATION)
    parser.add_argument("--host-repository", default=_DEFAULT_HOST)
    parser.add_argument(
        "--repository",
        default=None,
        help="Repository whose workflows are checked; defaults to the CI host.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical ValidationReport JSON on PASS, WARN, FAIL and ERROR.",
    )
    parsed = parser.parse_args(argv)

    runtime_errors: list[str] = []
    if not Path(parsed.base_dir).is_dir():
        runtime_errors.append(f"base directory {parsed.base_dir} does not exist")
    head_files, head_errors = _gather(parsed.head_dir)
    base_files: list[ModelSourceFile] = []
    if not runtime_errors:
        base_files, base_errors = _gather(parsed.base_dir)
        runtime_errors.extend(base_errors)
    runtime_errors.extend(head_errors)
    if not head_files:
        runtime_errors.append(
            f"zero workflow files read under {parsed.head_dir}: a run that reads "
            "nothing is ERROR, never PASS"
        )

    if runtime_errors:
        _write_report(
            parsed.report_json,
            ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, tuple(runtime_errors)
            ),
        )
        for error in runtime_errors:
            sys.stdout.write(f"ERROR: {error}\n")
        return 1

    request = ModelCiInheritanceCheckInput(
        organization=parsed.organization,
        host_repository=parsed.host_repository,
        repository=parsed.repository,
        base_files=base_files,
        head_files=head_files,
    )
    inheritance_report = HandlerCiInheritance().handle(request)
    jobs_report = HandlerCiRepositoryJobs().handle(request)
    report = ModelValidationReport.from_findings(
        findings=inheritance_report.findings + jobs_report.findings,
        request=ModelValidationRequestRef(profile="default"),
        validators_run=(VALIDATOR_ID, JOBS_VALIDATOR_ID),
    )
    _write_report(parsed.report_json, report)

    references = [f for f in report.findings if f.validator_id == VALIDATOR_ID]
    jobs = [f for f in report.findings if f.validator_id == JOBS_VALIDATOR_ID]
    fails = [f for f in references if f.severity in ("FAIL", "ERROR")]
    existing = [f for f in references if f.severity == "WARN"]
    if not fails:
        sys.stdout.write(
            f"OK: no new reusable CI reference outside {parsed.host_repository} "
            f"({len(existing)} existing reference(s) still hosted elsewhere)\n"
        )
    else:
        sys.stdout.write(
            f"FAIL: {len(fails)} new reusable CI reference(s) hosted outside "
            f"{parsed.host_repository}:\n"
        )
        for finding in fails:
            sys.stdout.write(f"  {finding.message}\n")
        sys.stdout.write(
            f"\nShared CI lives in {parsed.organization}/{parsed.host_repository} and every "
            "repository inherits it from there (RULING 2026-10-14T20:01:09Z, OMN-17427).\n"
        )

    job_fails = [f for f in jobs if f.severity in ("FAIL", "ERROR")]
    if not job_fails:
        repository = (
            request.host_repository
            if request.repository is None
            else request.repository
        )
        counts = [
            len(
                repository_specific_jobs(
                    file.source, file.path, repository, request.host_repository
                )
            )
            for file in request.head_files
        ]
        sys.stdout.write(
            "OK: no new repository-specific CI job "
            f"({sum(counts)} existing repository-specific job(s) across "
            f"{sum(count > 0 for count in counts)} file(s))\n"
        )
    else:
        sys.stdout.write(f"FAIL: {len(job_fails)} new repository-specific CI job(s):\n")
        for finding in job_fails:
            sys.stdout.write(f"  {finding.message}\n")
        sys.stdout.write(
            "\nRepositories of the same type run the same CI, hosted in "
            f"{parsed.organization}/{parsed.host_repository} "
            "(RULINGs 2026-10-14T19:54:41Z and 2026-10-14T20:01:09Z, OMN-17427).\n"
        )
    return 1 if fails or job_fails else 0


if __name__ == "__main__":
    sys.exit(main())
