# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RendererThemeContract — versioned design-token contract artifact.

Phase 0 UI theming contract (OMN-13389, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6, §7).

Design tokens are declared here as **contract fields**, not prose. A renderer
that wants to apply a theme reads every token from this model — no literal color
or spacing value is permitted outside a ModelRendererThemeContract instance.
The explicit ``contract_version`` field makes schema drift detectable; the
``emit_ts_types.py`` pipeline mirrors this contract to TypeScript, and CI
diffs the generated file to gate drift.

Token taxonomy
--------------
Surfaces:
  color_background_primary / secondary / elevated

Text:
  color_text_primary / secondary / disabled

Brand / accent:
  color_accent_primary / secondary

Semantic status:
  color_status_success / warning / error / info

Borders:
  color_border_default / strong

Spacing scale (CSS rem strings):
  spacing_xs / sm / md / lg / xl

Typography:
  font_family_base, font_size_sm / md / lg,
  font_weight_normal / bold

Border radius:
  border_radius_sm / md / lg

All token fields are ``str`` — the contract is a *source of truth for values*,
not a CSS-in-Python library. Consumers emit whatever format their platform
needs (CSS custom properties, JS theme objects, iOS UIColor, etc.).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelRendererThemeContract"]


class ModelRendererThemeContract(BaseModel):
    """A versioned, platform-neutral design-token contract for renderers.

    Every renderer that declares ``supports_theming=True`` in its
    ``ModelRendererCapabilityContract`` must consume tokens from an instance
    of this model — it must never hard-code token values.

    ``contract_version`` is the authoritative version of this token set.
    Consumers should carry the version forward into their generated output (e.g.
    ``--theme-version: 1.0.0`` in CSS) so drift is always traceable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # ------------------------------------------------------------------
    # Identity / versioning
    # ------------------------------------------------------------------

    theme_id: str = Field(
        ...,
        description=(
            "Stable, namespaced theme identifier "
            "(e.g. 'onex.theme.dark.v1', 'onex.theme.light.v1')"
        ),
        min_length=1,
    )
    contract_version: ModelSemVer = Field(
        ...,
        description=(
            "Semantic version of this token contract. "
            "Bump when adding, removing, or renaming any token field."
        ),
    )

    # ------------------------------------------------------------------
    # Surface / background tokens
    # ------------------------------------------------------------------

    color_background_primary: str = Field(
        ...,
        description="Primary page/panel background (e.g. '#0f172a')",
        min_length=1,
    )
    color_background_secondary: str = Field(
        ...,
        description="Secondary / sidebar background",
        min_length=1,
    )
    color_background_elevated: str = Field(
        ...,
        description="Elevated surface background (cards, dropdowns)",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Text tokens
    # ------------------------------------------------------------------

    color_text_primary: str = Field(
        ...,
        description="Primary body text color",
        min_length=1,
    )
    color_text_secondary: str = Field(
        ...,
        description="Secondary / muted text color",
        min_length=1,
    )
    color_text_disabled: str = Field(
        ...,
        description="Disabled / placeholder text color",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Brand / accent tokens
    # ------------------------------------------------------------------

    color_accent_primary: str = Field(
        ...,
        description="Primary brand / interactive accent color",
        min_length=1,
    )
    color_accent_secondary: str = Field(
        ...,
        description="Secondary / hover accent color",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Semantic status tokens
    # ------------------------------------------------------------------

    color_status_success: str = Field(
        ...,
        description="Success / green semantic color",
        min_length=1,
    )
    color_status_warning: str = Field(
        ...,
        description="Warning / amber semantic color",
        min_length=1,
    )
    color_status_error: str = Field(
        ...,
        description="Error / red semantic color",
        min_length=1,
    )
    color_status_info: str = Field(
        ...,
        description="Informational / blue semantic color",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Border tokens
    # ------------------------------------------------------------------

    color_border_default: str = Field(
        ...,
        description="Default / subtle border color",
        min_length=1,
    )
    color_border_strong: str = Field(
        ...,
        description="Strong / emphasized border color",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Spacing scale (CSS rem strings)
    # ------------------------------------------------------------------

    spacing_xs: str = Field(
        ...,
        description="Extra-small spacing token (e.g. '0.25rem')",
        min_length=1,
    )
    spacing_sm: str = Field(
        ...,
        description="Small spacing token (e.g. '0.5rem')",
        min_length=1,
    )
    spacing_md: str = Field(
        ...,
        description="Medium / base spacing token (e.g. '1rem')",
        min_length=1,
    )
    spacing_lg: str = Field(
        ...,
        description="Large spacing token (e.g. '1.5rem')",
        min_length=1,
    )
    spacing_xl: str = Field(
        ...,
        description="Extra-large spacing token (e.g. '2rem')",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Typography tokens
    # ------------------------------------------------------------------

    font_family_base: str = Field(
        ...,
        description="Base / body font-family stack (e.g. \"'Inter', system-ui, sans-serif\")",
        min_length=1,
    )
    font_size_sm: str = Field(
        ...,
        description="Small font size (e.g. '0.875rem')",
        min_length=1,
    )
    font_size_md: str = Field(
        ...,
        description="Medium / body font size (e.g. '1rem')",
        min_length=1,
    )
    font_size_lg: str = Field(
        ...,
        description="Large font size (e.g. '1.125rem')",
        min_length=1,
    )
    font_weight_normal: str = Field(
        ...,
        description="Normal font weight (e.g. '400')",
        min_length=1,
    )
    font_weight_bold: str = Field(
        ...,
        description="Bold font weight (e.g. '700')",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Border radius tokens
    # ------------------------------------------------------------------

    border_radius_sm: str = Field(
        ...,
        description="Small border radius (e.g. '0.25rem')",
        min_length=1,
    )
    border_radius_md: str = Field(
        ...,
        description="Medium border radius (e.g. '0.5rem')",
        min_length=1,
    )
    border_radius_lg: str = Field(
        ...,
        description="Large border radius (e.g. '1rem')",
        min_length=1,
    )
