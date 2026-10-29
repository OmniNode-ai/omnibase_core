# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure canonical-file-shape check: facts and contract in, ModelValidationReport out (OMN-21515)."""

from __future__ import annotations

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_canonical_file_shape_check_input import (
    ModelCanonicalFileShapeCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.matcher_node_home import (
    RULE_PREFIX,
    NodeHomeRule,
)
from omnibase_core.validation.checker_canonical_file_shape import (
    VALIDATOR_ID,
    check,
    load_rule_set,
)


class NodeCanonicalFileShapeCheckCompute:
    """Run the pure checker and report one finding per refused path and rule."""

    def handle(
        self, request: ModelCanonicalFileShapeCheckInput
    ) -> ModelValidationReport:
        """Return the report for ``request.facts`` under ``request.contract``."""
        try:
            rules = load_rule_set(request.contract)
        except ModelOnexError as exc:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, (exc.message,)
            )
        findings: list[ModelValidationFindingEmbed] = []
        if request.facts is not None:
            findings.extend(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    location=f"{issue.file_path}:1",
                    message=issue.message,
                    rule_id=issue.code,
                )
                for issue in check(request.facts, rules)
            )
        if request.node_home is not None:
            findings.extend(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    location=f"{finding.path}:1",
                    message=finding.message,
                    rule_id=f"{RULE_PREFIX}{finding.code}",
                )
                for finding in NodeHomeRule(rules).check(request.node_home).findings
            )
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
