# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelSecurityMetadataRef."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.handlers.model_security_metadata_ref import (
    ModelSecurityMetadataRef,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelSecurityMetadataRefInstantiation:
    """Tests for ModelSecurityMetadataRef instantiation."""

    def test_basic_instantiation_with_ref(self) -> None:
        """Test creating security metadata ref with required ref field."""
        ref = ModelSecurityMetadataRef(ref="security://handlers/api-gateway")
        assert ref.ref == "security://handlers/api-gateway"
        assert ref.digest is None
        assert ref.version is None
        assert ref.source is None

    def test_instantiation_with_digest(self) -> None:
        """Test creating security metadata ref with optional digest."""
        ref = ModelSecurityMetadataRef(
            ref="security://handlers/api-gateway",
            digest="sha256:abc123def456",
        )
        assert ref.ref == "security://handlers/api-gateway"
        assert ref.digest == "sha256:abc123def456"

    def test_instantiation_with_version(self) -> None:
        """Test creating security metadata ref with optional version."""
        version = ModelSemVer(major=1, minor=2, patch=0)
        ref = ModelSecurityMetadataRef(
            ref="security://handlers/api-gateway",
            version=version,
        )
        assert ref.ref == "security://handlers/api-gateway"
        assert ref.version == version

    def test_instantiation_with_source(self) -> None:
        """Test creating security metadata ref with optional source."""
        ref = ModelSecurityMetadataRef(
            ref="security://handlers/api-gateway",
            source="vault://prod",
        )
        assert ref.ref == "security://handlers/api-gateway"
        assert ref.source == "vault://prod"

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating security metadata ref with all optional fields."""
        version = ModelSemVer(major=1, minor=2, patch=0)
        ref = ModelSecurityMetadataRef(
            ref="security://handlers/api-gateway",
            digest="sha256:abc123def456",
            version=version,
            source="vault://prod",
        )
        assert ref.ref == "security://handlers/api-gateway"
        assert ref.digest == "sha256:abc123def456"
        assert ref.version == version
        assert ref.source == "vault://prod"


@pytest.mark.unit
class TestModelSecurityMetadataRefOptionalFields:
    """Tests for ModelSecurityMetadataRef optional fields."""

    def test_optional_digest_default_none(self) -> None:
        """Test digest defaults to None."""
        ref = ModelSecurityMetadataRef(ref="security://test")
        assert ref.digest is None

    def test_optional_version_default_none(self) -> None:
        """Test version defaults to None."""
        ref = ModelSecurityMetadataRef(ref="security://test")
        assert ref.version is None

    def test_optional_source_default_none(self) -> None:
        """Test source defaults to None."""
        ref = ModelSecurityMetadataRef(ref="security://test")
        assert ref.source is None

    def test_all_optional_fields_can_be_explicitly_none(self) -> None:
        """Test all optional fields can be explicitly set to None."""
        ref = ModelSecurityMetadataRef(
            ref="security://test",
            digest=None,
            version=None,
            source=None,
        )
        assert ref.digest is None
        assert ref.version is None
        assert ref.source is None


@pytest.mark.unit
class TestModelSecurityMetadataRefImmutability:
    """Tests for ModelSecurityMetadataRef frozen immutability."""

    def test_frozen_immutability_ref(self) -> None:
        """Test that ref cannot be modified (frozen model)."""
        ref = ModelSecurityMetadataRef(ref="security://test")
        with pytest.raises(ValidationError, match="frozen"):
            ref.ref = "security://modified"  # type: ignore[misc]

    def test_frozen_immutability_digest(self) -> None:
        """Test that digest cannot be modified (frozen model)."""
        ref = ModelSecurityMetadataRef(ref="security://test", digest="sha256:abc")
        with pytest.raises(ValidationError, match="frozen"):
            ref.digest = "sha256:xyz"  # type: ignore[misc]

    def test_frozen_immutability_version(self) -> None:
        """Test that version cannot be modified (frozen model)."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        ref = ModelSecurityMetadataRef(ref="security://test", version=version)
        new_version = ModelSemVer(major=2, minor=0, patch=0)
        with pytest.raises(ValidationError, match="frozen"):
            ref.version = new_version  # type: ignore[misc]

    def test_frozen_immutability_source(self) -> None:
        """Test that source cannot be modified (frozen model)."""
        ref = ModelSecurityMetadataRef(ref="security://test", source="vault://prod")
        with pytest.raises(ValidationError, match="frozen"):
            ref.source = "vault://dev"  # type: ignore[misc]


@pytest.mark.unit
class TestModelSecurityMetadataRefExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelSecurityMetadataRef(
                ref="security://test",
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelSecurityMetadataRefValidation:
    """Tests for ModelSecurityMetadataRef validation."""

    def test_empty_ref_rejected(self) -> None:
        """Test that empty ref is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSecurityMetadataRef(ref="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_various_ref_formats_accepted(self) -> None:
        """Test that various ref formats are accepted (opaque identifier)."""
        # Security URI format
        ref1 = ModelSecurityMetadataRef(ref="security://handlers/api-gateway")
        assert ref1.ref == "security://handlers/api-gateway"

        # URN format
        ref2 = ModelSecurityMetadataRef(ref="urn:onex:security:policy-v1")
        assert ref2.ref == "urn:onex:security:policy-v1"

        # Vault path format
        ref3 = ModelSecurityMetadataRef(ref="vault://secrets/handlers/config")
        assert ref3.ref == "vault://secrets/handlers/config"

        # Simple slug format
        ref4 = ModelSecurityMetadataRef(ref="api-gateway-security-v1")
        assert ref4.ref == "api-gateway-security-v1"


@pytest.mark.unit
class TestModelSecurityMetadataRefSerialization:
    """Tests for ModelSecurityMetadataRef serialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal fields."""
        ref = ModelSecurityMetadataRef(ref="security://test")
        data = ref.model_dump()
        assert data["ref"] == "security://test"
        assert data["digest"] is None
        assert data["version"] is None
        assert data["source"] is None

    def test_model_dump_full(self) -> None:
        """Test model_dump with all fields."""
        version = ModelSemVer(major=2, minor=1, patch=0)
        ref = ModelSecurityMetadataRef(
            ref="security://test",
            digest="sha256:securityhash",
            version=version,
            source="consul://security-store",
        )
        data = ref.model_dump()
        assert data["ref"] == "security://test"
        assert data["digest"] == "sha256:securityhash"
        assert data["version"]["major"] == 2
        assert data["version"]["minor"] == 1
        assert data["version"]["patch"] == 0
        assert data["source"] == "consul://security-store"

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        original = ModelSecurityMetadataRef(
            ref="security://roundtrip",
            digest="sha256:roundtriphash",
            version=version,
            source="vault://test",
        )
        data = original.model_dump()
        restored = ModelSecurityMetadataRef(**data)

        assert restored.ref == original.ref
        assert restored.digest == original.digest
        assert restored.version == original.version
        assert restored.source == original.source


@pytest.mark.unit
class TestModelSecurityMetadataRefThreadSafety:
    """Tests for thread safety characteristics."""

    def test_immutable_after_creation(self) -> None:
        """Test that the model is immutable after creation (thread-safe)."""
        ref = ModelSecurityMetadataRef(
            ref="security://test",
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
