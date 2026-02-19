# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPackagingMetadataRef."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.handlers.model_packaging_metadata_ref import (
    ModelPackagingMetadataRef,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelPackagingMetadataRefInstantiation:
    """Tests for ModelPackagingMetadataRef instantiation."""

    def test_basic_instantiation_with_ref(self) -> None:
        """Test creating packaging metadata ref with required ref field."""
        ref = ModelPackagingMetadataRef(ref="pkg:omnibase-core/node-validator")
        assert ref.ref == "pkg:omnibase-core/node-validator"
        assert ref.digest is None
        assert ref.version is None
        assert ref.source is None

    def test_instantiation_with_digest(self) -> None:
        """Test creating packaging metadata ref with optional digest."""
        ref = ModelPackagingMetadataRef(
            ref="pkg:omnibase-core/node-validator",
            digest="sha256:abc123...",
        )
        assert ref.ref == "pkg:omnibase-core/node-validator"
        assert ref.digest == "sha256:abc123..."

    def test_instantiation_with_version(self) -> None:
        """Test creating packaging metadata ref with optional version."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        ref = ModelPackagingMetadataRef(
            ref="pkg:omnibase-core/node-validator",
            version=version,
        )
        assert ref.ref == "pkg:omnibase-core/node-validator"
        assert ref.version == version

    def test_instantiation_with_source(self) -> None:
        """Test creating packaging metadata ref with optional source."""
        ref = ModelPackagingMetadataRef(
            ref="pkg:omnibase-core/node-validator",
            source="https://registry.omninode.ai/packages",
        )
        assert ref.ref == "pkg:omnibase-core/node-validator"
        assert ref.source == "https://registry.omninode.ai/packages"

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating packaging metadata ref with all optional fields."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        ref = ModelPackagingMetadataRef(
            ref="pkg:omnibase-core/node-validator",
            digest="sha256:abc123...",
            version=version,
            source="https://registry.omninode.ai/packages",
        )
        assert ref.ref == "pkg:omnibase-core/node-validator"
        assert ref.digest == "sha256:abc123..."
        assert ref.version == version
        assert ref.source == "https://registry.omninode.ai/packages"


@pytest.mark.unit
class TestModelPackagingMetadataRefOptionalFields:
    """Tests for ModelPackagingMetadataRef optional fields."""

    def test_optional_digest_default_none(self) -> None:
        """Test digest defaults to None."""
        ref = ModelPackagingMetadataRef(ref="pkg://test")
        assert ref.digest is None

    def test_optional_version_default_none(self) -> None:
        """Test version defaults to None."""
        ref = ModelPackagingMetadataRef(ref="pkg://test")
        assert ref.version is None

    def test_optional_source_default_none(self) -> None:
        """Test source defaults to None."""
        ref = ModelPackagingMetadataRef(ref="pkg://test")
        assert ref.source is None

    def test_all_optional_fields_can_be_explicitly_none(self) -> None:
        """Test all optional fields can be explicitly set to None."""
        ref = ModelPackagingMetadataRef(
            ref="pkg://test",
            digest=None,
            version=None,
            source=None,
        )
        assert ref.digest is None
        assert ref.version is None
        assert ref.source is None


@pytest.mark.unit
class TestModelPackagingMetadataRefImmutability:
    """Tests for ModelPackagingMetadataRef frozen immutability."""

    def test_frozen_immutability_ref(self) -> None:
        """Test that ref cannot be modified (frozen model)."""
        ref = ModelPackagingMetadataRef(ref="pkg://test")
        with pytest.raises(ValidationError, match="frozen"):
            ref.ref = "pkg://modified"  # type: ignore[misc]

    def test_frozen_immutability_digest(self) -> None:
        """Test that digest cannot be modified (frozen model)."""
        ref = ModelPackagingMetadataRef(ref="pkg://test", digest="sha256:abc")
        with pytest.raises(ValidationError, match="frozen"):
            ref.digest = "sha256:xyz"  # type: ignore[misc]

    def test_frozen_immutability_version(self) -> None:
        """Test that version cannot be modified (frozen model)."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        ref = ModelPackagingMetadataRef(ref="pkg://test", version=version)
        new_version = ModelSemVer(major=2, minor=0, patch=0)
        with pytest.raises(ValidationError, match="frozen"):
            ref.version = new_version  # type: ignore[misc]

    def test_frozen_immutability_source(self) -> None:
        """Test that source cannot be modified (frozen model)."""
        ref = ModelPackagingMetadataRef(
            ref="pkg://test", source="https://registry.example.com"
        )
        with pytest.raises(ValidationError, match="frozen"):
            ref.source = "https://other.example.com"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPackagingMetadataRefExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelPackagingMetadataRef(
                ref="pkg://test",
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelPackagingMetadataRefValidation:
    """Tests for ModelPackagingMetadataRef validation."""

    def test_empty_ref_rejected(self) -> None:
        """Test that empty ref is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPackagingMetadataRef(ref="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_various_ref_formats_accepted(self) -> None:
        """Test that various ref formats are accepted (opaque identifier)."""
        # Package URL format
        ref1 = ModelPackagingMetadataRef(ref="pkg:omnibase-core/node-validator")
        assert ref1.ref == "pkg:omnibase-core/node-validator"

        # Package URI format
        ref2 = ModelPackagingMetadataRef(ref="pkg://mypackage/handler-v1")
        assert ref2.ref == "pkg://mypackage/handler-v1"

        # Colon-separated format
        ref3 = ModelPackagingMetadataRef(ref="omnibase-core:node-validator:v1")
        assert ref3.ref == "omnibase-core:node-validator:v1"

        # Simple slug format
        ref4 = ModelPackagingMetadataRef(ref="node-validator-pkg")
        assert ref4.ref == "node-validator-pkg"

        # Python package format
        ref5 = ModelPackagingMetadataRef(ref="omnibase_core.handlers.validator")
        assert ref5.ref == "omnibase_core.handlers.validator"


@pytest.mark.unit
class TestModelPackagingMetadataRefSerialization:
    """Tests for ModelPackagingMetadataRef serialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal fields."""
        ref = ModelPackagingMetadataRef(ref="pkg://test")
        data = ref.model_dump()
        assert data["ref"] == "pkg://test"
        assert data["digest"] is None
        assert data["version"] is None
        assert data["source"] is None

    def test_model_dump_full(self) -> None:
        """Test model_dump with all fields."""
        version = ModelSemVer(major=3, minor=2, patch=1)
        ref = ModelPackagingMetadataRef(
            ref="pkg://test",
            digest="sha256:packaginghash",
            version=version,
            source="https://pypi.org/simple",
        )
        data = ref.model_dump()
        assert data["ref"] == "pkg://test"
        assert data["digest"] == "sha256:packaginghash"
        assert data["version"]["major"] == 3
        assert data["version"]["minor"] == 2
        assert data["version"]["patch"] == 1
        assert data["source"] == "https://pypi.org/simple"

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        original = ModelPackagingMetadataRef(
            ref="pkg://roundtrip",
            digest="sha256:roundtriphash",
            version=version,
            source="https://registry.example.com",
        )
        data = original.model_dump()
        restored = ModelPackagingMetadataRef(**data)

        assert restored.ref == original.ref
        assert restored.digest == original.digest
        assert restored.version == original.version
        assert restored.source == original.source


@pytest.mark.unit
class TestModelPackagingMetadataRefThreadSafety:
    """Tests for thread safety characteristics."""

    def test_immutable_after_creation(self) -> None:
        """Test that the model is immutable after creation (thread-safe)."""
        ref = ModelPackagingMetadataRef(
            ref="pkg://test",
            digest="sha256:abc",
        )
        # Verify all fields can be read
        _ = ref.ref
        _ = ref.digest
        _ = ref.version
        _ = ref.source

        # Verify mutations are rejected (making it thread-safe for reads)
        with pytest.raises(ValidationError):
            ref.ref = "modified"  # type: ignore[misc]
