# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for CI reference inheritance and repository-specific jobs (OMN-17427, OMN-21518).

The pre-commit hook and the ci.yml job both run the same pure handlers
(:class:`HandlerCiInheritance` and :class:`HandlerCiRepositoryJobs`); this
module owns the filesystem read through the ``node_source_file_gather_effect``
EFFECT node, the rule data read from ``contracts/ci_inheritance.validation.yaml``,
the report writer resolved from the container, report merging, and output for
both rules.

The caller materializes the base workflows in a directory (CI: ``git archive``
of the pull request's base; pre-commit: of ``HEAD``) and passes it with
``--base-dir``; ``--head-dir`` is the working tree's workflow directory. This
module runs no git command.

``--baseline`` names the repository's shrink-only CI inheritance baseline
(OMN-21277): an inline job passes only when it lists the job, whatever the
base carried. ``--base-baseline`` names the base revision's copy; a path that
does not exist means the base carries none. With ``--baseline`` and no
``--base-dir`` only the head baseline is enforced. :func:`main_emitting`
runs the same checks and publishes one validator-triggered event per failing
validator through an injected bus ``publish`` call; :func:`main` does the same over an
in-process in-memory bus (OMN-21277, RULING 2026-10-14T20:01:09Z).

Usage::

    python -m omnibase_core.nodes.node_ci_inheritance_check_compute.runtime_ci_inheritance_check \\
        --base-dir /tmp/base/.github/workflows --head-dir .github/workflows \\
        --baseline .onex_ratchets/ci_inheritance_baseline.yaml \\
        --base-baseline /tmp/base/.onex_ratchets/ci_inheritance_baseline.yaml

Exit codes: 0 — no FAIL or ERROR finding; 1 — otherwise.

Ticket: OMN-17427 (RULING 2026-10-14T20:01:09Z: all CI lives in core).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from functools import cache
from importlib import resources
from pathlib import Path
from uuid import uuid4

import yaml
from pydantic import ValidationError

from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_baseline import (
    ModelCiInheritanceBaseline,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_reference_input import (
    ModelCiInheritanceReferenceInput,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_rules import (
    ModelCiInheritanceRules,
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
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_input import (
    ModelValidatorTriggeredEmitInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_ci_inheritance_check_compute.handler_ci_inheritance import (
    VALIDATOR_ID,
    HandlerCiInheritance,
)
from omnibase_core.nodes.node_ci_repository_jobs_check_compute.handler_ci_repository_jobs import (
    VALIDATOR_ID as JOBS_VALIDATOR_ID,
)
from omnibase_core.nodes.node_ci_repository_jobs_check_compute.handler_ci_repository_jobs import (
    HandlerCiRepositoryJobs,
    repository_specific_jobs,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_triggered_emit import (
    HandlerValidatorTriggeredEmit,
    PublishFn,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

__all__ = [
    "build_container",
    "load_cli_defaults",
    "load_contract",
    "main",
    "main_emitting",
    "rules_from_contract",
]


@cache
def load_contract() -> ModelValidatorSubcontract:
    """The ci_inheritance validation contract shipped inside the package."""
    raw = resources.files("omnibase_core.validation").joinpath(
        "contracts/ci_inheritance.validation.yaml"
    )
    return load_yaml_content_as_model(raw.read_text("utf-8"), ModelValidatorSubcontract)


def _row(contract: ModelValidatorSubcontract, rule_id: str) -> ModelValidatorRule:
    return {row.rule_id: row for row in contract.rules}[rule_id]


def rules_from_contract(
    contract: ModelValidatorSubcontract,
) -> ModelCiInheritanceRules:
    """The handler's rule data, read from the rule rows of ``contract``."""
    return ModelCiInheritanceRules(
        uses_pattern=rule_string(
            _row(contract, "org_reference_pattern"), "uses_pattern"
        ),
        new_reference_message=rule_string(
            _row(contract, "new_org_reference"), "message_template"
        ),
        new_reference_remediation=rule_string(
            _row(contract, "new_org_reference"), "remediation_template"
        ),
        existing_reference_message=rule_string(
            _row(contract, "existing_org_reference"), "message_template"
        ),
    )


def load_cli_defaults(
    contract: ModelValidatorSubcontract | None = None,
) -> tuple[str, str, str, tuple[str, ...]]:
    """Head directory, organization, host repository and workflow patterns defaults."""
    row = _row(contract or load_contract(), "command_line_defaults")
    return (
        rule_string(row, "head_dir"),
        rule_string(row, "organization"),
        rule_string(row, "host_repository"),
        rule_strings(row, "workflow_patterns"),
    )


def build_container() -> ModelONEXContainer:
    """The composition root: a container with the report writer registered."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry()
    run_coro_sync(
        registry.register_instance(
            NodeValidationReportWriteEffect, NodeValidationReportWriteEffect()
        )
    )
    return container


def _gather(directory: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Read the workflow files directly under ``directory`` (EFFECT boundary)."""
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=directory, include_patterns=list(load_cli_defaults()[3])
        )
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


def _read_baseline(
    path: str, *, required: bool
) -> tuple[ModelCiInheritanceBaseline | None, list[str]]:
    """Read and parse one baseline file (EFFECT boundary for the read)."""
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(Path(path).parent),
            include_patterns=[Path(path).name],
            explicit_paths=[path],
        )
    )
    if not output.files:
        if not required and not Path(path).exists():
            return None, []
        reasons = [skipped.reason for skipped in output.skipped] or ["not read"]
        return None, [f"baseline {path}: {reasons[0]}"]
    try:
        # The baseline is plain data validated by its Pydantic model below.
        data: object = yaml.load(output.files[0].source, Loader=yaml.SafeLoader)
        return ModelCiInheritanceBaseline.model_validate(data), []
    except (yaml.YAMLError, ValidationError) as error:
        return None, [f"baseline {path}: {str(error).splitlines()[0]}"]


def _write_report(
    path: str | None,
    report: ModelValidationReport,
    container: ModelONEXContainer,
) -> None:
    if path is not None:
        writer = container.get_service(NodeValidationReportWriteEffect)
        writer.handle(ModelValidationReportWriteInput(report_path=path, report=report))


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 when no FAIL or ERROR finding, else 1.

    Each triggered validator is published as an event on an in-process
    in-memory bus, the bus every check runtime here dispatches over; a caller
    holding a broker-backed bus calls :func:`main_emitting` with its ``publish``.
    """
    return asyncio.run(_main_on_inmemory_bus(argv))


async def _main_on_inmemory_bus(argv: list[str] | None) -> int:
    bus = EventBusInmemory()
    await bus.start()
    try:
        return await main_emitting(argv, bus.publish)
    finally:
        await bus.shutdown()


async def main_emitting(
    argv: list[str] | None,
    publish: PublishFn,
    *,
    pull_request: int | None = None,
    head_sha: str | None = None,
    container: ModelONEXContainer | None = None,
) -> int:
    """Run :func:`main` and publish one validator-triggered event per failing validator."""
    exit_code, report, repository = _run(argv, container or build_container())
    await HandlerValidatorTriggeredEmit(publish).handle(
        ModelValidatorTriggeredEmitInput(
            report=report,
            repository=repository,
            pull_request=pull_request,
            head_sha=head_sha,
            correlation_id=uuid4(),
        )
    )
    return exit_code


def _run(
    argv: list[str] | None, container: ModelONEXContainer
) -> tuple[int, ModelValidationReport, str]:
    default_head_dir, default_organization, default_host, _ = load_cli_defaults()
    parser = argparse.ArgumentParser(
        prog="check-ci-inheritance",
        description=(
            "Refuse a change that adds a reusable workflow or action reference to an "
            "organization repository other than the CI host, or adds a "
            "repository-specific CI job (OMN-17427)."
        ),
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Base workflow directory; may be omitted only with --baseline.",
    )
    parser.add_argument(
        "--head-dir", default=default_head_dir, help="Head workflow directory."
    )
    parser.add_argument("--organization", default=default_organization)
    parser.add_argument("--host-repository", default=default_host)
    parser.add_argument(
        "--repository",
        default=None,
        help="Repository whose workflows are checked; defaults to the CI host.",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Shrink-only CI inheritance baseline of the checked repository (OMN-21277).",
    )
    parser.add_argument(
        "--base-baseline",
        default=None,
        help="The base revision's baseline; a missing file means the base has none.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical ValidationReport JSON on PASS, WARN, FAIL and ERROR.",
    )
    parsed = parser.parse_args(argv)

    repository = (
        parsed.host_repository if parsed.repository is None else parsed.repository
    )
    runtime_errors: list[str] = []
    if parsed.base_dir is None:
        if parsed.baseline is None:
            runtime_errors.append("--base-dir is required without --baseline")
    elif not Path(parsed.base_dir).is_dir():
        runtime_errors.append(f"base directory {parsed.base_dir} does not exist")
    head_files, head_errors = _gather(parsed.head_dir)
    base_files: list[ModelSourceFile] = []
    if not runtime_errors and parsed.base_dir is not None:
        base_files, base_errors = _gather(parsed.base_dir)
        runtime_errors.extend(base_errors)
    runtime_errors.extend(head_errors)
    baseline: ModelCiInheritanceBaseline | None = None
    base_baseline: ModelCiInheritanceBaseline | None = None
    if parsed.baseline is not None:
        baseline, baseline_errors = _read_baseline(parsed.baseline, required=True)
        runtime_errors.extend(baseline_errors)
    if parsed.base_baseline is not None:
        base_baseline, baseline_errors = _read_baseline(
            parsed.base_baseline, required=False
        )
        runtime_errors.extend(baseline_errors)
    if not head_files:
        runtime_errors.append(
            f"zero workflow files read under {parsed.head_dir}: a run that reads "
            "nothing is ERROR, never PASS"
        )

    if runtime_errors:
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
        _write_report(parsed.report_json, error_report, container)
        for error in runtime_errors:
            sys.stdout.write(f"ERROR: {error}\n")
        return 1, error_report, repository

    request = ModelCiInheritanceCheckInput(
        organization=parsed.organization,
        host_repository=parsed.host_repository,
        repository=parsed.repository,
        base_files=base_files,
        head_files=head_files,
        baseline=baseline,
        base_baseline=base_baseline,
        compare_base=parsed.base_dir is not None,
    )
    inheritance_report = HandlerCiInheritance().handle(
        ModelCiInheritanceReferenceInput(
            check=request, rules=rules_from_contract(load_contract())
        )
    )
    jobs_report = HandlerCiRepositoryJobs().handle(request)
    report = ModelValidationReport.from_findings(
        findings=inheritance_report.findings + jobs_report.findings,
        request=ModelValidationRequestRef(profile="default"),
        validators_run=(VALIDATOR_ID, JOBS_VALIDATOR_ID),
    )
    _write_report(parsed.report_json, report, container)

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
        counts = [
            len(
                repository_specific_jobs(
                    file.source, file.path, repository, request.host_repository
                )
            )
            for file in request.head_files
        ]
        kind = "existing" if baseline is None else "baselined"
        sys.stdout.write(
            "OK: no new repository-specific CI job "
            f"({sum(counts)} {kind} repository-specific job(s) across "
            f"{sum(count > 0 for count in counts)} file(s))\n"
        )
    else:
        sys.stdout.write(
            f"FAIL: {len(job_fails)} repository-specific CI job or baseline finding(s):\n"
            if baseline is not None
            else f"FAIL: {len(job_fails)} new repository-specific CI job(s):\n"
        )
        for finding in job_fails:
            sys.stdout.write(f"  {finding.message}\n")
        sys.stdout.write(
            "\nRepositories of the same type run the same CI, hosted in "
            f"{parsed.organization}/{parsed.host_repository} "
            "(RULINGs 2026-10-14T19:54:41Z and 2026-10-14T20:01:09Z, OMN-17427).\n"
        )
    return (1 if fails or job_fails else 0), report, repository


if __name__ == "__main__":
    sys.exit(main())
