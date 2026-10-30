# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Composition root of the K1 handler_di check (OMN-21531).

The hook ``handler-di-gate`` runs this module. It composes a container holding the check
effect and the report writer, resolves both with ``get_service`` -- no handler, writer or
bus is built at a call site -- and prints one line per finding. Usage::

    python -m omnibase_core.nodes.node_handler_di_check_effect.runtime_handler_di_check [--baseline FILE] [--report-json PATH] <files...>
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
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
from omnibase_core.models.validation.model_handler_di_check_input import (
    ModelHandlerDiCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_handler_di_check_effect.handler import (
    NodeHandlerDiCheckEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_handler_di import ValidatorHandlerDi

_CHECK_TOKEN = cast("type[NodeHandlerDiCheckEffect]", NodeHandlerDiCheckEffect)
_WRITER_TOKEN = cast(
    "type[NodeValidationReportWriteEffect]", NodeValidationReportWriteEffect
)


def build_container(
    *,
    check: NodeHandlerDiCheckEffect | None = None,
    report_writer: NodeValidationReportWriteEffect | None = None,
) -> ModelONEXContainer:
    """Register the effects under their tokens; injection supports in-memory tests."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation, instance in (
        (_CHECK_TOKEN, NodeHandlerDiCheckEffect, check),
        (_WRITER_TOKEN, NodeValidationReportWriteEffect, report_writer),
    ):
        if instance is None:
            run_coro_sync(
                registry.register_service(
                    token,
                    implementation,
                    EnumServiceLifecycle.SINGLETON,
                    EnumInjectionScope.GLOBAL,
                )
            )
        else:
            run_coro_sync(registry.register_instance(token, instance))
    return container


def run(
    argv: Sequence[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Judge the passed files and persist the report with the container's writer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--report-json", default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    owned = container is None
    if container is None:
        container = build_container()
    try:
        try:
            report = container.get_service(_CHECK_TOKEN).handle(
                ModelHandlerDiCheckInput(
                    targets=tuple(args.filenames) or (".",),
                    root=str((args.repo_root or Path.cwd()).resolve()),
                    baseline_path=args.baseline,
                )
            )
        except (OSError, ValueError, ModelOnexError) as exc:
            report = ModelValidationReport.from_runtime_errors(
                ValidatorHandlerDi.validator_id, (str(exc),)
            )
        if args.report_json is not None:
            container.get_service(_WRITER_TOKEN).handle(
                ModelValidationReportWriteInput(
                    report_path=args.report_json, report=report
                )
            )
        for finding in report.findings:
            sys.stderr.write(
                f"{finding.severity}: {finding.location}: [{finding.rule_id}] {finding.message}\n"
            )
        return 0 if report.overall_status == "PASS" else 1
    finally:
        if owned:
            container.close()


if __name__ == "__main__":
    sys.exit(run())
