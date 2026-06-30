# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelRendererThemeContract (OMN-13389).

Acceptance criteria:
- Frozen Pydantic model, extra="forbid"
- Explicit version field (versioned contract artifact)
- Design tokens as typed fields — no hardcoded values in consumers
- A consumer fixture demonstrates theming from the contract with NO hardcoded tokens
- TS drift gate: model appears in emit_ts_types.py MODELS dict
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelRendererThemeContract
from omnibase_core.models.primitives.model_semver import ModelSemVer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_v1_dark() -> ModelRendererThemeContract:
    """Canonical dark-mode theme v1.0.0 — all required tokens explicit."""
    return ModelRendererThemeContract(
        theme_id="onex.theme.dark.v1",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        # Surface tokens
        color_background_primary="#0f172a",
        color_background_secondary="#1e293b",
        color_background_elevated="#334155",
        # Text tokens
        color_text_primary="#f8fafc",
        color_text_secondary="#94a3b8",
        color_text_disabled="#475569",
        # Brand / accent
        color_accent_primary="#6366f1",
        color_accent_secondary="#818cf8",
        # Semantic status tokens
        color_status_success="#22c55e",
        color_status_warning="#f59e0b",
        color_status_error="#ef4444",
        color_status_info="#38bdf8",
        # Border
        color_border_default="#334155",
        color_border_strong="#475569",
        # Spacing scale (CSS rem values as strings)
        spacing_xs="0.25rem",
        spacing_sm="0.5rem",
        spacing_md="1rem",
        spacing_lg="1.5rem",
        spacing_xl="2rem",
        # Typography
        font_family_base="'Inter', system-ui, sans-serif",
        font_size_sm="0.875rem",
        font_size_md="1rem",
        font_size_lg="1.125rem",
        font_weight_normal="400",
        font_weight_bold="700",
        # Border radii
        border_radius_sm="0.25rem",
        border_radius_md="0.5rem",
        border_radius_lg="1rem",
    )


def _make_v1_light() -> ModelRendererThemeContract:
    """Light-mode theme v1.0.0."""
    return ModelRendererThemeContract(
        theme_id="onex.theme.light.v1",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        color_background_primary="#ffffff",
        color_background_secondary="#f8fafc",
        color_background_elevated="#f1f5f9",
        color_text_primary="#0f172a",
        color_text_secondary="#475569",
        color_text_disabled="#94a3b8",
        color_accent_primary="#6366f1",
        color_accent_secondary="#818cf8",
        color_status_success="#16a34a",
        color_status_warning="#d97706",
        color_status_error="#dc2626",
        color_status_info="#0284c7",
        color_border_default="#e2e8f0",
        color_border_strong="#cbd5e1",
        spacing_xs="0.25rem",
        spacing_sm="0.5rem",
        spacing_md="1rem",
        spacing_lg="1.5rem",
        spacing_xl="2rem",
        font_family_base="'Inter', system-ui, sans-serif",
        font_size_sm="0.875rem",
        font_size_md="1rem",
        font_size_lg="1.125rem",
        font_weight_normal="400",
        font_weight_bold="700",
        border_radius_sm="0.25rem",
        border_radius_md="0.5rem",
        border_radius_lg="1rem",
    )


# ---------------------------------------------------------------------------
# Model contract tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelRendererThemeContractModel:
    """ModelRendererThemeContract satisfies the OMN-13389 model contract."""

    def test_creation_succeeds_with_all_required_fields(self) -> None:
        theme = _make_v1_dark()
        assert theme.theme_id == "onex.theme.dark.v1"
        assert theme.contract_version == ModelSemVer(major=1, minor=0, patch=0)

    def test_frozen_immutable(self) -> None:
        theme = _make_v1_dark()
        with pytest.raises(ValidationError):
            theme.color_background_primary = "#000000"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelRendererThemeContract(
                theme_id="t",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                color_background_primary="#000",
                color_background_secondary="#111",
                color_background_elevated="#222",
                color_text_primary="#fff",
                color_text_secondary="#ccc",
                color_text_disabled="#aaa",
                color_accent_primary="#123",
                color_accent_secondary="#456",
                color_status_success="#0f0",
                color_status_warning="#ff0",
                color_status_error="#f00",
                color_status_info="#00f",
                color_border_default="#333",
                color_border_strong="#444",
                spacing_xs="4px",
                spacing_sm="8px",
                spacing_md="16px",
                spacing_lg="24px",
                spacing_xl="32px",
                font_family_base="sans",
                font_size_sm="14px",
                font_size_md="16px",
                font_size_lg="18px",
                font_weight_normal="400",
                font_weight_bold="700",
                border_radius_sm="4px",
                border_radius_md="8px",
                border_radius_lg="16px",
                unknown_extra_field="bad",  # type: ignore[call-arg]
            )

    def test_version_field_is_modelsemver(self) -> None:
        theme = _make_v1_dark()
        assert isinstance(theme.contract_version, ModelSemVer)
        assert theme.contract_version.major == 1

    def test_theme_id_required_nonempty(self) -> None:
        with pytest.raises(ValidationError):
            ModelRendererThemeContract(
                theme_id="",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                color_background_primary="#000",
                color_background_secondary="#111",
                color_background_elevated="#222",
                color_text_primary="#fff",
                color_text_secondary="#ccc",
                color_text_disabled="#aaa",
                color_accent_primary="#123",
                color_accent_secondary="#456",
                color_status_success="#0f0",
                color_status_warning="#ff0",
                color_status_error="#f00",
                color_status_info="#00f",
                color_border_default="#333",
                color_border_strong="#444",
                spacing_xs="4px",
                spacing_sm="8px",
                spacing_md="16px",
                spacing_lg="24px",
                spacing_xl="32px",
                font_family_base="sans",
                font_size_sm="14px",
                font_size_md="16px",
                font_size_lg="18px",
                font_weight_normal="400",
                font_weight_bold="700",
                border_radius_sm="4px",
                border_radius_md="8px",
                border_radius_lg="16px",
            )

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            # Missing color_background_primary and many others
            ModelRendererThemeContract(  # type: ignore[call-arg]
                theme_id="t",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
            )

    def test_json_roundtrip(self) -> None:
        theme = _make_v1_dark()
        restored = ModelRendererThemeContract.model_validate_json(
            theme.model_dump_json()
        )
        assert restored == theme

    def test_json_schema_contains_contract_version(self) -> None:
        schema = ModelRendererThemeContract.model_json_schema()
        # contract_version must be a property in the JSON schema
        assert "contract_version" in schema.get("properties", {})

    def test_two_themes_at_different_versions_coexist(self) -> None:
        """Versioning allows multiple themes to coexist without collision."""
        dark_v1 = _make_v1_dark()
        dark_v2 = ModelRendererThemeContract(
            **{
                **dark_v1.model_dump(),
                "theme_id": "onex.theme.dark.v2",
                "contract_version": {"major": 2, "minor": 0, "patch": 0},
                "color_accent_primary": "#7c3aed",  # changed token
            }
        )
        assert dark_v1.contract_version.major == 1
        assert dark_v2.contract_version.major == 2
        assert dark_v1 != dark_v2

    def test_all_spacing_tokens_are_strings(self) -> None:
        theme = _make_v1_dark()
        for attr in (
            "spacing_xs",
            "spacing_sm",
            "spacing_md",
            "spacing_lg",
            "spacing_xl",
        ):
            assert isinstance(getattr(theme, attr), str), f"{attr} must be str"

    def test_all_color_tokens_are_strings(self) -> None:
        theme = _make_v1_dark()
        color_fields = [f for f in theme.model_fields if f.startswith("color_")]
        assert len(color_fields) > 0
        for field in color_fields:
            value = getattr(theme, field)
            assert isinstance(value, str), f"{field} must be str"


# ---------------------------------------------------------------------------
# Consumer fixture: a renderer themes from the contract — no hardcoded tokens
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRendererThemingFromContract:
    """A renderer consumes ModelRendererThemeContract with NO hardcoded tokens."""

    def test_renderer_fixture_reads_tokens_from_contract(self) -> None:
        """Renderer fixture builds its CSS var map purely from contract fields."""
        theme = _make_v1_dark()

        # Simulate a renderer building a CSS custom-property map.
        # This is the consumer pattern: every value comes from the contract —
        # no literal color/spacing/font value is hardcoded here.
        css_vars: dict[str, str] = {
            "--color-bg-primary": theme.color_background_primary,
            "--color-bg-secondary": theme.color_background_secondary,
            "--color-bg-elevated": theme.color_background_elevated,
            "--color-text-primary": theme.color_text_primary,
            "--color-text-secondary": theme.color_text_secondary,
            "--color-text-disabled": theme.color_text_disabled,
            "--color-accent": theme.color_accent_primary,
            "--color-accent-alt": theme.color_accent_secondary,
            "--color-status-success": theme.color_status_success,
            "--color-status-warning": theme.color_status_warning,
            "--color-status-error": theme.color_status_error,
            "--color-status-info": theme.color_status_info,
            "--color-border": theme.color_border_default,
            "--color-border-strong": theme.color_border_strong,
            "--spacing-xs": theme.spacing_xs,
            "--spacing-sm": theme.spacing_sm,
            "--spacing-md": theme.spacing_md,
            "--spacing-lg": theme.spacing_lg,
            "--spacing-xl": theme.spacing_xl,
            "--font-family": theme.font_family_base,
            "--font-size-sm": theme.font_size_sm,
            "--font-size-md": theme.font_size_md,
            "--font-size-lg": theme.font_size_lg,
            "--font-weight-normal": theme.font_weight_normal,
            "--font-weight-bold": theme.font_weight_bold,
            "--border-radius-sm": theme.border_radius_sm,
            "--border-radius-md": theme.border_radius_md,
            "--border-radius-lg": theme.border_radius_lg,
        }

        # Contract-version annotates the output so drift is detectable
        css_vars["--theme-version"] = str(theme.contract_version)

        # All values present and non-empty
        for var, value in css_vars.items():
            assert value, f"{var} resolved to empty string from contract"

        # Version annotation derived from contract — not hardcoded
        assert css_vars["--theme-version"] == "1.0.0"
        # Background primary from contract, not literal
        assert css_vars["--color-bg-primary"] == theme.color_background_primary

    def test_renderer_can_swap_themes_by_contract_swap(self) -> None:
        """Swapping the contract object is the only way to change tokens."""
        dark = _make_v1_dark()
        light = _make_v1_light()

        def render_background(theme: ModelRendererThemeContract) -> str:
            # Consumer reads from contract — NO hardcoded "#0f172a" or "#ffffff"
            return theme.color_background_primary

        assert render_background(dark) != render_background(light)
        assert render_background(dark) == dark.color_background_primary
        assert render_background(light) == light.color_background_primary

    def test_theme_as_json_schema_for_ts_drift(self) -> None:
        """JSON schema includes all token fields — forms the basis of the TS drift gate."""
        schema = ModelRendererThemeContract.model_json_schema()
        props = schema.get("properties", {})

        required_in_schema = {
            "theme_id",
            "contract_version",
            "color_background_primary",
            "color_text_primary",
            "color_accent_primary",
            "color_status_success",
            "spacing_md",
            "font_family_base",
            "border_radius_md",
        }
        missing = required_in_schema - set(props.keys())
        assert not missing, f"Schema missing properties: {missing}"


# ---------------------------------------------------------------------------
# TS drift gate: emit_ts_types.py includes ModelRendererThemeContract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTsDriftGate:
    """ModelRendererThemeContract must appear in the emit_ts_types MODELS dict."""

    def test_emit_ts_types_models_includes_renderer_theme_contract(self) -> None:
        """emit_ts_types.MODELS must include ModelRendererThemeContract."""
        from scripts import emit_ts_types  # type: ignore[import]

        assert "ModelRendererThemeContract" in emit_ts_types.MODELS, (
            "ModelRendererThemeContract is missing from emit_ts_types.MODELS — "
            "add it so the TS drift gate covers theme tokens"
        )
        assert (
            emit_ts_types.MODELS["ModelRendererThemeContract"]
            is ModelRendererThemeContract
        )

    def test_json_schema_round_trips_correctly(self) -> None:
        """Schema can be serialised to JSON without errors (production path)."""
        schema = ModelRendererThemeContract.model_json_schema()
        # Confirm it's JSON-serialisable (what emit_ts_types does)
        serialised = json.dumps(schema, indent=2)
        restored = json.loads(serialised)
        assert restored["title"] == "ModelRendererThemeContract"
