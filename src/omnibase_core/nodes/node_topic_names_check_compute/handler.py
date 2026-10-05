# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure core topic naming validator over inline source pairs."""

from omnibase_core.models.nodes.topic_names_check.model_topic_names_check_input import (
    ModelTopicNamesCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_topic_names_check_compute.matcher_topic_names import (
    VALIDATOR_ID,
    extract_topics,
    topic_error,
)


class NodeTopicNamesCheckCompute:
    """Validate topic constants without filesystem or runtime dependencies."""

    def handle(self, request: ModelTopicNamesCheckInput) -> ModelValidationReport:
        """Return one FAIL per invalid topic, using the canonical report engine."""
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            for line, value in extract_topics(file.path, file.source):
                error = topic_error(value)
                if error is not None:
                    rule, message = error
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id=rule,
                            location=f"{file.path}:{line}",
                            message=message,
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
