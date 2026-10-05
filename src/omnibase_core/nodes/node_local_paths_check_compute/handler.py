# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure typed local-paths validation, with no bus or runtime dependencies."""

from __future__ import annotations

from omnibase_core.models.nodes.local_paths_check.model_local_paths_check_input import (
    ModelLocalPathsCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_local_paths_check_compute.matcher_local_paths import (
    VALIDATOR_ID,
    scan_source,
)


class NodeLocalPathsCheckCompute:
    """Scan inline source files and return the canonical validation report."""

    def handle(self, request: ModelLocalPathsCheckInput) -> ModelValidationReport:
        """Return one FAIL finding per old scanner match, preserving its order."""
        findings = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for file in request.files
            for finding in scan_source(file.source, file.path)
        )
        return ModelValidationReport.from_findings(
            findings=findings,
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
