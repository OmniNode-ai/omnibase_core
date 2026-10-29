# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerActionPin -- how a workflow ``uses:`` ref must be pinned.

* Third-party actions: the ref must be a full 40-hex commit sha (FAIL otherwise).
* First-party actions (the organisations the overlay names): the ref must be a
  dev-merge tag that fully matches the overlay's tag pattern (FAIL otherwise).
  A first-party sha is a FAIL unless the overlay lists that exact ``uses``
  value as a known exception with a reason (WARN). A first-party ``@main`` is a
  FAIL, or a WARN to remove later when the overlay keeps the earlier allowance.
* Local ``./`` actions carry no external ref and pass.

On a full-tree scan a known exception no file uses any more is a WARN, so it is
removed. Pure: no filesystem, no clock, no global state. Ticket: OMN-17427.
"""

from __future__ import annotations

from typing import Final, Literal

from omnibase_core.models.action_pins.model_action_pin_check_input import (
    ModelActionPinCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_action_pin_check_effect.matcher_action_pin import (
    extract_uses,
    is_candidate,
    is_full_sha,
    is_local,
    split_ref,
)

__all__ = ["HandlerActionPin"]

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class HandlerActionPin:
    """COMPUTE handler that judges every ``uses:`` ref of the workflow files."""

    def handle(self, request: ModelActionPinCheckInput) -> ModelValidationReport:
        """Definition-B canonical entry-point: typed request in, typed report out."""
        overlay = request.overlay
        rules = request.rules
        exceptions = {exc.uses: exc for exc in overlay.known_exceptions}
        used: set[str] = set()
        findings: list[ModelValidationFindingEmbed] = []

        def add(
            severity: Literal["WARN", "FAIL"],
            location: str,
            message: str,
            remediation: str | None,
        ) -> None:
            findings.append(
                ModelValidationFindingEmbed(
                    validator_id=rules.report_validator_name,
                    severity=severity,
                    location=location,
                    message=message,
                    remediation=remediation,
                )
            )

        for file in sorted(request.files, key=lambda f: f.path):
            if not is_candidate(file.path, rules):
                continue
            for line, value in extract_uses(file.source, rules):
                if is_local(value, rules):
                    continue
                location = f"{file.path}:{line}"
                action, ref = split_ref(value)
                if not overlay.is_first_party(action):
                    if not is_full_sha(ref, rules):
                        add(
                            "FAIL",
                            location,
                            rules.third_party_message.format(
                                location=location, value=value
                            ),
                            rules.third_party_remediation,
                        )
                    continue
                is_sha = is_full_sha(ref, rules)
                if (
                    ref is not None
                    and not is_sha
                    and ref != rules.main_ref
                    and overlay.matches_tag(ref)
                ):
                    continue
                if ref == rules.main_ref and overlay.first_party_main == "warn":
                    add(
                        "WARN",
                        location,
                        rules.first_party_main_message.format(
                            location=location, value=value
                        ),
                        rules.first_party_remediation,
                    )
                elif is_sha and value in exceptions:
                    used.add(value)
                    add(
                        "WARN",
                        location,
                        rules.known_exception_message.format(
                            location=location,
                            value=value,
                            reason=exceptions[value].reason,
                        ),
                        None,
                    )
                else:
                    add(
                        "FAIL",
                        location,
                        rules.first_party_tag_message.format(
                            location=location,
                            value=value,
                            tag_pattern=overlay.tag_pattern,
                        ),
                        rules.first_party_remediation,
                    )

        if request.report_stale_exceptions:
            for uses, exc in sorted(exceptions.items()):
                if uses not in used:
                    add(
                        "WARN",
                        uses,
                        rules.stale_exception_message.format(
                            uses=uses, reason=exc.reason
                        ),
                        None,
                    )

        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(rules.report_validator_name,),
        )
