# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the no-hardcoded-topics hook (OMN-20074, OMN-21518).

Reads the named files through the source-file gather EFFECT, loads the rules from
the ``no_hardcoded_topics`` validator contract and hands both to the pure
``HandlerNoHardcodedTopics``. Usage::

    python -m omnibase_core.nodes.node_no_hardcoded_topics_check_compute.runtime_no_hardcoded_topics_check [files...]

Exit code 0 = clean. Exit code 1 = violations found, or a named file unreadable.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_check_input import (
    ModelNoHardcodedTopicsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_hardcoded_topics_check_compute.handler_no_hardcoded_topics import (
    HandlerNoHardcodedTopics,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_no_hardcoded_topics import (
    ValidatorNoHardcodedTopics,
    load_rules,
)

__all__ = ["main"]

VALIDATOR_ID: Final[str] = "no-hardcoded-topics"


_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN = cast(
    "type[NodeSourceFileGatherEffect]", NodeSourceFileGatherEffect
)
_HANDLER_NO_HARDCODED_TOPICS_TOKEN = cast(
    "type[HandlerNoHardcodedTopics]", HandlerNoHardcodedTopics
)


def _write_report(
    report_path: str | None,
    overlay_path: Path | None,
    findings: tuple[ModelValidationFindingEmbed, ...] = (),
    *,
    runtime_errors: tuple[str, ...] = (),
) -> None:
    """Persist every verdict and publish its events using the configured overlay."""
    handler = HandlerValidatorRuntimeOverlay()
    settings = handler.settings()
    overlay = handler.load(overlay_path or handler.default_overlay_path())
    report = (
        ModelValidationReport.from_runtime_errors(VALIDATOR_ID, runtime_errors)
        if runtime_errors
        else ModelValidationReport.from_findings(
            findings=findings,
            request=ModelValidationRequestRef(profile=overlay.profile),
            validators_run=(VALIDATOR_ID,),
        )
    )
    container = build_validator_container(overlay)
    try:
        container.get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(
                report_path=report_path
                or settings.default_report_path.format(validator_id=VALIDATOR_ID),
                report=report,
                repository=settings.default_repository,
            )
        )
    finally:
        container.close()


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN, NodeSourceFileGatherEffect),
        (_HANDLER_NO_HARDCODED_TOPICS_TOKEN, HandlerNoHardcodedTopics),
    ):
        run_coro_sync(
            registry.register_service(
                token,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(
    argv: Sequence[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: Sequence[str] | None, container: ModelONEXContainer) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument(
        "--report-json",
        default=None,
        metavar="PATH",
        help="Report path; the runtime settings' default when omitted",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        default=None,
        metavar="PATH",
        help="Validator-runtime overlay; the settings' default when omitted",
    )
    parsed = parser.parse_args(argv)
    paths = parsed.paths
    if not paths:
        _write_report(parsed.report_json, parsed.overlay)
        return 0
    gathered = container.get_service(_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN).handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=paths,
            include_patterns=["**/*"],
            decode_errors="replace",
        )
    )
    if gathered.skipped:
        _write_report(
            parsed.report_json,
            parsed.overlay,
            runtime_errors=tuple(
                f"{skipped.path}: {skipped.reason}" for skipped in gathered.skipped
            ),
        )
        for skipped in gathered.skipped:
            sys.stdout.write(f"ERROR: {skipped.path}: {skipped.reason}\n")
        return 1
    rules = load_rules(ValidatorNoHardcodedTopics().contract)
    report = container.get_service(_HANDLER_NO_HARDCODED_TOPICS_TOKEN).handle(
        ModelNoHardcodedTopicsCheckInput(
            files=[
                ModelSourceFile(path=f.path, source=f.source) for f in gathered.files
            ],
            rules=rules,
        )
    )
    _write_report(
        parsed.report_json,
        parsed.overlay,
        tuple(
            ModelValidationFindingEmbed(
                validator_id=VALIDATOR_ID,
                severity="FAIL",
                location=finding.location,
                rule_id=finding.rule_id,
                message=finding.message,
            )
            for finding in report.findings
        ),
    )
    if report.findings:
        for finding in report.findings:
            sys.stdout.write(f"{finding.message}\n")
        sys.stdout.write(
            f"\n{len(report.findings)} violation(s). {rules.remediation}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
