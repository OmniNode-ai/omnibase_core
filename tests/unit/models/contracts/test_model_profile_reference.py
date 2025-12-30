# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProfileReference."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference


class TestModelProfileReference:
    """Tests for ModelProfileReference model."""

    def test_valid_profile_reference(self) -> None:
        """Test creating a valid profile reference."""
        ref = ModelProfileReference(
            profile="compute_pure",
            version="1.0.0",
        )
        assert ref.profile == "compute_pure"
        assert ref.version == "1.0.0"

    def test_various_profile_names(self) -> None:
        """Test various valid profile name formats."""
        profiles = [
            "compute_pure",
            "effect_http",
            "orchestrator_safe",
            "reducer_fsm",
            "my_custom_profile",
        ]
        for profile in profiles:
            ref = ModelProfileReference(profile=profile, version="1.0.0")
            assert ref.profile == profile

    def test_various_version_formats(self) -> None:
        """Test various valid version formats."""
        versions = [
            "1.0.0",
            "2.1.3",
            "0.1.0-alpha",
            "^1.0",
            "~1.2.3",
            ">=1.0.0",
        ]
        for version in versions:
            ref = ModelProfileReference(profile="test", version=version)
            assert ref.version == version

    def test_profile_required(self) -> None:
        """Test that profile is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProfileReference(version="1.0.0")  # type: ignore[call-arg]
        assert "profile" in str(exc_info.value)

    def test_version_required(self) -> None:
        """Test that version is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProfileReference(profile="test")  # type: ignore[call-arg]
        assert "version" in str(exc_info.value)

    def test_empty_profile_rejected(self) -> None:
        """Test that empty profile is rejected."""
        with pytest.raises(ValidationError):
            ModelProfileReference(profile="", version="1.0.0")

    def test_empty_version_rejected(self) -> None:
        """Test that empty version is rejected."""
        with pytest.raises(ValidationError):
            ModelProfileReference(profile="test", version="")

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProfileReference(
                profile="test",
                version="1.0.0",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc_info.value).lower()

    def test_frozen_model(self) -> None:
        """Test that the model is immutable (frozen=True)."""
        ref = ModelProfileReference(profile="test", version="1.0.0")
        with pytest.raises(ValidationError):
            ref.profile = "changed"  # type: ignore[misc]

    def test_repr(self) -> None:
        """Test string representation."""
        ref = ModelProfileReference(profile="compute_pure", version="1.0.0")
        repr_str = repr(ref)
        assert "compute_pure" in repr_str
        assert "1.0.0" in repr_str

    def test_equality(self) -> None:
        """Test equality comparison."""
        ref1 = ModelProfileReference(profile="test", version="1.0.0")
        ref2 = ModelProfileReference(profile="test", version="1.0.0")
        ref3 = ModelProfileReference(profile="test", version="2.0.0")
        assert ref1 == ref2
        assert ref1 != ref3

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {"profile": "compute_pure", "version": "1.0.0"}
        ref = ModelProfileReference.model_validate(data)
        assert ref.profile == "compute_pure"
        assert ref.version == "1.0.0"

    def test_to_dict(self) -> None:
        """Test serializing to dictionary."""
        ref = ModelProfileReference(profile="test", version="1.0.0")
        data = ref.model_dump()
        assert data == {"profile": "test", "version": "1.0.0"}
