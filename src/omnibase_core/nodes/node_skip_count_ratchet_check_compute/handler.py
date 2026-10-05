# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure shrink-only decision over a frozen baseline and test inventory."""

from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_ratchet_check_input import (
    ModelSkipCountRatchetCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.ratchet_decision import (
    VALIDATOR_ID,
    ZERO_RECORDS_MESSAGE,
    evaluate,
)


class NodeSkipCountRatchetCheckCompute:
    """COMPUTE handler: no filesystem, clock, environment or other side effects."""

    def handle(self, request: ModelSkipCountRatchetCheckInput) -> ModelValidationReport:
        findings: list[ModelValidationFinding] = []
        if request.observation.test_records == 0:
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="zero-test-records",
                    location=f"{request.baseline.path}:1",
                    message=ZERO_RECORDS_MESSAGE,
                )
            )
        else:
            code, lines = evaluate(request.baseline, request.observation)
            if code:
                for line in lines:
                    if line.startswith(("::error::", "    + ")):
                        findings.append(
                            ModelValidationFinding(
                                validator_id=VALIDATOR_ID,
                                severity="FAIL",
                                rule_id=f"skip-growth-{request.baseline.mode}",
                                location=f"{request.baseline.path}:1",
                                message=line,
                            )
                        )
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**f.model_dump(mode="json"))
                for f in findings
            ),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
