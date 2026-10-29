# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure parent-ticket and exemption citation policy (OMN-21504 / T-Q1)."""

from __future__ import annotations

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_dod_verify_overlay import (
    ModelDodVerifyOverlay,
)
from omnibase_core.models.validation.model_parent_ticket_citation_facts import (
    ModelParentTicketCitationFacts,
)

RULE_PARENT_ONLY_CITATION = "parent_ticket_only_citation"
RULE_EXEMPTION_CITES_TASK_TICKET = "exemption_cites_task_ticket"


def check_parent_ticket_citation(
    facts: ModelParentTicketCitationFacts,
    overlay: ModelDodVerifyOverlay,
) -> tuple[ModelValidationIssue, ...]:
    """Refuse parent-only citations and exemptions citing factory task tickets."""
    cited = sorted({ticket.upper() for ticket in facts.cited_tickets})
    issues: list[ModelValidationIssue] = []
    if cited and all(ticket in overlay.parent_tickets for ticket in cited):
        issues.append(
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                code=RULE_PARENT_ONLY_CITATION,
                rule_name=RULE_PARENT_ONLY_CITATION,
                message=(
                    f"pull request cites only parent ticket(s) {', '.join(cited)}; "
                    "cite a task ticket whose contract binds this change"
                ),
            )
        )
    tasks = [ticket for ticket in cited if ticket in overlay.factory_task_tickets]
    if facts.exemption is not None and tasks:
        issues.append(
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                code=RULE_EXEMPTION_CITES_TASK_TICKET,
                rule_name=RULE_EXEMPTION_CITES_TASK_TICKET,
                message=(
                    f"exemption {facts.exemption.value} cannot admit a pull request "
                    f"that cites factory task ticket(s) {', '.join(tasks)}"
                ),
            )
        )
    return tuple(issues)
