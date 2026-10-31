# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI for explicit filenames or a full source-tree scan through EFFECT nodes."""

from __future__ import annotations

import argparse
import sys
from functools import cache

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.no_untyped_metadata_check.model_no_untyped_metadata_check_input import (
    ModelNoUntypedMetadataCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_untyped_metadata_check_compute.handler import (
    VALIDATOR_ID,
    NodeNoUntypedMetadataCheckCompute,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
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
        NodeNoUntypedMetadataCheckCompute,
        NodeSourceFileGatherEffect,
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


def _split_gather_output(
    output: ModelSourceFileGatherOutput,
) -> tuple[list[ModelSourceFile], list[str]]:
    errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if skipped.reason.startswith(("read error:", "error checking file size:"))
        or skipped.reason == "not a file"
    ]
    return [ModelSourceFile(path=f.path, source=f.source) for f in output.files], errors


def _gather(
    request: ModelSourceFileGatherInput,
) -> tuple[list[ModelSourceFile], list[str]]:
    try:
        output = _container().get_service(NodeSourceFileGatherEffect).handle(request)
    except (OSError, UnicodeError) as exc:
        return [], [f"{request.root}: read error: {exc}"]
    return _split_gather_output(output)


def _gather_from_filenames(paths: list[str]) -> tuple[list[ModelSourceFile], list[str]]:
    eligible = [path for path in paths if path.endswith(".py")]
    if not eligible:
        return [], []
    return _gather(
        ModelSourceFileGatherInput(
            root=".", explicit_paths=eligible, include_patterns=["**/*.py"]
        )
    )


def _gather_from_root(root: str) -> tuple[list[ModelSourceFile], list[str]]:
    return _gather(ModelSourceFileGatherInput(root=root, include_patterns=["**/*.py"]))


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        _container().get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """Return zero only on PASS; preserve the old hook's silence on success."""
    parser = argparse.ArgumentParser(
        prog="no-untyped-metadata",
        description="Reject untyped metadata fields through the canonical COMPUTE node.",
    )
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--root", default="src")
    parser.add_argument("--report-json", default=None)
    parsed = parser.parse_args(argv)
    full_tree = not parsed.filenames
    files, errors = (
        _gather_from_root(parsed.root)
        if full_tree
        else _gather_from_filenames(parsed.filenames)
    )
    if not errors and full_tree and not files:
        errors = [
            f"zero files scanned under {parsed.root}: a full-tree run that scans "
            "nothing is ERROR, never PASS"
        ]
    if errors:
        report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, tuple(errors))
        _write_report(parsed.report_json, report)
        for error in errors:
            sys.stdout.write(f"ERROR: {error}\n")
        return 1

    report = (
        _container()
        .get_service(NodeNoUntypedMetadataCheckCompute)
        .handle(ModelNoUntypedMetadataCheckInput(files=files))
    )
    _write_report(parsed.report_json, report)
    if report.overall_status == "PASS":
        return 0
    for finding in report.findings:
        sys.stdout.write(f"{finding.message}\n")
    sys.stdout.write(
        f"\n{report.metrics.total} violation(s). Replace dict[str, Any] with TypedDict.\n"
    )
    sys.stdout.write(
        "If intentional, add: # ONEX_" + "EXCLUDE: dict_str_any - <reason>\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
