# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelUnavailableBehavior — skill unavailability presentation contract.

Skills declare this block to control what a user experiences when the skill's
activation or applicability scope is not satisfied. This prevents the silent
disappearance of skills in non-OmniNode contexts and gives alpha testers a
path to understand why a skill is missing.

The four modes (hidden | noop | warn | block) mirror the enforcement tier
vocabulary intentionally: they describe user-visible outcome, not enforcement
severity.

diagnostics: explain (opt-in):
    When set, a separate discovery command (e.g. /onex:doctor) lists hidden
    skills with structured reasons. Without this, users in external contexts
    cannot discover that skills exist but are suppressed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_diagnostics_mode import EnumDiagnosticsMode
from omnibase_core.enums.enum_unavailable_mode import EnumUnavailableMode


class ModelUnavailableBehavior(BaseModel):
    """
    Skill unavailability presentation contract.

    Controls what a user experiences when a skill's activation or applicability
    scope is not satisfied for the current session or invocation context.

    Skills that omit this block default to ``hidden`` with ``silent``
    diagnostics — the safe default that avoids confusing non-OmniNode users
    with unfamiliar skill names.

    Attributes:
        default:     Presentation mode when scope is not satisfied.
        diagnostics: Whether to emit structured reasons via discovery commands.

    Example YAML surface:

    .. code-block:: yaml

        unavailable_behavior:
          default: hidden
          diagnostics: explain

    See Also:
        - :class:`~omnibase_core.enums.enum_unavailable_mode.EnumUnavailableMode`:
          Available presentation modes.
        - :class:`~omnibase_core.enums.enum_diagnostics_mode.EnumDiagnosticsMode`:
          Diagnostics opt-in.
        - :class:`~omnibase_core.models.scope.model_enforcement_scope.ModelEnforcementScope`:
          Parent scope model for skills.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    default: EnumUnavailableMode = Field(
        default=EnumUnavailableMode.HIDDEN,
        description=(
            "Presentation mode when the skill's scope is not satisfied. "
            "Defaults to 'hidden' to avoid confusing non-OmniNode users."
        ),
    )
    diagnostics: EnumDiagnosticsMode = Field(
        default=EnumDiagnosticsMode.SILENT,
        description=(
            "Whether to emit structured unavailability reasons via /onex:doctor "
            "or equivalent discovery commands. Set 'explain' for alpha-tester profiles."
        ),
    )


__all__ = ["ModelUnavailableBehavior"]
