# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reject hardcoded ONEX topic literals outside approved constant files (OMN-20074, OMN-21518).

Pure over explicit ``(path, source)`` pairs and the rule data the request carries;
the matchers are ``matcher_no_hardcoded_topics`` and the CLI is
``runtime_no_hardcoded_topics_check``.
"""

from __future__ import annotations

from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_check_input import (
    ModelNoHardcodedTopicsCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_hardcoded_topics_check_compute.matcher_no_hardcoded_topics import (
    is_exempt_path,
    violation_lines,
)


class HandlerNoHardcodedTopics:
    """Decide, per supplied source, which lines hold an unapproved topic literal."""

    def handle(
        self, request: ModelNoHardcodedTopicsCheckInput
    ) -> ModelValidationReport:
        """Return one FAIL finding per flagged line, in file then line order."""
        rules = request.rules
        findings: list[ModelValidationFindingEmbed] = []
        for file in request.files:
            if is_exempt_path(file.path, rules):
                continue
            for lineno in violation_lines(file.source, rules):
                location = f"{file.path}:{lineno}"
                finding = ModelValidationFinding(
                    validator_id=rules.validator_name,
                    severity="FAIL",
                    rule_id=rules.validator_name,
                    location=location,
                    message=f"{location}: {rules.message}",
                )
                findings.append(
                    ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                )
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(rules.validator_name,),
        )
