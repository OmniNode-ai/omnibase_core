# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""How one severity renders — by token name, label, and icon (OMN-16884).

The model that replaces ``status_colors``. Three differences, each deliberate:

1. **A theme token NAME, not a colour value.** The name is validated against
   ``ModelRendererThemeContract``'s own fields, so a role cannot point at a
   token that does not exist, and the value comes from whichever theme instance
   is active (OMN-16882).
2. **A label and an icon, always.** Severity must never be conveyed by colour
   alone — the board has to stay legible to a colourblind operator and in a
   screenshot pasted into a monochrome channel.
3. **No ordering field.** Order is declared once on
   ``EnumStatusSeverity.severity_rank``; duplicating it here would let a config
   disagree with the enum about which tile is worse.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_renderer_theme_contract import (
    ModelRendererThemeContract,
)

__all__ = ["DEFAULT_SEVERITY_ROLES", "ModelSeverityRole"]


class ModelSeverityRole(BaseModel):
    """Presentation of one severity: theme token, text label, icon."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    severity: EnumStatusSeverity = Field(
        ...,
        description="Semantic severity this role renders",
    )
    theme_color_token: str = Field(
        ...,
        description=(
            "Name of the ModelRendererThemeContract token this severity resolves "
            "to (e.g. 'color_status_error'). A NAME, never a colour value."
        ),
        min_length=1,
    )
    label: str = Field(
        ...,
        description="Text label rendered for this severity; never colour alone",
        min_length=1,
    )
    icon: str = Field(
        ...,
        description="Icon/shape identifier rendered for this severity; distinct per severity",
        min_length=1,
    )

    @field_validator("theme_color_token")
    @classmethod
    def validate_theme_color_token(cls, value: str) -> str:
        """Reject a token name the theme contract does not define.

        Raises:
            ValueError: If ``value`` is not a field of
                ``ModelRendererThemeContract``.
        """
        if value not in ModelRendererThemeContract.model_fields:
            # error-ok: Pydantic field_validator rejects undefined theme token names
            raise ValueError(
                f"theme_color_token '{value}' is not a field of "
                f"ModelRendererThemeContract; a severity role must resolve "
                f"through the theme, and a hex value is never accepted here"
            )
        return value


#: The canonical severity role set: one role per severity, each with a distinct
#: label and a distinct icon, each resolving to a theme token by NAME. Used as
#: the default so a board is legible out of the box, and containing no colour
#: value, so gate GC.5 ("no hex literal in any ModelWidgetConfig* default")
#: holds by construction rather than by review.
DEFAULT_SEVERITY_ROLES: tuple[ModelSeverityRole, ...] = (
    ModelSeverityRole(
        severity=EnumStatusSeverity.CRITICAL,
        theme_color_token=EnumStatusSeverity.CRITICAL.theme_color_token,
        label="Critical",
        icon="octagon-x",
    ),
    ModelSeverityRole(
        severity=EnumStatusSeverity.ATTENTION,
        theme_color_token=EnumStatusSeverity.ATTENTION.theme_color_token,
        label="Attention",
        icon="triangle-alert",
    ),
    ModelSeverityRole(
        severity=EnumStatusSeverity.UNKNOWN,
        theme_color_token=EnumStatusSeverity.UNKNOWN.theme_color_token,
        label="Unknown",
        icon="question-diamond",
    ),
    ModelSeverityRole(
        severity=EnumStatusSeverity.NOMINAL,
        theme_color_token=EnumStatusSeverity.NOMINAL.theme_color_token,
        label="Nominal",
        icon="check-circle",
    ),
)
