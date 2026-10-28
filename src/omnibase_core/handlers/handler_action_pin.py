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

from omnibase_core.handlers.handler_action_pin_rules import (
    FULL_SHA,
    VALIDATOR_ID,
    extract_uses,
    is_candidate,
    is_local,
    split_ref,
)
from omnibase_core.models.action_pins.model_action_pin_check_input import (
    ModelActionPinCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["HandlerActionPin"]

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"
_THIRD_PARTY_REMEDIATION: Final[str] = (
    "Pin the action to the full 40-hex commit sha its tag resolves to, "
    "with the tag in a trailing comment."
)
_FIRST_PARTY_REMEDIATION: Final[str] = (
    "Reference our own repositories by the dev-merge tag of the commit "
    "(dev-YYYYMMDDhhmmss-<sha12>), never by a sha or a branch."
)


class HandlerActionPin:
    """COMPUTE handler that judges every ``uses:`` ref of the workflow files."""

    def handle(self, request: ModelActionPinCheckInput) -> ModelValidationReport:
        """Definition-B canonical entry-point: typed request in, typed report out."""
        overlay = request.overlay
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
                    validator_id=VALIDATOR_ID,
                    severity=severity,
                    location=location,
                    message=message,
                    remediation=remediation,
                )
            )

        for file in sorted(request.files, key=lambda f: f.path):
            if not is_candidate(file.path):
                continue
            for line, value in extract_uses(file.source):
                if is_local(value):
                    continue
                location = f"{file.path}:{line}"
                action, ref = split_ref(value)
                if not overlay.is_first_party(action):
                    if ref is None or FULL_SHA.fullmatch(ref) is None:
                        add(
                            "FAIL",
                            location,
                            f"{location}: third-party {value} is not pinned to a "
                            "full 40-hex commit sha",
                            _THIRD_PARTY_REMEDIATION,
                        )
                    continue
                if ref is not None and overlay.matches_tag(ref):
                    continue
                if ref == "main" and overlay.first_party_main == "warn":
                    add(
                        "WARN",
                        location,
                        f"{location}: first-party {value} rides main; replace it "
                        "with a dev-merge tag and remove this allowance",
                        _FIRST_PARTY_REMEDIATION,
                    )
                elif (
                    ref is not None
                    and FULL_SHA.fullmatch(ref) is not None
                    and value in exceptions
                ):
                    used.add(value)
                    add(
                        "WARN",
                        location,
                        f"{location}: first-party {value} is a known exception: "
                        f"{exceptions[value].reason}",
                        None,
                    )
                else:
                    add(
                        "FAIL",
                        location,
                        f"{location}: first-party {value} is not a dev-merge tag "
                        f"matching {overlay.tag_pattern}",
                        _FIRST_PARTY_REMEDIATION,
                    )

        if request.report_stale_exceptions:
            for uses, exc in sorted(exceptions.items()):
                if uses not in used:
                    add(
                        "WARN",
                        uses,
                        f"known exception {uses} ({exc.reason}) is no longer used; "
                        "remove it from the overlay",
                        None,
                    )

        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
