# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""K1 handler_di check effect: read the targets, judge them, return the canonical report (OMN-21531)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_handler_di_check_input import (
    ModelHandlerDiCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.validation.validator_handler_di import ValidatorHandlerDi

__all__ = ["NodeHandlerDiCheckEffect"]


class NodeHandlerDiCheckEffect:
    """Own the file reads of the K1 check; the rules are the pure checker's."""

    def handle(self, request: ModelHandlerDiCheckInput) -> ModelValidationReport:
        """Return one finding per refused line of ``request.targets``."""
        root = Path(request.root)
        validator = ValidatorHandlerDi(root=root, baseline_path=request.baseline_path)
        result = validator.validate([Path(t) for t in request.targets])
        failing = (EnumSeverity.ERROR, EnumSeverity.CRITICAL, EnumSeverity.FATAL)
        findings = tuple(
            ModelValidationFindingEmbed(
                validator_id=validator.validator_id,
                severity="FAIL" if issue.severity in failing else "WARN",
                location=(
                    None
                    if issue.file_path is None
                    else f"{issue.file_path}:{issue.line_number or 1}"
                ),
                rule_id=issue.rule_name or issue.code,
                message=issue.message,
            )
            for issue in result.issues
        )
        return ModelValidationReport.from_findings(
            findings=findings,
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(validator.validator_id,),
        )
