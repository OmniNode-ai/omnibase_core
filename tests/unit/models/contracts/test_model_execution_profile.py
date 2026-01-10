# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelExecutionProfile.

Tests execution profile configuration including:
- Basic creation and validation
- Phase ordering and phase_order property
- Nondeterministic allowed phases validation
- Immutability

See Also:
    - OMN-1227: ProtocolConstraintValidator for SPI
    - OMN-1292: Core Models for ProtocolConstraintValidator
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)


@pytest.mark.unit
class TestModelExecutionProfileCreation:
    """Tests for ModelExecutionProfile creation."""

    def test_default_creation(self) -> None:
        """Test creation with all defaults."""
        profile = ModelExecutionProfile()
        assert profile.phases == list(DEFAULT_EXECUTION_PHASES)
        assert profile.nondeterministic_allowed_phases == []

    def test_custom_phases(self) -> None:
        """Test creation with custom phases."""
        profile = ModelExecutionProfile(phases=["init", "execute", "cleanup"])
        assert profile.phases == ["init", "execute", "cleanup"]

    def test_with_nondeterministic_allowed_phases(self) -> None:
        """Test creation with nondeterministic_allowed_phases."""
        profile = ModelExecutionProfile(
            phases=["init", "execute", "cleanup"],
            nondeterministic_allowed_phases=["execute"],
        )
        assert profile.nondeterministic_allowed_phases == ["execute"]

    def test_multiple_nondeterministic_phases(self) -> None:
        """Test creation with multiple nondeterministic phases."""
        profile = ModelExecutionProfile(
            phases=["init", "execute", "emit", "cleanup"],
            nondeterministic_allowed_phases=["execute", "emit"],
        )
        assert profile.nondeterministic_allowed_phases == ["execute", "emit"]


@pytest.mark.unit
class TestPhaseOrderProperty:
    """Tests for phase_order computed property."""

    def test_phase_order_default_phases(self) -> None:
        """Test phase_order with default phases."""
        profile = ModelExecutionProfile()
        phase_order = profile.phase_order
        assert phase_order["preflight"] == 0
        assert phase_order["before"] == 1
        assert phase_order["execute"] == 2
        assert phase_order["after"] == 3
        assert phase_order["emit"] == 4
        assert phase_order["finalize"] == 5

    def test_phase_order_custom_phases(self) -> None:
        """Test phase_order with custom phases."""
        profile = ModelExecutionProfile(phases=["init", "execute", "cleanup"])
        phase_order = profile.phase_order
        assert phase_order == {"init": 0, "execute": 1, "cleanup": 2}

    def test_phase_order_single_phase(self) -> None:
        """Test phase_order with single phase."""
        profile = ModelExecutionProfile(phases=["main"])
        assert profile.phase_order == {"main": 0}

    def test_phase_order_returns_fresh_dict(self) -> None:
        """Test that phase_order returns a fresh dict each time."""
        profile = ModelExecutionProfile(phases=["init", "execute"])
        order1 = profile.phase_order
        order2 = profile.phase_order
        # Should be equal but not the same object
        assert order1 == order2
        # Modifying one should not affect the other
        order1["modified"] = 999
        assert "modified" not in order2


@pytest.mark.unit
class TestNondeterministicPhasesValidation:
    """Tests for nondeterministic_allowed_phases validation."""

    def test_nondeterministic_phases_must_be_subset(self) -> None:
        """Test that nondeterministic_allowed_phases must be subset of phases."""
        with pytest.raises(
            ValidationError, match="nondeterministic_allowed_phases contains phases"
        ):
            ModelExecutionProfile(
                phases=["init", "execute"],
                nondeterministic_allowed_phases=["cleanup"],  # Not in phases
            )

    def test_multiple_invalid_nondeterministic_phases(self) -> None:
        """Test error message includes all invalid phases."""
        with pytest.raises(ValidationError, match="nondeterministic_allowed_phases"):
            ModelExecutionProfile(
                phases=["init", "execute"],
                nondeterministic_allowed_phases=["cleanup", "unknown"],
            )

    def test_empty_nondeterministic_phases_valid(self) -> None:
        """Test that empty nondeterministic_allowed_phases is valid."""
        profile = ModelExecutionProfile(
            phases=["init", "execute"],
            nondeterministic_allowed_phases=[],
        )
        assert profile.nondeterministic_allowed_phases == []

    def test_all_phases_nondeterministic_valid(self) -> None:
        """Test that all phases can be nondeterministic."""
        profile = ModelExecutionProfile(
            phases=["init", "execute", "cleanup"],
            nondeterministic_allowed_phases=["init", "execute", "cleanup"],
        )
        assert set(profile.nondeterministic_allowed_phases) == set(profile.phases)


@pytest.mark.unit
class TestPhasesValidation:
    """Tests for phases field validation."""

    def test_phases_must_be_unique(self) -> None:
        """Test that phases must contain unique values."""
        with pytest.raises(ValidationError, match="phases must contain unique values"):
            ModelExecutionProfile(phases=["init", "execute", "init"])

    def test_phases_must_be_non_empty_strings(self) -> None:
        """Test that phases must be non-empty strings."""
        with pytest.raises(ValidationError, match="phases must be non-empty strings"):
            ModelExecutionProfile(phases=["init", "", "cleanup"])

    def test_phases_whitespace_only_rejected(self) -> None:
        """Test that whitespace-only phases are rejected."""
        with pytest.raises(ValidationError, match="phases must be non-empty strings"):
            ModelExecutionProfile(phases=["init", "   ", "cleanup"])


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_frozen_model(self) -> None:
        """Test that model is frozen and cannot be modified."""
        profile = ModelExecutionProfile()
        with pytest.raises(ValidationError):
            profile.phases = ["modified"]  # type: ignore[misc]

    def test_nondeterministic_phases_frozen(self) -> None:
        """Test that nondeterministic_allowed_phases cannot be modified."""
        profile = ModelExecutionProfile(
            phases=["init", "execute"],
            nondeterministic_allowed_phases=["execute"],
        )
        with pytest.raises(ValidationError):
            profile.nondeterministic_allowed_phases = ["init"]  # type: ignore[misc]


@pytest.mark.unit
class TestModelFromAttributes:
    """Tests for from_attributes compatibility."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "phases": ["init", "execute", "cleanup"],
            "nondeterministic_allowed_phases": ["execute"],
        }
        profile = ModelExecutionProfile.model_validate(data)
        assert profile.phases == ["init", "execute", "cleanup"]
        assert profile.nondeterministic_allowed_phases == ["execute"]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="extra"):
            ModelExecutionProfile.model_validate(
                {"phases": ["init"], "unknown_field": "value"}
            )
