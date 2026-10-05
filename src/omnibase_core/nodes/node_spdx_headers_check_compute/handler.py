# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure SPDX header check; the header logic is shared with `onex spdx validate`."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from omnibase_core.cli.cli_spdx import is_spdx_eligible_path, validate_spdx_source
from omnibase_core.models.nodes.spdx_headers_check.model_spdx_headers_check_input import (
    ModelSpdxHeadersCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

VALIDATOR_ID: Final[str] = "spdx-headers-check"
RULE_ID: Final[str] = "spdx-header"
_LINE_PREFIX: Final[re.Pattern[str]] = re.compile(r"^Line (\d+):")


class NodeSpdxHeadersCheckCompute:
    """One FAIL finding per eligible file whose SPDX header is wrong."""

    def handle(self, request: ModelSpdxHeadersCheckInput) -> ModelValidationReport:
        """Return the canonical report; no I/O."""
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            if not is_spdx_eligible_path(Path(file.path)):
                continue
            error = validate_spdx_source(file.source)
            if error is None:
                continue
            match = _LINE_PREFIX.match(error)
            line = int(match[1]) if match else 1
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    rule_id=RULE_ID,
                    location=f"{file.path}:{line}",
                    message=f"{file.path}: {error}",
                )
            )
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                for finding in findings
            ),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
