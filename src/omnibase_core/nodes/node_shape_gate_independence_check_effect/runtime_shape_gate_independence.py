# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the shape-gate independence guard (OMN-20298).

Usage::

    python -m omnibase_core.nodes.node_shape_gate_independence_check_effect.runtime_shape_gate_independence [workflow.yml ...]

With no paths, every file under ``.github/workflows`` is scanned.
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
from omnibase_core.models.validation.model_shape_gate_independence_request import (
    ModelShapeGateIndependenceRequest,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_shape_gate_independence_check_effect.handler_shape_gate_independence import (
    HandlerShapeGateIndependence,
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

VALIDATOR_ID: Final[str] = "shape-gate-independence"


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
    parser = argparse.ArgumentParser(
        description="Refuse shape-gate detector jobs that depend on the OCC preflight."
    )
    parser.add_argument("paths", nargs="*", type=Path)
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
    findings = (
        HandlerShapeGateIndependence()
        .handle(ModelShapeGateIndependenceRequest(paths=tuple(args.paths)))
        .findings
    )
    _write_report(
        args.report_json,
        args.overlay,
        tuple(
            ModelValidationFindingEmbed(
                validator_id=VALIDATOR_ID,
                severity="FAIL",
                location=str(finding.path),
                message=finding.reason,
            )
            for finding in findings
        ),
    )
    for finding in findings:
        sys.stderr.write(f"{finding.format()}\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
