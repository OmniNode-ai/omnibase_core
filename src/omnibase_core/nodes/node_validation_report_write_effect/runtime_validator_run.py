# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Run a ``ValidatorBase`` validator and persist its canonical report (OMN-21498).

The runtime half of the generic validator format: the checker is pure, the
validator reads, and this module turns a validator's result into the canonical
``ModelValidationReport`` and hands it to the report-writing EFFECT node. The
writer is never built here; ``run_validator`` resolves it from the container with
``get_service``, so the in-memory default and any other overlay are what the
container was composed with. ``main`` is the composition root: it composes the
default container, injecting the writer, and runs the validator.

Usage (a validator is named by ``module:Class``; the validators live in
``validation/``, which never imports a node, so the node runtime imports them)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run \\
        omnibase_core.validation.validator_hook_writes:ValidatorHookWrites <targets...>

The writer also publishes (OMN-21529): the container's ``ModelValidatorRuntimeBus`` is bound
from a validator-runtime overlay, ``--overlay`` names the file (the contract names the
default, the in-memory overlay) and the Redpanda overlay differs from it in the bus
binding alone. ``--report-json`` defaults to the contract's report path, so a hook run
always leaves a report.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_overlay import (
    ModelValidatorRuntimeOverlay,
    ValidationProfile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validation_report_publish import (
    NodeValidationReportPublishEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.validation.validator_base import EXIT_ERRORS, ValidatorBase

__all__ = [
    "build_report",
    "build_validator_container",
    "main",
    "main_for_reference",
    "run_validator",
    "validator_class",
]


def _location(path: Path | None, line: int | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        shown = path.resolve().relative_to(root.resolve())
    except ValueError:
        shown = path
    return f"{shown}:{line}" if line else str(shown)


def build_report(
    validator_id: str,
    result: ModelValidationResult[None],
    root: Path,
    profile: ValidationProfile,
) -> ModelValidationReport:
    """The canonical report of one validator result: one finding per issue.

    Locations are relative to ``root`` when the path lies under it.
    """
    failing = (EnumSeverity.ERROR, EnumSeverity.CRITICAL, EnumSeverity.FATAL)
    findings = tuple(
        ModelValidationFindingEmbed(
            validator_id=validator_id,
            severity="FAIL" if issue.severity in failing else "WARN",
            location=_location(issue.file_path, issue.line_number, root),
            rule_id=issue.rule_name or issue.code,
            message=issue.message,
        )
        for issue in result.issues
    )
    return ModelValidationReport.from_findings(
        findings=findings,
        request=ModelValidationRequestRef(profile=profile),
        validators_run=(validator_id,),
    )


def build_validator_container(
    overlay: ModelValidatorRuntimeOverlay | None = None,
) -> ModelONEXContainer:
    """Compose the container: the overlay's bus and the report writer, bound to it.

    With no overlay the contract's default (in-memory) overlay is used.
    """
    handler = HandlerValidatorRuntimeOverlay()
    bound = overlay or handler.load(handler.default_overlay_path())
    container = ModelONEXContainer(enable_service_registry=True)
    registry = container.service_registry

    async def _compose() -> None:
        await registry.register_instance(
            ModelValidatorRuntimeBus, handler.bind_bus(bound)
        )
        await registry.register_instance(
            interface=NodeValidationReportWriteEffect,
            instance=NodeValidationReportPublishEffect(
                container, handler.settings().run_topic
            ),
        )

    asyncio.run(_compose())
    return container


def run_validator(
    container: ModelONEXContainer | None,
    validator: ValidatorBase,
    targets: Sequence[Path],
    report_path: str | None,
    profile: ValidationProfile,
    repository: str,
) -> ModelValidationResult[None]:
    """Validate ``targets``; write the report through the container's writer."""
    result = validator.validate(list(targets))
    if report_path is not None:
        if container is None:
            raise ModelOnexError(
                message="a report path needs a container that supplies the report writer",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        writer = container.get_service(NodeValidationReportWriteEffect)
        writer.handle(
            ModelValidationReportWriteInput(
                report_path=report_path,
                report=build_report(
                    validator.validator_id, result, Path.cwd(), profile
                ),
                repository=repository,
            )
        )
    return result


def main(
    validator_cls: type[ValidatorBase],
    argv: Sequence[str] | None = None,
    container_factory: Callable[[ModelValidatorRuntimeOverlay], ModelONEXContainer]
    | None = None,
) -> int:
    """CLI runtime: targets, ``--report-json``, ``--overlay``; exit 0 when valid, else the base code."""
    parser = argparse.ArgumentParser(
        description=f"Run {validator_cls.validator_id} validator"
    )
    parser.add_argument("targets", nargs="*", type=Path, default=[Path()])
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--report-json",
        default=None,
        metavar="PATH",
        help="Report path; the node contract's default when omitted",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        default=None,
        metavar="PATH",
        help="Validator-runtime overlay; the node contract's default when omitted",
    )
    parser.add_argument(
        "--repository",
        default=None,
        help="Repository named on triggered events; the node contract's default when omitted",
    )
    args = parser.parse_args(argv)

    targets: list[Path] = []
    for target in args.targets:
        validated = validator_cls._validate_cli_path(target, "target path")
        if validated is None:
            return EXIT_ERRORS
        targets.append(validated)

    validator = validator_cls()
    handler = HandlerValidatorRuntimeOverlay()
    try:
        settings = handler.settings()
        overlay = handler.load(args.overlay or handler.default_overlay_path())
        result = run_validator(
            container_factory(overlay) if container_factory else None,
            validator,
            targets,
            args.report_json
            or settings.default_report_path.format(validator_id=validator.validator_id),
            overlay.profile,
            args.repository or settings.default_repository,
        )
    except ModelOnexError as exc:
        sys.stderr.write(f"Validation error: {exc.message}\n")
        return EXIT_ERRORS
    if args.verbose or not result.is_valid:
        sys.stdout.write(f"{result.summary}\n")
        for issue in result.issues:
            location = str(issue.file_path or "")
            if issue.line_number:
                location += f":{issue.line_number}"
            sys.stdout.write(
                f"  [{issue.severity.value.upper()}] {location}: "
                f"{issue.rule_name}: {issue.message}\n"
            )
    return validator.get_exit_code(result)


def validator_class(reference: str) -> type[ValidatorBase]:
    """The ``ValidatorBase`` subclass that ``module:Class`` names."""
    module_name, separator, class_name = reference.partition(":")
    if not separator or not module_name or not class_name:
        raise ModelOnexError(
            message=f"validator reference {reference!r} is not 'module:Class'",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )
    candidate: object = getattr(importlib.import_module(module_name), class_name, None)
    if not (isinstance(candidate, type) and issubclass(candidate, ValidatorBase)):
        raise ModelOnexError(
            message=f"validator reference {reference!r} is not a ValidatorBase subclass",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )
    return candidate


def main_for_reference(argv: Sequence[str] | None = None) -> int:
    """CLI runtime for a pre-commit hook: ``module:Class`` first, then ``main``'s arguments."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        sys.stderr.write("Validation error: a 'module:Class' validator is required\n")
        return EXIT_ERRORS
    try:
        cls = validator_class(arguments[0])
    except ModelOnexError as exc:
        sys.stderr.write(f"Validation error: {exc.message}\n")
        return EXIT_ERRORS
    return main(cls, arguments[1:], container_factory=build_validator_container)


if __name__ == "__main__":
    sys.exit(main_for_reference())
