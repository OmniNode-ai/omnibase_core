# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelArtifactRef."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.handlers.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelArtifactRefInstantiation:
    """Tests for ModelArtifactRef instantiation."""

    def test_basic_instantiation_with_ref(self) -> None:
        """Test creating artifact ref with required ref field."""
        ref = ModelArtifactRef(ref="artifact://schemas/user-profile")
        assert ref.ref == "artifact://schemas/user-profile"
        assert ref.digest is None
        assert ref.version is None
        assert ref.source is None

    def test_instantiation_with_digest(self) -> None:
        """Test creating artifact ref with optional digest."""
        ref = ModelArtifactRef(
            ref="artifact://myartifact",
            digest="sha256:a1b2c3d4e5f6",
        )
        assert ref.ref == "artifact://myartifact"
        assert ref.digest == "sha256:a1b2c3d4e5f6"

    def test_instantiation_with_version(self) -> None:
        """Test creating artifact ref with optional version."""
        version = ModelSemVer(major=1, minor=2, patch=0)
        ref = ModelArtifactRef(
            ref="artifact://myartifact",
            version=version,
        )
        assert ref.ref == "artifact://myartifact"
        assert ref.version == version

    def test_instantiation_with_source(self) -> None:
        """Test creating artifact ref with optional source."""
        ref = ModelArtifactRef(
            ref="artifact://myartifact",
            source="https://registry.omninode.ai/artifacts",
        )
        assert ref.ref == "artifact://myartifact"
        assert ref.source == "https://registry.omninode.ai/artifacts"

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating artifact ref with all optional fields."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        ref = ModelArtifactRef(
            ref="artifact://schemas/event-envelope",
            digest="sha256:e3b0c44298fc1c149afbf4c8996fb924",
            version=version,
            source="https://registry.example.com",
        )
        assert ref.ref == "artifact://schemas/event-envelope"
        assert ref.digest == "sha256:e3b0c44298fc1c149afbf4c8996fb924"
        assert ref.version == version
        assert ref.source == "https://registry.example.com"


@pytest.mark.unit
class TestModelArtifactRefOptionalFields:
    """Tests for ModelArtifactRef optional fields."""

    def test_optional_digest_default_none(self) -> None:
        """Test digest defaults to None."""
        ref = ModelArtifactRef(ref="artifact://test")
        assert ref.digest is None

    def test_optional_version_default_none(self) -> None:
        """Test version defaults to None."""
        ref = ModelArtifactRef(ref="artifact://test")
        assert ref.version is None

    def test_optional_source_default_none(self) -> None:
        """Test source defaults to None."""
        ref = ModelArtifactRef(ref="artifact://test")
        assert ref.source is None

    def test_version_can_be_explicitly_none(self) -> None:
        """Test version can be explicitly set to None."""
        ref = ModelArtifactRef(ref="artifact://test", version=None)
        assert ref.version is None


@pytest.mark.unit
class TestModelArtifactRefImmutability:
    """Tests for ModelArtifactRef frozen immutability."""

    def test_frozen_immutability_ref(self) -> None:
        """Test that ref cannot be modified (frozen model)."""
        ref = ModelArtifactRef(ref="artifact://test")
        with pytest.raises(ValidationError, match="frozen"):
            ref.ref = "artifact://modified"  # type: ignore[misc]

    def test_frozen_immutability_digest(self) -> None:
        """Test that digest cannot be modified (frozen model)."""
        ref = ModelArtifactRef(ref="artifact://test", digest="sha256:abc")
        with pytest.raises(ValidationError, match="frozen"):
            ref.digest = "sha256:xyz"  # type: ignore[misc]

    def test_frozen_immutability_version(self) -> None:
        """Test that version cannot be modified (frozen model)."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        ref = ModelArtifactRef(ref="artifact://test", version=version)
        new_version = ModelSemVer(major=2, minor=0, patch=0)
        with pytest.raises(ValidationError, match="frozen"):
            ref.version = new_version  # type: ignore[misc]

    def test_frozen_immutability_source(self) -> None:
        """Test that source cannot be modified (frozen model)."""
        ref = ModelArtifactRef(ref="artifact://test", source="https://example.com")
        with pytest.raises(ValidationError, match="frozen"):
            ref.source = "https://other.com"  # type: ignore[misc]


@pytest.mark.unit
class TestModelArtifactRefExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelArtifactRef(
                ref="artifact://test",
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelArtifactRefValidation:
    """Tests for ModelArtifactRef validation."""

    def test_empty_ref_rejected(self) -> None:
        """Test that empty ref is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelArtifactRef(ref="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_ref_accepted(self) -> None:
        """Test that whitespace-only ref is accepted (no strip validation)."""
        # The model only checks min_length, not content
        ref = ModelArtifactRef(ref=" ")
        assert ref.ref == " "

    def test_various_ref_formats_accepted(self) -> None:
        """Test that various ref formats are accepted (opaque identifier)."""
        # URI format
        ref1 = ModelArtifactRef(ref="artifact://path/to/resource")
        assert ref1.ref == "artifact://path/to/resource"

        # URN format
        ref2 = ModelArtifactRef(ref="urn:artifact:v1:abc123")
        assert ref2.ref == "urn:artifact:v1:abc123"

        # Path format
        ref3 = ModelArtifactRef(ref="/path/to/artifact.yaml")
        assert ref3.ref == "/path/to/artifact.yaml"

        # Custom slug format
        ref4 = ModelArtifactRef(ref="my-artifact-v1")
        assert ref4.ref == "my-artifact-v1"


@pytest.mark.unit
class TestModelArtifactRefSerialization:
    """Tests for ModelArtifactRef serialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal fields."""
        ref = ModelArtifactRef(ref="artifact://test")
        data = ref.model_dump()
        assert data["ref"] == "artifact://test"
        assert data["digest"] is None
        assert data["version"] is None
        assert data["source"] is None

    def test_model_dump_full(self) -> None:
        """Test model_dump with all fields."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        ref = ModelArtifactRef(
            ref="artifact://test",
            digest="sha256:abc123",
            version=version,
            source="https://registry.example.com",
        )
        data = ref.model_dump()
        assert data["ref"] == "artifact://test"
        assert data["digest"] == "sha256:abc123"
        assert data["version"]["major"] == 1
        assert data["version"]["minor"] == 2
        assert data["version"]["patch"] == 3
        assert data["source"] == "https://registry.example.com"

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        original = ModelArtifactRef(
            ref="artifact://roundtrip",
            digest="sha256:xyz789",
            version=version,
            source="https://source.example.com",
        )
        data = original.model_dump()
        restored = ModelArtifactRef(**data)

        assert restored.ref == original.ref
        assert restored.digest == original.digest
        assert restored.version == original.version
        assert restored.source == original.source
