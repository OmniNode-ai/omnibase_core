# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure port of omnibase_infra's integration silent-skip evaluation."""

from __future__ import annotations

import re
from typing import Final

from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_config import (
    ModelIntegrationSkipsCheckConfig,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_input import (
    ModelIntegrationSkipsCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

VALIDATOR_ID: Final = "integration-skip-guard"


def classify_skip(
    reason: str, config: ModelIntegrationSkipsCheckConfig
) -> tuple[str | None, bool]:
    """First required-service match wins, even when an optional pattern matches."""
    offending = next(
        (
            service
            for service, spec in config.required_services.items()
            if any(
                re.search(pattern, reason, re.IGNORECASE)
                for pattern in spec.missing_skip_patterns
            )
        ),
        None,
    )
    allowed = any(
        re.search(pattern, reason, re.IGNORECASE)
        for pattern in config.allowed_optional_skip_patterns
    )
    return offending, allowed


class NodeIntegrationSkipsCheckCompute:
    """Evaluate typed artifact observations without side effects."""

    def handle(self, request: ModelIntegrationSkipsCheckInput) -> ModelValidationReport:
        """Preserve the oracle's rule order and exact violation text."""
        findings: list[ModelValidationFinding] = []
        config = request.config
        if not config.silent_skip_allowed:
            for record in request.skipped:
                offending, allowed = classify_skip(record.reason, config)
                if offending is not None:
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="false-green",
                            location=f"{record.path}:{record.line}",
                            message=(
                                f"FALSE-GREEN: integration test {record.test_name!r} SKIPPED because "
                                f"provisioned service {offending!r} looked absent — reason: "
                                f"{record.reason!r}. The merge-gating job provisions {offending}; this "
                                "test SHOULD have run. Wire the service env or fix the skip guard."
                            ),
                        )
                    )
                elif request.strict and not allowed:
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="unclassified-skip",
                            location=f"{record.path}:{record.line}",
                            message=(
                                f"UNCLASSIFIED-SKIP (strict): integration test {record.test_name!r} skipped "
                                f"with an unrecognised reason: {record.reason!r}. Classify it in "
                                "integration_skip_guard.yaml (required_services vs "
                                "allowed_optional_skip_patterns)."
                            ),
                        )
                    )
            if request.executed < config.require_executed_min:
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        rule_id="under-collection",
                        location="<reports>:1",
                        message=(
                            f"ZERO/UNDER-COLLECTION: only {request.executed} integration test(s) "
                            f"executed (require >= {config.require_executed_min}). A marker typo or a "
                            "broken selector collecting nothing is itself a false-green. "
                            f"(total cases seen: {request.total_cases})"
                        ),
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
