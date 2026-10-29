# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validate PR citation facts against their ``dod_verify`` overlay (OMN-21504)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.handlers.handler_parent_ticket_citation import (
    check_parent_ticket_citation,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_dod_verify_overlay import (
    ModelDodVerifyOverlay,
)
from omnibase_core.models.validation.model_parent_ticket_citation_facts import (
    ModelParentTicketCitationFacts,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.validator_base import ValidatorBase

RULE_PR_CITATION_FACTS_INVALID = "pr_citation_facts_invalid"


class ValidatorParentTicketCitation(ValidatorBase):
    """Load facts and overlay, failing closed before applying the pure checker."""

    validator_id = "parent_ticket_citation"

    def _get_contract_path(self) -> Path:
        """The contract stays in the generic validator home, ``validation/contracts``."""
        return (
            Path(__file__).resolve().parents[1]
            / "validation"
            / "contracts"
            / f"{self.validator_id}.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        if not path.name.endswith(".pr_citation_facts.yaml"):
            return ()
        loaded = self._load(path)
        if isinstance(loaded, str):
            enabled, severity = self._get_rule_config(
                RULE_PR_CITATION_FACTS_INVALID, contract
            )
            if not enabled:
                return ()
            return (
                ModelValidationIssue(
                    severity=severity,
                    code=RULE_PR_CITATION_FACTS_INVALID,
                    rule_name=RULE_PR_CITATION_FACTS_INVALID,
                    message=f"invalid PR citation facts or dod_verify overlay: {loaded}",
                    file_path=path,
                    line_number=1,
                ),
            )
        facts, overlay = loaded
        issues: list[ModelValidationIssue] = []
        for issue in check_parent_ticket_citation(facts, overlay):
            assert issue.rule_name is not None
            enabled, severity = self._get_rule_config(issue.rule_name, contract)
            if enabled:
                issues.append(
                    issue.model_copy(
                        update={
                            "severity": severity,
                            "file_path": path,
                            "line_number": 1,
                        }
                    )
                )
        return tuple(issues)

    @staticmethod
    def _load(
        path: Path,
    ) -> tuple[ModelParentTicketCitationFacts, ModelDodVerifyOverlay] | str:
        """Return the facts and the overlay, or the reason either is unreadable."""
        try:
            raw = load_yaml_mapping_no_duplicates(
                path.read_text(encoding="utf-8"), source=str(path)
            )
            overlay_name = raw.pop("overlay", None)
            if (
                not isinstance(overlay_name, str)
                or not overlay_name
                or Path(overlay_name).is_absolute()
            ):
                return "overlay must name a path relative to the facts file"
            cited = raw.get("cited_tickets")
            if not isinstance(cited, list) or any(
                not isinstance(ticket, str) for ticket in cited
            ):
                return "cited_tickets must be a list of strings"
            facts = ModelParentTicketCitationFacts.model_validate(raw)
            overlay_path = path.parent / overlay_name
            document = load_yaml_mapping_no_duplicates(
                overlay_path.read_text(encoding="utf-8"), source=str(overlay_path)
            )
            section = document.get("dod_verify")
            if not isinstance(section, dict):
                return "overlay must contain a dod_verify mapping"
            for key in ("parent_tickets", "factory_task_tickets"):
                values = section.get(key, [])
                if not isinstance(values, list) or any(
                    not isinstance(ticket, str) for ticket in values
                ):
                    return f"{key} must be a list of ticket strings"
            return facts, ModelDodVerifyOverlay.model_validate(section)
        except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
            return str(exc)


if __name__ == "__main__":
    sys.exit(ValidatorParentTicketCitation.main())
