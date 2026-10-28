# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure handler for pre-commit hook repository pin parity (OMN-21433)."""

from __future__ import annotations

from omnibase_core.handlers.handler_precommit_pin_parity_rules import (
    VALIDATOR_ID,
    extract_pins,
    normalize_repo_url,
)
from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.models.precommit_pins.model_precommit_pin_parity_input import (
    ModelPrecommitPinParityInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["HandlerPrecommitPinParity"]


class HandlerPrecommitPinParity:
    """Judge each named repository's pins using caller-supplied commit times."""

    def handle(self, request: ModelPrecommitPinParityInput) -> ModelValidationReport:
        """Return FAIL for older pins and unresolved revs in multi-rev groups."""
        named = {normalize_repo_url(repo) for repo in request.rules.hook_repos}
        groups: dict[str, list[ModelPrecommitPin]] = {}
        for pin in extract_pins(request.source):
            repo = normalize_repo_url(pin.repo)
            if repo in named:
                groups.setdefault(repo, []).append(pin)

        times = {item.rev: item.committed_at for item in request.rev_times}
        findings: list[ModelValidationFindingEmbed] = []
        for pins in groups.values():
            revs = {pin.rev for pin in pins}
            if len(revs) < 2:
                continue
            resolved = sorted(rev for rev in revs if rev in times)
            newest = max(resolved, key=lambda rev: times[rev]) if resolved else None
            for pin in pins:
                location = f"{request.path}:{pin.line}"
                hooks = ", ".join(pin.hook_ids) or "(no hook IDs)"
                if pin.rev not in times:
                    message = (
                        f"{location}: {pin.repo} rev {pin.rev} for hooks {hooks} "
                        "has no committed_at; cannot establish parity with "
                        f"newest pin {newest or '(unresolved)'}"
                    )
                elif newest is not None and times[pin.rev] < times[newest]:
                    message = (
                        f"{location}: {pin.repo} rev {pin.rev} for hooks {hooks} "
                        f"is older than newest rev {newest}"
                    )
                else:
                    continue
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location=location,
                        message=message,
                        remediation=(
                            "Resolve missing commit times, then bump the hook's rev "
                            f"to the newest pin {newest or '(once resolved)'} "
                            "(or lower the newest pin if it is the wrong one)."
                        ),
                    )
                )

        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
