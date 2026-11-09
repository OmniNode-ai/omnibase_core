# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the cross-repository dependency-pin check (OMN-22360).

Backs the ``check-dependency-pins`` pre-commit hook, the reusable
``dependency-pins.yml`` workflow and manual runs. The git reads (release tags,
hook history) are ``NodeDependencyPinsCheckEffect``; the verdict is the pure
``checker_dependency_pins``; the report is written by
``node_validation_report_write_effect``.

Usage::

    check-dependency-pins                                  # the repository in the cwd
    check-dependency-pins ../omnibase_infra                # another repository
    check-dependency-pins --hook-history ../omnibase_core  # an existing hook clone
    check-dependency-pins --layer-order f.yaml --policy p.yaml --report-json r.json
    check-dependency-pins --today 2026-11-17               # judge hook rev exemptions as of a day

Exit codes: 0 -- PASS; 1 -- any finding, or the check could not run.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_dependency_pins_check_effect.handler import (
    NodeDependencyPinsCheckEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_dependency_pins import (
    ValidatorDependencyPins,
    load_dependency_pin_policy,
    load_layer_order,
)

__all__ = ["build_container", "main", "run"]

_FACTS_TOKEN = NodeDependencyPinsCheckEffect
_WRITER_TOKEN = NodeValidationReportWriteEffect


def build_container(
    *,
    facts_source: NodeDependencyPinsCheckEffect | None = None,
    report_writer: NodeValidationReportWriteEffect | None = None,
) -> ModelONEXContainer:
    """Register the two effects under their tokens; injection supports in-memory tests."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    if facts_source is None:
        run_coro_sync(
            registry.register_service(
                _FACTS_TOKEN,
                NodeDependencyPinsCheckEffect,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    else:
        run_coro_sync(registry.register_instance(_FACTS_TOKEN, facts_source))
    if report_writer is None:
        run_coro_sync(
            registry.register_service(
                _WRITER_TOKEN,
                NodeValidationReportWriteEffect,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    else:
        run_coro_sync(registry.register_instance(_WRITER_TOKEN, report_writer))
    return container


def run(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Judge the named repositories (or the cwd) and persist the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--repo")
    parser.add_argument("--layer-order", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--hook-history")
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--report-json")
    parser.add_argument(
        "--today", type=date.fromisoformat, help="UTC day (YYYY-MM-DD); default today"
    )
    args = parser.parse_args(argv)
    owned = container is None
    if container is None:
        container = build_container()
    try:
        try:
            validator = ValidatorDependencyPins(
                container.get_service(_FACTS_TOKEN).handle,
                contract=None,
                layer_order=load_layer_order(args.layer_order),
                policy=load_dependency_pin_policy(args.policy),
                repo=args.repo,
                hook_history_dir=args.hook_history,
                today=args.today,
            )
            targets = [Path(t) for t in args.targets] or [Path()]
            if not validator.manifests(targets):
                raise ModelOnexError(
                    message=f"no dependency manifest under {[str(t) for t in targets]}",
                    error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                )
            result = validator.validate(targets)
            findings = tuple(
                ModelValidationFindingEmbed(
                    validator_id=validator.validator_id,
                    severity="WARN" if issue.severity.value == "warning" else "FAIL",
                    location=f"{issue.file_path}:{issue.line_number or 1}",
                    message=issue.message,
                    remediation=issue.suggestion,
                    rule_id=issue.code,
                )
                for issue in result.issues
            )
            report = ModelValidationReport.from_findings(
                findings=findings,
                request=ModelValidationRequestRef(profile="default"),
                validators_run=(validator.validator_id,),
            )
            code = 0 if result.is_valid else 1
        except (OSError, ValueError, ModelOnexError) as exc:
            report = ModelValidationReport.from_runtime_errors(
                ValidatorDependencyPins.validator_id, (str(exc),)
            )
            code = 1
        if args.report_json is not None:
            container.get_service(_WRITER_TOKEN).handle(
                ModelValidationReportWriteInput(
                    report_path=args.report_json, report=report
                )
            )
        for finding in report.findings:
            sys.stdout.write(f"{finding.severity}: {finding.message}\n")
        sys.stdout.write(f"{report.overall_status}: dependency pins\n")
        return code
    finally:
        if owned:
            container.close()


def main() -> int:
    """Console entry point."""
    return run()


if __name__ == "__main__":
    sys.exit(main())
