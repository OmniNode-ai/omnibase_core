# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumEnvelopeValidationFailureType."""

import pytest

from omnibase_core.enums.enum_envelope_validation_failure_type import (
    EnumEnvelopeValidationFailureType,
)


class TestEnumEnvelopeValidationFailureTypeValues:
    """Tests for EnumEnvelopeValidationFailureType member values."""

    def test_all_members_present(self) -> None:
        """All expected members are present in the enum."""
        expected_values = {
            "missing_correlation_id",
            "invalid_envelope_structure",
            "empty_payload",
            "type_mismatch",
            "missing_message_id",
            "missing_entity_id",
            "unknown",
        }
        actual_values = {member.value for member in EnumEnvelopeValidationFailureType}
        assert actual_values == expected_values

    def test_missing_correlation_id_value(self) -> None:
        """MISSING_CORRELATION_ID has the correct string value."""
        assert (
            EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID.value
            == "missing_correlation_id"
        )

    def test_invalid_envelope_structure_value(self) -> None:
        """INVALID_ENVELOPE_STRUCTURE has the correct string value."""
        assert (
            EnumEnvelopeValidationFailureType.INVALID_ENVELOPE_STRUCTURE.value
            == "invalid_envelope_structure"
        )

    def test_empty_payload_value(self) -> None:
        """EMPTY_PAYLOAD has the correct string value."""
        assert EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD.value == "empty_payload"

    def test_type_mismatch_value(self) -> None:
        """TYPE_MISMATCH has the correct string value."""
        assert EnumEnvelopeValidationFailureType.TYPE_MISMATCH.value == "type_mismatch"

    def test_unknown_value(self) -> None:
        """UNKNOWN has the correct string value."""
        assert EnumEnvelopeValidationFailureType.UNKNOWN.value == "unknown"


class TestEnumEnvelopeValidationFailureTypeStrBehavior:
    """Tests for str-based enum behavior (StrValueHelper mixin)."""

    def test_enum_is_string(self) -> None:
        """Enum members are instances of str."""
        for member in EnumEnvelopeValidationFailureType:
            assert isinstance(member, str)

    def test_str_comparison(self) -> None:
        """Enum members compare equal to their string values."""
        assert (
            EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID
            == "missing_correlation_id"
        )

    def test_from_string(self) -> None:
        """Enum can be constructed from its string value."""
        result = EnumEnvelopeValidationFailureType("empty_payload")
        assert result == EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD

    def test_invalid_string_raises(self) -> None:
        """Constructing from an invalid string raises ValueError."""
        with pytest.raises(ValueError):
            EnumEnvelopeValidationFailureType("not_a_real_type")


class TestEnumEnvelopeValidationFailureTypeExport:
    """Tests for __all__ and package-level export."""

    def test_importable_from_enums_package(self) -> None:
        """EnumEnvelopeValidationFailureType is importable from the enums package."""
        from omnibase_core.enums import EnumEnvelopeValidationFailureType as Imported

        assert Imported is EnumEnvelopeValidationFailureType
