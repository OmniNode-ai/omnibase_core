# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for enforcement-related enums for replay safety infrastructure.

Tests cover:
- EnumEnforcementMode values
- EnumEffectDeterminism values
- EnumNonDeterministicSource values
- Enum string serialization

OMN-1150: Replay Safety Enforcement

.. versionadded:: 0.6.3
"""

from __future__ import annotations

from enum import Enum

import pytest

from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
from omnibase_core.enums.replay.enum_enforcement_mode import EnumEnforcementMode
from omnibase_core.enums.replay.enum_non_deterministic_source import (
    EnumNonDeterministicSource,
)

# =============================================================================
# TEST ENUM_ENFORCEMENT_MODE
# =============================================================================


@pytest.mark.unit
class TestEnumEnforcementModeValues:
    """Test cases for EnumEnforcementMode enum values."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values are present."""
        assert hasattr(EnumEnforcementMode, "STRICT")
        assert hasattr(EnumEnforcementMode, "WARN")
        assert hasattr(EnumEnforcementMode, "PERMISSIVE")
        assert hasattr(EnumEnforcementMode, "MOCKED")

    def test_enum_values_are_correct(self) -> None:
        """Test that enum values have correct string values."""
        assert EnumEnforcementMode.STRICT.value == "strict"
        assert EnumEnforcementMode.WARN.value == "warn"
        assert EnumEnforcementMode.PERMISSIVE.value == "permissive"
        assert EnumEnforcementMode.MOCKED.value == "mocked"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 4 values."""
        values = list(EnumEnforcementMode)
        assert len(values) == 4

    def test_all_expected_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {"strict", "warn", "permissive", "mocked"}
        actual_values = {member.value for member in EnumEnforcementMode}
        assert actual_values == expected_values


@pytest.mark.unit
class TestEnumEnforcementModeStringBehavior:
    """Test string enum behavior for EnumEnforcementMode."""

    def test_enum_is_string(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEnforcementMode, str)
        assert issubclass(EnumEnforcementMode, Enum)

    def test_enum_string_comparison(self) -> None:
        """Test string comparison behavior."""
        assert EnumEnforcementMode.STRICT == "strict"
        assert EnumEnforcementMode.WARN == "warn"
        assert EnumEnforcementMode.PERMISSIVE == "permissive"
        assert EnumEnforcementMode.MOCKED == "mocked"

    def test_enum_equality(self) -> None:
        """Test enum equality."""
        assert EnumEnforcementMode.STRICT == EnumEnforcementMode.STRICT
        assert EnumEnforcementMode.STRICT != EnumEnforcementMode.WARN

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumEnforcementMode.STRICT in EnumEnforcementMode
        assert "strict" in EnumEnforcementMode
        assert "invalid_mode" not in EnumEnforcementMode


@pytest.mark.unit
class TestEnumEnforcementModeSerialization:
    """Test enum serialization for EnumEnforcementMode."""

    def test_enum_serialization(self) -> None:
        """Test enum serialization via .value property."""
        assert EnumEnforcementMode.STRICT.value == "strict"
        assert EnumEnforcementMode.WARN.value == "warn"
        assert EnumEnforcementMode.PERMISSIVE.value == "permissive"
        assert EnumEnforcementMode.MOCKED.value == "mocked"

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumEnforcementMode("strict") == EnumEnforcementMode.STRICT
        assert EnumEnforcementMode("warn") == EnumEnforcementMode.WARN
        assert EnumEnforcementMode("permissive") == EnumEnforcementMode.PERMISSIVE
        assert EnumEnforcementMode("mocked") == EnumEnforcementMode.MOCKED

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEnforcementMode("invalid_mode")

        with pytest.raises(ValueError):
            EnumEnforcementMode("")


@pytest.mark.unit
class TestEnumEnforcementModeDocstring:
    """Test enum documentation for EnumEnforcementMode."""

    def test_enum_has_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumEnforcementMode.__doc__ is not None
        assert "enforcement" in EnumEnforcementMode.__doc__.lower()


# =============================================================================
# TEST ENUM_EFFECT_DETERMINISM
# =============================================================================


@pytest.mark.unit
class TestEnumEffectDeterminismValues:
    """Test cases for EnumEffectDeterminism enum values."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values are present."""
        assert hasattr(EnumEffectDeterminism, "DETERMINISTIC")
        assert hasattr(EnumEffectDeterminism, "NON_DETERMINISTIC")
        assert hasattr(EnumEffectDeterminism, "UNKNOWN")

    def test_enum_values_are_correct(self) -> None:
        """Test that enum values have correct string values."""
        assert EnumEffectDeterminism.DETERMINISTIC.value == "deterministic"
        assert EnumEffectDeterminism.NON_DETERMINISTIC.value == "non_deterministic"
        assert EnumEffectDeterminism.UNKNOWN.value == "unknown"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 3 values."""
        values = list(EnumEffectDeterminism)
        assert len(values) == 3

    def test_all_expected_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {"deterministic", "non_deterministic", "unknown"}
        actual_values = {member.value for member in EnumEffectDeterminism}
        assert actual_values == expected_values


@pytest.mark.unit
class TestEnumEffectDeterminismStringBehavior:
    """Test string enum behavior for EnumEffectDeterminism."""

    def test_enum_is_string(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEffectDeterminism, str)
        assert issubclass(EnumEffectDeterminism, Enum)

    def test_enum_string_comparison(self) -> None:
        """Test string comparison behavior."""
        assert EnumEffectDeterminism.DETERMINISTIC == "deterministic"
        assert EnumEffectDeterminism.NON_DETERMINISTIC == "non_deterministic"
        assert EnumEffectDeterminism.UNKNOWN == "unknown"

    def test_enum_equality(self) -> None:
        """Test enum equality."""
        assert (
            EnumEffectDeterminism.DETERMINISTIC == EnumEffectDeterminism.DETERMINISTIC
        )
        assert (
            EnumEffectDeterminism.DETERMINISTIC
            != EnumEffectDeterminism.NON_DETERMINISTIC
        )


@pytest.mark.unit
class TestEnumEffectDeterminismSerialization:
    """Test enum serialization for EnumEffectDeterminism."""

    def test_enum_serialization(self) -> None:
        """Test enum serialization via .value property."""
        assert EnumEffectDeterminism.DETERMINISTIC.value == "deterministic"
        assert EnumEffectDeterminism.NON_DETERMINISTIC.value == "non_deterministic"
        assert EnumEffectDeterminism.UNKNOWN.value == "unknown"

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert (
            EnumEffectDeterminism("deterministic")
            == EnumEffectDeterminism.DETERMINISTIC
        )
        assert (
            EnumEffectDeterminism("non_deterministic")
            == EnumEffectDeterminism.NON_DETERMINISTIC
        )
        assert EnumEffectDeterminism("unknown") == EnumEffectDeterminism.UNKNOWN

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEffectDeterminism("invalid")


@pytest.mark.unit
class TestEnumEffectDeterminismDocstring:
    """Test enum documentation for EnumEffectDeterminism."""

    def test_enum_has_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumEffectDeterminism.__doc__ is not None
        assert "determinism" in EnumEffectDeterminism.__doc__.lower()


# =============================================================================
# TEST ENUM_NON_DETERMINISTIC_SOURCE
# =============================================================================


@pytest.mark.unit
class TestEnumNonDeterministicSourceValues:
    """Test cases for EnumNonDeterministicSource enum values."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values are present."""
        assert hasattr(EnumNonDeterministicSource, "TIME")
        assert hasattr(EnumNonDeterministicSource, "RANDOM")
        assert hasattr(EnumNonDeterministicSource, "UUID")
        assert hasattr(EnumNonDeterministicSource, "NETWORK")
        assert hasattr(EnumNonDeterministicSource, "DATABASE")
        assert hasattr(EnumNonDeterministicSource, "FILESYSTEM")
        assert hasattr(EnumNonDeterministicSource, "ENVIRONMENT")

    def test_enum_values_are_correct(self) -> None:
        """Test that enum values have correct string values."""
        assert EnumNonDeterministicSource.TIME.value == "time"
        assert EnumNonDeterministicSource.RANDOM.value == "random"
        assert EnumNonDeterministicSource.UUID.value == "uuid"
        assert EnumNonDeterministicSource.NETWORK.value == "network"
        assert EnumNonDeterministicSource.DATABASE.value == "database"
        assert EnumNonDeterministicSource.FILESYSTEM.value == "filesystem"
        assert EnumNonDeterministicSource.ENVIRONMENT.value == "environment"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 7 values."""
        values = list(EnumNonDeterministicSource)
        assert len(values) == 7

    def test_all_expected_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "time",
            "random",
            "uuid",
            "network",
            "database",
            "filesystem",
            "environment",
        }
        actual_values = {member.value for member in EnumNonDeterministicSource}
        assert actual_values == expected_values


@pytest.mark.unit
class TestEnumNonDeterministicSourceStringBehavior:
    """Test string enum behavior for EnumNonDeterministicSource."""

    def test_enum_is_string(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumNonDeterministicSource, str)
        assert issubclass(EnumNonDeterministicSource, Enum)

    def test_enum_string_comparison(self) -> None:
        """Test string comparison behavior."""
        assert EnumNonDeterministicSource.TIME == "time"
        assert EnumNonDeterministicSource.RANDOM == "random"
        assert EnumNonDeterministicSource.UUID == "uuid"
        assert EnumNonDeterministicSource.NETWORK == "network"
        assert EnumNonDeterministicSource.DATABASE == "database"
        assert EnumNonDeterministicSource.FILESYSTEM == "filesystem"
        assert EnumNonDeterministicSource.ENVIRONMENT == "environment"

    def test_enum_equality(self) -> None:
        """Test enum equality."""
        assert EnumNonDeterministicSource.TIME == EnumNonDeterministicSource.TIME
        assert EnumNonDeterministicSource.TIME != EnumNonDeterministicSource.RANDOM


@pytest.mark.unit
class TestEnumNonDeterministicSourceSerialization:
    """Test enum serialization for EnumNonDeterministicSource."""

    def test_enum_serialization(self) -> None:
        """Test enum serialization via .value property."""
        assert EnumNonDeterministicSource.TIME.value == "time"
        assert EnumNonDeterministicSource.NETWORK.value == "network"
        assert EnumNonDeterministicSource.DATABASE.value == "database"

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumNonDeterministicSource("time") == EnumNonDeterministicSource.TIME
        assert EnumNonDeterministicSource("random") == EnumNonDeterministicSource.RANDOM
        assert EnumNonDeterministicSource("uuid") == EnumNonDeterministicSource.UUID
        assert (
            EnumNonDeterministicSource("network") == EnumNonDeterministicSource.NETWORK
        )
        assert (
            EnumNonDeterministicSource("database")
            == EnumNonDeterministicSource.DATABASE
        )
        assert (
            EnumNonDeterministicSource("filesystem")
            == EnumNonDeterministicSource.FILESYSTEM
        )
        assert (
            EnumNonDeterministicSource("environment")
            == EnumNonDeterministicSource.ENVIRONMENT
        )

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumNonDeterministicSource("invalid_source")


@pytest.mark.unit
class TestEnumNonDeterministicSourceDocstring:
    """Test enum documentation for EnumNonDeterministicSource."""

    def test_enum_has_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumNonDeterministicSource.__doc__ is not None
        assert "non-determinism" in EnumNonDeterministicSource.__doc__.lower()


# =============================================================================
# TEST ENUM ITERATION
# =============================================================================


@pytest.mark.unit
class TestEnumIteration:
    """Test enum iteration for all enforcement enums."""

    def test_enforcement_mode_iteration(self) -> None:
        """Test that we can iterate over EnumEnforcementMode values."""
        values = list(EnumEnforcementMode)
        assert EnumEnforcementMode.STRICT in values
        assert EnumEnforcementMode.WARN in values
        assert EnumEnforcementMode.PERMISSIVE in values
        assert EnumEnforcementMode.MOCKED in values

    def test_effect_determinism_iteration(self) -> None:
        """Test that we can iterate over EnumEffectDeterminism values."""
        values = list(EnumEffectDeterminism)
        assert EnumEffectDeterminism.DETERMINISTIC in values
        assert EnumEffectDeterminism.NON_DETERMINISTIC in values
        assert EnumEffectDeterminism.UNKNOWN in values

    def test_non_deterministic_source_iteration(self) -> None:
        """Test that we can iterate over EnumNonDeterministicSource values."""
        values = list(EnumNonDeterministicSource)
        assert EnumNonDeterministicSource.TIME in values
        assert EnumNonDeterministicSource.RANDOM in values
        assert EnumNonDeterministicSource.UUID in values
        assert EnumNonDeterministicSource.NETWORK in values
        assert EnumNonDeterministicSource.DATABASE in values
        assert EnumNonDeterministicSource.FILESYSTEM in values
        assert EnumNonDeterministicSource.ENVIRONMENT in values


# =============================================================================
# TEST JSON SERIALIZATION COMPATIBILITY
# =============================================================================


@pytest.mark.unit
class TestJsonSerializationCompatibility:
    """Test JSON serialization compatibility for all enums."""

    def test_enforcement_mode_json_compatible(self) -> None:
        """Test EnumEnforcementMode is JSON serializable."""
        import json

        data = {"mode": EnumEnforcementMode.STRICT.value}
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        assert loaded["mode"] == "strict"

    def test_effect_determinism_json_compatible(self) -> None:
        """Test EnumEffectDeterminism is JSON serializable."""
        import json

        data = {"determinism": EnumEffectDeterminism.NON_DETERMINISTIC.value}
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        assert loaded["determinism"] == "non_deterministic"

    def test_non_deterministic_source_json_compatible(self) -> None:
        """Test EnumNonDeterministicSource is JSON serializable."""
        import json

        data = {"source": EnumNonDeterministicSource.NETWORK.value}
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        assert loaded["source"] == "network"
