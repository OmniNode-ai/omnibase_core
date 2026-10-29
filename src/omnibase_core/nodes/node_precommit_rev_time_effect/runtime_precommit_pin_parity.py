# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Composition root for the pin-parity validator and its two effects."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

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
from omnibase_core.nodes.node_precommit_rev_time_effect.handler import (
    NodePrecommitRevTimeEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_precommit_pin_parity import (
    ValidatorPrecommitPinParity,
)


def build_container(
    *,
    rev_time_source: NodePrecommitRevTimeEffect | None = None,
    report_writer: NodeValidationReportWriteEffect | None = None,
) -> ModelONEXContainer:
    """Register effects under protocol tokens; injection supports in-memory tests."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    resolver_token = cast(
        "type[NodePrecommitRevTimeEffect]", NodePrecommitRevTimeEffect
    )
    writer_token = cast(
        "type[NodeValidationReportWriteEffect]", NodeValidationReportWriteEffect
    )
    if rev_time_source is None:
        run_coro_sync(
            registry.register_service(
                resolver_token,
                NodePrecommitRevTimeEffect,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    else:
        run_coro_sync(registry.register_instance(resolver_token, rev_time_source))
    if report_writer is None:
        run_coro_sync(
            registry.register_service(
                writer_token,
                NodeValidationReportWriteEffect,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    else:
        run_coro_sync(registry.register_instance(writer_token, report_writer))
    return container


def run(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Validate passed filenames and persist reports using the resolved writer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--report-json")
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--history-repo")
    parser.add_argument("--pre-commit-home")
    args = parser.parse_args(argv)
    owned = container is None
    if container is None:
        container = build_container()
    try:
        try:
            resolver = container.get_service(
                cast("type[NodePrecommitRevTimeEffect]", NodePrecommitRevTimeEffect)
            )
            validator = ValidatorPrecommitPinParity(
                resolver.handle,
                contract_path=args.contract,
                history_repo=args.history_repo,
                cache_home=args.pre_commit_home,
            )
            result = validator.validate(
                [Path(f) for f in args.filenames] if args.filenames else Path()
            )
            findings = tuple(
                ModelValidationFindingEmbed(
                    validator_id=validator.validator_id,
                    severity="WARN" if issue.severity.value == "warning" else "FAIL",
                    location=f"{issue.file_path}:{issue.line_number}",
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
                ValidatorPrecommitPinParity.validator_id, (str(exc),)
            )
            code = 1
        if args.report_json is not None:
            container.get_service(
                cast(
                    "type[NodeValidationReportWriteEffect]",
                    NodeValidationReportWriteEffect,
                )
            ).handle(
                ModelValidationReportWriteInput(
                    report_path=args.report_json, report=report
                )
            )
        for finding in report.findings:
            sys.stdout.write(f"{finding.severity}: {finding.message}\n")
        sys.stdout.write(f"{report.overall_status}: pre-commit pin parity\n")
        return code
    finally:
        if owned:
            container.close()


if __name__ == "__main__":
    sys.exit(run())
