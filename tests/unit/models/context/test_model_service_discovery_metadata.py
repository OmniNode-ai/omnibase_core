# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelServiceDiscoveryMetadata.

Tests all ModelServiceDiscoveryMetadata functionality including:
- Basic instantiation with all fields
- Required field validation (service_name)
- Partial instantiation with optional fields
- Default value verification
- Field validation (protocol, health_check_url)
- Frozen behavior (immutability)
- Extra fields forbidden
- JSON serialization/deserialization
- from_attributes behavior
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelServiceDiscoveryMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Helper classes for from_attributes testing
# =============================================================================


@dataclass
class ServiceDiscoveryMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelServiceDiscoveryMetadata."""

    service_name: str = "default-service"
    service_version: ModelSemVer | None = None
    service_instance_id: UUID | None = None
    health_check_url: str | None = None
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    protocol: str = "grpc"


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataInstantiation:
    """Tests for ModelServiceDiscoveryMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating metadata with all fields populated."""
        instance_id = uuid4()
        version = ModelSemVer(major=2, minor=1, patch=0)
        metadata = ModelServiceDiscoveryMetadata(
            service_name="user-service",
            service_version=version,
            service_instance_id=instance_id,
            health_check_url="https://user-service:8080/health",
            capabilities=["create_user", "delete_user", "list_users"],
            dependencies=["auth-service", "database-service"],
            tags=["production", "us-west-2"],
            protocol="grpc",
        )

        assert metadata.service_name == "user-service"
        assert metadata.service_version == version
        assert metadata.service_instance_id == instance_id
        assert metadata.health_check_url == "https://user-service:8080/health"
        assert metadata.capabilities == ["create_user", "delete_user", "list_users"]
        assert metadata.dependencies == ["auth-service", "database-service"]
        assert metadata.tags == ["production", "us-west-2"]
        assert metadata.protocol == "grpc"

    def test_create_with_required_field_only(self) -> None:
        """Test creating metadata with only the required service_name field."""
        metadata = ModelServiceDiscoveryMetadata(service_name="minimal-service")

        assert metadata.service_name == "minimal-service"
        assert metadata.service_version is None
        assert metadata.service_instance_id is None
        assert metadata.health_check_url is None
        assert metadata.capabilities == []
        assert metadata.dependencies == []
        assert metadata.tags == []
        assert metadata.protocol == "grpc"  # default

    def test_create_with_partial_fields(self) -> None:
        """Test creating metadata with some fields."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        metadata = ModelServiceDiscoveryMetadata(
            service_name="partial-service",
            service_version=version,
            protocol="http",
        )

        assert metadata.service_name == "partial-service"
        assert metadata.service_version == version
        assert metadata.protocol == "http"
        assert metadata.capabilities == []


# =============================================================================
# Required Field Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataRequiredFields:
    """Tests for ModelServiceDiscoveryMetadata required fields."""

    def test_service_name_is_required(self) -> None:
        """Test that service_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceDiscoveryMetadata()  # type: ignore[call-arg]
        assert "service_name" in str(exc_info.value).lower()

    def test_service_name_minimum_length(self) -> None:
        """Test that service_name must have at least 1 character."""
        # Valid minimum
        metadata = ModelServiceDiscoveryMetadata(service_name="x")
        assert metadata.service_name == "x"

        # Invalid (empty string)
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceDiscoveryMetadata(service_name="")
        assert "service_name" in str(exc_info.value).lower()


# =============================================================================
# Default Value Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataDefaults:
    """Tests for ModelServiceDiscoveryMetadata default values."""

    def test_protocol_defaults_to_grpc(self) -> None:
        """Test that protocol defaults to 'grpc'."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test-service")
        assert metadata.protocol == "grpc"

    def test_list_fields_default_to_empty_list(self) -> None:
        """Test that list fields default to empty lists."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test-service")
        assert metadata.capabilities == []
        assert metadata.dependencies == []
        assert metadata.tags == []

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test-service")
        assert metadata.service_version is None
        assert metadata.service_instance_id is None
        assert metadata.health_check_url is None


# =============================================================================
# Field Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataValidation:
    """Tests for ModelServiceDiscoveryMetadata field validation."""

    def test_protocol_accepts_grpc(self) -> None:
        """Test that protocol accepts 'grpc'."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test", protocol="grpc")
        assert metadata.protocol == "grpc"

    def test_protocol_accepts_http(self) -> None:
        """Test that protocol accepts 'http'."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test", protocol="http")
        assert metadata.protocol == "http"

    def test_protocol_accepts_https(self) -> None:
        """Test that protocol accepts 'https'."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test", protocol="https")
        assert metadata.protocol == "https"

    def test_protocol_accepts_ws(self) -> None:
        """Test that protocol accepts 'ws'."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test", protocol="ws")
        assert metadata.protocol == "ws"

    def test_protocol_accepts_wss(self) -> None:
        """Test that protocol accepts 'wss'."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test", protocol="wss")
        assert metadata.protocol == "wss"

    def test_protocol_is_case_insensitive(self) -> None:
        """Test that protocol validation is case-insensitive."""
        metadata_upper = ModelServiceDiscoveryMetadata(
            service_name="test", protocol="GRPC"
        )
        assert metadata_upper.protocol == "grpc"

        metadata_mixed = ModelServiceDiscoveryMetadata(
            service_name="test", protocol="Http"
        )
        assert metadata_mixed.protocol == "http"

    def test_protocol_rejects_invalid_value(self) -> None:
        """Test that invalid protocol values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceDiscoveryMetadata(service_name="test", protocol="invalid")
        assert "protocol" in str(exc_info.value).lower()

    def test_protocol_rejects_empty_string(self) -> None:
        """Test that empty string protocol is rejected."""
        with pytest.raises(ValidationError):
            ModelServiceDiscoveryMetadata(service_name="test", protocol="")

    def test_health_check_url_accepts_valid_http_url(self) -> None:
        """Test that health_check_url accepts valid HTTP URL."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url="http://service:8080/health",
        )
        assert metadata.health_check_url == "http://service:8080/health"

    def test_health_check_url_accepts_valid_https_url(self) -> None:
        """Test that health_check_url accepts valid HTTPS URL."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url="https://service:8080/health",
        )
        assert metadata.health_check_url == "https://service:8080/health"

    def test_health_check_url_rejects_non_http_scheme(self) -> None:
        """Test that health_check_url rejects non-HTTP schemes."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceDiscoveryMetadata(
                service_name="test",
                health_check_url="ftp://service:8080/health",
            )
        assert "health_check_url" in str(exc_info.value).lower()

    def test_health_check_url_rejects_missing_host(self) -> None:
        """Test that health_check_url rejects URL without host."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceDiscoveryMetadata(
                service_name="test",
                health_check_url="http:///health",
            )
        assert "host" in str(exc_info.value).lower()

    def test_health_check_url_rejects_invalid_url(self) -> None:
        """Test that health_check_url rejects malformed URLs."""
        with pytest.raises(ValidationError):
            ModelServiceDiscoveryMetadata(
                service_name="test",
                health_check_url="not-a-valid-url",
            )

    def test_health_check_url_accepts_none(self) -> None:
        """Test that health_check_url accepts None."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url=None,
        )
        assert metadata.health_check_url is None

    def test_health_check_url_empty_string_becomes_none(self) -> None:
        """Test that empty string health_check_url becomes None."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url="",
        )
        assert metadata.health_check_url is None

    def test_health_check_url_whitespace_only_becomes_none(self) -> None:
        """Test that whitespace-only health_check_url becomes None."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url="   ",
        )
        assert metadata.health_check_url is None

    def test_service_instance_id_accepts_valid_uuid(self) -> None:
        """Test that service_instance_id accepts valid UUID."""
        instance_id = uuid4()
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            service_instance_id=instance_id,
        )
        assert metadata.service_instance_id == instance_id

    def test_service_instance_id_accepts_uuid_string(self) -> None:
        """Test that service_instance_id accepts UUID as string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            service_instance_id=uuid_str,  # type: ignore[arg-type]
        )
        assert metadata.service_instance_id == UUID(uuid_str)


# =============================================================================
# Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataImmutability:
    """Tests for ModelServiceDiscoveryMetadata immutability (frozen=True)."""

    def test_cannot_modify_service_name(self) -> None:
        """Test that service_name cannot be modified after creation."""
        metadata = ModelServiceDiscoveryMetadata(service_name="original")
        with pytest.raises(ValidationError):
            metadata.service_name = "modified"  # type: ignore[misc]

    def test_cannot_modify_protocol(self) -> None:
        """Test that protocol cannot be modified after creation."""
        metadata = ModelServiceDiscoveryMetadata(service_name="test", protocol="grpc")
        with pytest.raises(ValidationError):
            metadata.protocol = "http"  # type: ignore[misc]

    def test_cannot_modify_capabilities(self) -> None:
        """Test that capabilities list cannot be reassigned."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            capabilities=["cap1"],
        )
        with pytest.raises(ValidationError):
            metadata.capabilities = ["cap2"]  # type: ignore[misc]

    def test_cannot_modify_health_check_url(self) -> None:
        """Test that health_check_url cannot be modified after creation."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url="http://test:8080/health",
        )
        with pytest.raises(ValidationError):
            metadata.health_check_url = "http://new:8080/health"  # type: ignore[misc]


# =============================================================================
# Extra Fields Forbidden Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataExtraForbid:
    """Tests for ModelServiceDiscoveryMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceDiscoveryMetadata(
                service_name="test",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# From Attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataFromAttributes:
    """Tests for ModelServiceDiscoveryMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelServiceDiscoveryMetadata from an object with attributes."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        attrs = ServiceDiscoveryMetadataAttrs(
            service_name="from-attrs-service",
            service_version=version,
            protocol="https",
        )
        metadata = ModelServiceDiscoveryMetadata.model_validate(attrs)
        assert metadata.service_name == "from-attrs-service"
        assert metadata.service_version == version
        assert metadata.protocol == "https"

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        instance_id = uuid4()
        version = ModelSemVer(major=2, minor=0, patch=0)
        attrs = ServiceDiscoveryMetadataAttrs(
            service_name="full-service",
            service_version=version,
            service_instance_id=instance_id,
            health_check_url="https://full:8080/health",
            capabilities=["read", "write"],
            dependencies=["dep1", "dep2"],
            tags=["tag1", "tag2"],
            protocol="http",
        )
        metadata = ModelServiceDiscoveryMetadata.model_validate(attrs)
        assert metadata.service_name == "full-service"
        assert metadata.service_instance_id == instance_id
        assert metadata.capabilities == ["read", "write"]
        assert metadata.protocol == "http"


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataSerialization:
    """Tests for ModelServiceDiscoveryMetadata serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump serialization."""
        instance_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        metadata = ModelServiceDiscoveryMetadata(
            service_name="serialize-service",
            service_version=version,
            service_instance_id=instance_id,
            capabilities=["cap1", "cap2"],
        )

        data = metadata.model_dump()
        assert data["service_name"] == "serialize-service"
        assert data["service_version"] == version.model_dump()
        assert data["service_instance_id"] == instance_id
        assert data["capabilities"] == ["cap1", "cap2"]

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="json-service",
            protocol="https",
            tags=["prod", "west"],
        )

        json_str = metadata.model_dump_json()
        assert isinstance(json_str, str)
        assert "json-service" in json_str
        assert "https" in json_str
        assert "prod" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        version = ModelSemVer(major=3, minor=0, patch=0)
        data = {
            "service_name": "dict-service",
            "service_version": version.model_dump(),
            "protocol": "grpc",
            "dependencies": ["other-service"],
        }

        metadata = ModelServiceDiscoveryMetadata.model_validate(data)
        assert metadata.service_name == "dict-service"
        assert metadata.service_version == version
        assert metadata.protocol == "grpc"
        assert metadata.dependencies == ["other-service"]

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        version = ModelSemVer(major=4, minor=0, patch=0)
        original = ModelServiceDiscoveryMetadata(
            service_name="roundtrip-service",
            service_version=version,
            service_instance_id=uuid4(),
            health_check_url="https://roundtrip:8080/health",
            capabilities=["a", "b", "c"],
            dependencies=["x", "y"],
            tags=["tag1", "tag2", "tag3"],
            protocol="wss",
        )

        json_str = original.model_dump_json()
        restored = ModelServiceDiscoveryMetadata.model_validate_json(json_str)

        assert restored == original


# =============================================================================
# Edge Cases and Additional Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataEdgeCases:
    """Tests for edge cases and additional scenarios."""

    def test_service_name_with_special_characters(self) -> None:
        """Test that service_name accepts various characters."""
        metadata = ModelServiceDiscoveryMetadata(service_name="my-service_v1.2.3")
        assert metadata.service_name == "my-service_v1.2.3"

    def test_empty_lists_are_valid(self) -> None:
        """Test that empty lists are valid for list fields."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            capabilities=[],
            dependencies=[],
            tags=[],
        )
        assert metadata.capabilities == []
        assert metadata.dependencies == []
        assert metadata.tags == []

    def test_large_capability_list(self) -> None:
        """Test that large capability lists are accepted."""
        capabilities = [f"capability_{i}" for i in range(100)]
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            capabilities=capabilities,
        )
        assert len(metadata.capabilities) == 100

    def test_health_check_url_with_path_and_port(self) -> None:
        """Test health_check_url with complex path and port."""
        url = "https://service.example.com:9443/api/v2/health/detailed"
        metadata = ModelServiceDiscoveryMetadata(
            service_name="test",
            health_check_url=url,
        )
        assert metadata.health_check_url == url

    def test_model_copy_with_update(self) -> None:
        """Test model_copy with update for creating modified copies."""
        original = ModelServiceDiscoveryMetadata(
            service_name="original-service",
            protocol="grpc",
        )

        new_version = ModelSemVer(major=2, minor=0, patch=0)
        modified = original.model_copy(
            update={"protocol": "https", "service_version": new_version}
        )

        assert modified.service_name == "original-service"
        assert modified.protocol == "https"
        assert modified.service_version == new_version
        assert original.protocol == "grpc"  # Original unchanged


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelServiceDiscoveryMetadataIntegration:
    """Integration tests for ModelServiceDiscoveryMetadata."""

    def test_model_config_is_correct(self) -> None:
        """Verify model configuration is correct."""
        config = ModelServiceDiscoveryMetadata.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_can_be_used_in_dict(self) -> None:
        """Test that metadata can be stored in dictionary."""
        metadata = ModelServiceDiscoveryMetadata(
            service_name="dict-service",
            protocol="http",
        )
        services = {"primary": metadata}
        assert services["primary"].service_name == "dict-service"
        assert services["primary"].protocol == "http"

    def test_valid_protocols_constant(self) -> None:
        """Test that all valid protocols from the constant work."""
        # Import the constant
        from omnibase_core.models.context.model_service_discovery_metadata import (
            VALID_PROTOCOLS,
        )

        for protocol in VALID_PROTOCOLS:
            metadata = ModelServiceDiscoveryMetadata(
                service_name="test",
                protocol=protocol,
            )
            assert metadata.protocol == protocol

    def test_equality_with_lists(self) -> None:
        """Test equality comparison with list fields."""
        meta1 = ModelServiceDiscoveryMetadata(
            service_name="test",
            capabilities=["a", "b"],
            tags=["t1"],
        )
        meta2 = ModelServiceDiscoveryMetadata(
            service_name="test",
            capabilities=["a", "b"],
            tags=["t1"],
        )
        meta3 = ModelServiceDiscoveryMetadata(
            service_name="test",
            capabilities=["a", "b", "c"],
            tags=["t1"],
        )

        assert meta1 == meta2
        assert meta1 != meta3
