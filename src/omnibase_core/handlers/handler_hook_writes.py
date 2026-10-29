# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure handler requiring pre-commit hooks to check without rewriting (OMN-21498)."""

from __future__ import annotations

import re
from typing import Final

from omnibase_core.handlers.handler_hook_writes_rules import (
    VALIDATOR_ID,
    is_check_only,
    parse_hooks,
)
from omnibase_core.models.hook_writes.model_hook_writes_check_input import (
    ModelHookWritesCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["HandlerHookWrites"]

_REMEDIATION: Final[str] = (
    "Make the hook check-only: run the tool in its check or diff mode, or refuse "
    "with a message that names the command that fixes the file. "
    "A hook never rewrites the tree it checks."
)


class HandlerHookWrites:
    """COMPUTE handler judging hooks using only the supplied overlay and sources."""

    def handle(self, request: ModelHookWritesCheckInput) -> ModelValidationReport:
        """Return one finding per rewriting hook in file order, then hook order."""
        overlay = request.overlay
        findings: list[ModelValidationFindingEmbed] = []
        for file in request.files:
            for hook in parse_hooks(file.path, file.source):
                command = hook.command
                reasons = [
                    f"{signal.id}: {signal.reason}"
                    for signal in overlay.signals
                    if re.search(signal.pattern, command)
                    and not (signal.unless and re.search(signal.unless, command))
                ]
                rewriting = overlay.rewriting_hook(hook.id)
                if rewriting is not None and not is_check_only(hook, rewriting):
                    reasons.append(
                        f"hook id {hook.id} rewrites files: {rewriting.reason}"
                    )
                if reasons:
                    location = f"{file.path}::{hook.id}"
                    findings.append(
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            location=location,
                            rule_id=VALIDATOR_ID,
                            message=(
                                f"{location}: the hook rewrites files "
                                f"({'; '.join(reasons)})"
                            ),
                            remediation=_REMEDIATION,
                        )
                    )
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
