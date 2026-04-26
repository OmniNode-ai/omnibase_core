# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumNormalizationFamily enum (OMN-9759).

Phase 1 of the corpus classification and normalization layer
(parent epic OMN-9757). EnumNormalizationFamily classifies the family
of contract migrations being applied during normalization.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_normalization_family import EnumNormalizationFamily


@pytest.mark.unit
class TestEnumNormalizationFamily:
    """Test cases for EnumNormalizationFamily enum."""

    def test_top_families_present(self) -> None:
        """Required top-level migration families are present (per plan spec)."""
        required = {
            "family_legacy_input_output_model",
            "family_legacy_event_bus",
            "family_legacy_metadata",
            "family_legacy_handler_routing",
            "family_required_now_optional",
            "family_misc_extra_fields",
            "family_handler_block",
            "family_descriptor_block",
            "family_terminal_event",
            "family_event_schema_evolution",
            "family_state_machine",
            "family_dod_evidence_schema",
            "family_custom_validator",
            "family_node_type_alias",
        }
        actual = {f.value for f in EnumNormalizationFamily}
        assert required.issubset(actual)

    def test_member_count_is_fourteen(self) -> None:
        """Acceptance criterion: exactly 14 members."""
        assert len(list(EnumNormalizationFamily)) == 14

    def test_enum_inheritance(self) -> None:
        """Inherits from str and Enum (canonical pattern)."""
        assert issubclass(EnumNormalizationFamily, str)
        assert issubclass(EnumNormalizationFamily, Enum)

    def test_enum_string_behavior(self) -> None:
        """Members behave as strings."""
        family = EnumNormalizationFamily.FAMILY_LEGACY_INPUT_OUTPUT_MODEL
        assert isinstance(family, str)
        assert family == "family_legacy_input_output_model"

    def test_enum_membership(self) -> None:
        """Membership lookup by value."""
        values = {member.value for member in EnumNormalizationFamily}
        assert "family_legacy_event_bus" in values
        assert "family_does_not_exist" not in values

    def test_enum_deserialization(self) -> None:
        """Constructible from value string."""
        family = EnumNormalizationFamily("family_state_machine")
        assert family is EnumNormalizationFamily.FAMILY_STATE_MACHINE

    def test_enum_invalid_value_raises(self) -> None:
        """Invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumNormalizationFamily("family_invalid")

    def test_exported_from_enums_package(self) -> None:
        """Enum is re-exported from omnibase_core.enums."""
        from omnibase_core import enums

        assert hasattr(enums, "EnumNormalizationFamily")
        assert enums.EnumNormalizationFamily is EnumNormalizationFamily
        assert "EnumNormalizationFamily" in enums.__all__
