# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gather repository sources, validate required producers, and render a report."""

import argparse
import sys
from functools import cache
from pathlib import Path

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_gather_input import (
    ModelRequiredContextProducerGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.handler import (
    NodeRequiredContextProducerCheckCompute,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.required_context_producer_rules import (
    VALIDATOR_ID,
    manifest_rows,
)
from omnibase_core.nodes.node_required_context_producer_gather_effect.handler import (
    NodeRequiredContextProducerGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync


@cache
def _container() -> ModelONEXContainer:
    """Bind this runtime's effects and COMPUTE node in a container, built once."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for implementation in (
        NodeRequiredContextProducerCheckCompute,
        NodeRequiredContextProducerGatherEffect,
        NodeValidationReportWriteEffect,
    ):
        run_coro_sync(
            registry.register_service(
                implementation,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(argv: list[str] | None = None) -> int:
    """Run the paired nodes and write reports on PASS, FAIL, and ERROR."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument("--base", default=None, help="Base Git ref, e.g. origin/dev.")
    parser.add_argument("--report-json", default=None)
    args = parser.parse_args(argv)
    facts = (
        _container()
        .get_service(NodeRequiredContextProducerGatherEffect)
        .handle(
            ModelRequiredContextProducerGatherInput(repo_root=args.root, base=args.base)
        )
    )
    if facts.runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, facts.runtime_errors
        )
        code: int = facts.runtime_exit_code
    else:
        report = (
            _container()
            .get_service(NodeRequiredContextProducerCheckCompute)
            .handle(facts)
        )
        code = (
            0
            if report.overall_status == "PASS"
            else 2
            if report.overall_status == "ERROR"
            else 1
        )
    if args.report_json is not None:
        _container().get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(report_path=args.report_json, report=report)
        )
    if report.overall_status == "PASS":
        count = sum(
            row["mode"] == "REQUIRED" for row in manifest_rows(facts.head_manifest_text)
        )
        sys.stdout.write(
            f"OK: checked {count} REQUIRED rows; all required contexts retain producers.\n"
        )
    else:
        for finding in report.findings:
            sys.stderr.write(finding.message + "\n")
            if finding.remediation is not None:
                sys.stderr.write(finding.remediation + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
