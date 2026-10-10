# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure canonical COMPUTE handler for hardcoded-topic validation."""

from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.matcher_hardcoded_topic import (
    VALIDATOR_ID,
    scan_source,
)


class NodeHardcodedTopicCheckCompute:
    """Scan supplied source texts without I/O or transport dependencies."""

    def handle(self, request: ModelHardcodedTopicCheckInput) -> ModelValidationReport:
        """Return one canonical FAIL finding per original scanner match."""
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
