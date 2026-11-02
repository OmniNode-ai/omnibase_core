# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the todo-format hook (OMN-20068).

Usage::

    python -m omnibase_core.nodes.node_todo_format_check_effect.runtime_todo_format [files...]

Exit code 0 = clean. Exit code 1 = violations found.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_todo_format_request import (
    ModelTodoFormatRequest,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_todo_format_check_effect.handler_todo_format import (
    TICKET_FORMAT,
    HandlerTodoFormat,
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

__all__ = ["main"]

VALIDATOR_ID: Final[str] = "no-untracked-todos"


def _write_report(
    report_path: str | None,
    overlay_path: Path | None,
    findings: tuple[ModelValidationFindingEmbed, ...],
) -> None:
    """Persist every verdict and its events through the overlay's writer."""
    handler = HandlerValidatorRuntimeOverlay()
    settings = handler.settings()
    overlay = handler.load(overlay_path or handler.default_overlay_path())
    container = build_validator_container(overlay)
    try:
        container.get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(
                report_path=report_path
                or settings.default_report_path.format(validator_id=VALIDATOR_ID),
                report=ModelValidationReport.from_findings(
                    findings=findings,
                    request=ModelValidationRequestRef(profile=overlay.profile),
                    validators_run=(VALIDATOR_ID,),
                ),
                repository=settings.default_repository,
            )
        )
    finally:
        container.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Require unfinished-work markers to reference a ticket."
    )
    parser.add_argument("files", nargs="*")
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
        help="Validator-runtime overlay; the runtime settings' default when omitted",
    )
    args = parser.parse_args(argv)
    all_violations = (
        HandlerTodoFormat()
        .handle(ModelTodoFormatRequest(paths=tuple(args.files)))
        .findings
    )
    _write_report(
        args.report_json,
        args.overlay,
        tuple(
            ModelValidationFindingEmbed(
                validator_id=VALIDATOR_ID,
                severity="FAIL",
                location=f"{finding.path}:{finding.line}",
                message=finding.message,
            )
            for finding in all_violations
        ),
    )
    if all_violations:
        for finding in all_violations:
            sys.stdout.write(f"{finding.format()}\n")
        sys.stdout.write(
            f"\n{len(all_violations)} violation(s). Use format: {TICKET_FORMAT}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
