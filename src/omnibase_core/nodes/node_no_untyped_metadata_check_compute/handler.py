# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure line-scanning port of the no-untyped-metadata hook."""

from __future__ import annotations

import io
import re
from typing import Final

from omnibase_core.models.nodes.no_untyped_metadata_check.model_no_untyped_metadata_check_input import (
    ModelNoUntypedMetadataCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

VALIDATOR_ID: Final[str] = "no-untyped-metadata"
_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"metadata\s*:\s*(?:Optional\[)?dict\[str,\s*(?:Any|object)\]"
)
_EXCLUDE_COMMENT: Final[str] = "ONEX_" + "EXCLUDE:"
_MESSAGE: Final[str] = (
    "untyped metadata dict — use TypedDict or add ONEX_" + "EXCLUDE comment"
)


class NodeNoUntypedMetadataCheckCompute:
    """Preserve the script's lexical matching and same-line exemptions."""

    def handle(
        self, request: ModelNoUntypedMetadataCheckInput
    ) -> ModelValidationReport:
        """Return one FAIL finding per matching line, without parsing Python."""
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            if not file.path.endswith(".py"):
                continue
            # Universal newline iteration matches the script's text-mode open;
            # splitlines would also split Unicode separators inside a line.
            for lineno, line in enumerate(io.StringIO(file.source, newline=None), 1):
                if _PATTERN.search(line) and _EXCLUDE_COMMENT not in line:
                    location = f"{file.path}:{lineno}"
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id=VALIDATOR_ID,
                            location=location,
                            message=f"{location}: {_MESSAGE}",
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
