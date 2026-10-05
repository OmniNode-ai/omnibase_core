# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure private-IP validation over typed source pairs."""

from omnibase_core.models.nodes.private_ip_check.model_private_ip_check_input import (
    ModelPrivateIpCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_private_ip_check_compute.matcher_private_ip import (
    VALIDATOR_ID,
    find_private_ip_violations,
)


class NodePrivateIpCheckCompute:
    """Return canonical findings with the original runtime's message text."""

    def handle(self, request: ModelPrivateIpCheckInput) -> ModelValidationReport:
        findings = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for file in request.files
            for finding in find_private_ip_violations(file.path, file.source)
        )
        return ModelValidationReport.from_findings(
            findings=findings,
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
