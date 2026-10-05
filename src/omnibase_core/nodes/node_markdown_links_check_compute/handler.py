# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure core markdown link validation over explicit filesystem facts."""

from omnibase_core.models.nodes.markdown_links_check.model_markdown_links_check_input import (
    ModelMarkdownLinksCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_markdown_links_check_compute.validation_markdown_links import (
    VALIDATOR_ID,
    analyze,
)


class NodeMarkdownLinksCheckCompute:
    """Canonical COMPUTE handler; no filesystem or network operations."""

    def handle(self, request: ModelMarkdownLinksCheckInput) -> ModelValidationReport:
        findings, _, _, _ = analyze(request)
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                for finding in findings
            ),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
