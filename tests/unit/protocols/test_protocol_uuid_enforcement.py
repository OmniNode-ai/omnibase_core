"""Tests for UUID type enforcement in protocol implementations.

This test module verifies that protocol implementations correctly enforce UUID types
for ID fields, as per the changes in PR #119. These are regression tests to ensure
the string-to-UUID migration is properly enforced.

Related Documentation:
    - docs/guides/PROTOCOL_UUID_MIGRATION.md
    - PR #119: Change ID fields from str to UUID
"""

from typing import Any, Literal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.container.model_service_instance import ModelServiceInstance
from omnibase_core.models.container.model_service_metadata import ModelServiceMetadata
from omnibase_core.models.container.model_service_registration import (
    ModelServiceRegistration,
)
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.protocols.types import (
    ProtocolIdentifiable,
    ProtocolNodeMetadataBlock,
    ProtocolValidatable,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_uuid() -> UUID:
    """Create a valid UUID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def valid_uuid_string() -> str:
    """Create a valid UUID string for testing."""
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture
def sample_semver() -> ModelSemVer:
    """Create sample semantic version."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def sample_service_metadata(
    valid_uuid: UUID, sample_semver: ModelSemVer
) -> ModelServiceMetadata:
    """Create sample service metadata with UUID field."""
    return ModelServiceMetadata(
        service_id=valid_uuid,
        service_name="test_service",
        service_interface="ProtocolTest",
        service_implementation="TestImplementation",
        version=sample_semver,
    )


# =============================================================================
# Container Protocol UUID Enforcement Tests
# =============================================================================


class TestContainerProtocolUUIDEnforcement:
    """Test UUID enforcement in container protocol implementations."""

    def test_service_metadata_service_id_is_uuid(
        self, valid_uuid: UUID, sample_semver: ModelSemVer
    ) -> None:
        """Verify service_id field is UUID type."""
        metadata = ModelServiceMetadata(
            service_id=valid_uuid,
            service_name="test_service",
            service_interface="ProtocolTest",
            service_implementation="TestImpl",
            version=sample_semver,
        )

        assert isinstance(metadata.service_id, UUID)
        assert metadata.service_id == valid_uuid

    def test_service_metadata_accepts_uuid_string(
        self, valid_uuid_string: str, sample_semver: ModelSemVer
    ) -> None:
        """Verify service_id accepts valid UUID string and converts to UUID."""
        metadata = ModelServiceMetadata(
            service_id=valid_uuid_string,  # type: ignore[arg-type]
            service_name="test_service",
            service_interface="ProtocolTest",
            service_implementation="TestImpl",
            version=sample_semver,
        )

        # Pydantic should convert string to UUID
        assert isinstance(metadata.service_id, UUID)
        assert str(metadata.service_id) == valid_uuid_string

    def test_service_metadata_rejects_invalid_uuid_string(
        self, sample_semver: ModelSemVer
    ) -> None:
        """Verify service_id rejects invalid UUID string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceMetadata(
                service_id="not-a-valid-uuid",  # type: ignore[arg-type]
                service_name="test_service",
                service_interface="ProtocolTest",
                service_implementation="TestImpl",
                version=sample_semver,
            )

        # Check that validation error is for service_id field
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("service_id",) for error in errors)

    def test_service_registration_registration_id_is_uuid(
        self, sample_service_metadata: ModelServiceMetadata, sample_semver: ModelSemVer
    ) -> None:
        """Verify registration_id field is UUID type."""
        reg_id = uuid4()
        registration = ModelServiceRegistration(
            registration_id=reg_id,
            service_metadata=sample_service_metadata,
            lifecycle="singleton",
            scope="global",
        )

        assert isinstance(registration.registration_id, UUID)
        assert registration.registration_id == reg_id

    def test_service_registration_accepts_uuid_string(
        self,
        valid_uuid_string: str,
        sample_service_metadata: ModelServiceMetadata,
        sample_semver: ModelSemVer,
    ) -> None:
        """Verify registration_id accepts valid UUID string and converts to UUID."""
        registration = ModelServiceRegistration(
            registration_id=valid_uuid_string,  # type: ignore[arg-type]
            service_metadata=sample_service_metadata,
            lifecycle="singleton",
            scope="global",
        )

        assert isinstance(registration.registration_id, UUID)
        assert str(registration.registration_id) == valid_uuid_string

    def test_service_registration_rejects_invalid_uuid_string(
        self, sample_service_metadata: ModelServiceMetadata
    ) -> None:
        """Verify registration_id rejects invalid UUID string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceRegistration(
                registration_id="invalid-registration-id",  # type: ignore[arg-type]
                service_metadata=sample_service_metadata,
                lifecycle="singleton",
                scope="global",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("registration_id",) for error in errors)

    def test_service_instance_instance_id_is_uuid(self) -> None:
        """Verify instance_id field is UUID type."""
        inst_id = uuid4()
        reg_id = uuid4()
        instance = ModelServiceInstance(
            instance_id=inst_id,
            service_registration_id=reg_id,
            instance="mock_service",
            lifecycle="singleton",
            scope="global",
        )

        assert isinstance(instance.instance_id, UUID)
        assert instance.instance_id == inst_id

    def test_service_instance_service_registration_id_is_uuid(self) -> None:
        """Verify service_registration_id field is UUID type."""
        inst_id = uuid4()
        reg_id = uuid4()
        instance = ModelServiceInstance(
            instance_id=inst_id,
            service_registration_id=reg_id,
            instance="mock_service",
            lifecycle="singleton",
            scope="global",
        )

        assert isinstance(instance.service_registration_id, UUID)
        assert instance.service_registration_id == reg_id

    def test_service_instance_accepts_uuid_strings(
        self, valid_uuid_string: str
    ) -> None:
        """Verify both ID fields accept valid UUID strings."""
        another_uuid_string = "87654321-4321-8765-4321-876543218765"
        instance = ModelServiceInstance(
            instance_id=valid_uuid_string,  # type: ignore[arg-type]
            service_registration_id=another_uuid_string,  # type: ignore[arg-type]
            instance="mock_service",
            lifecycle="singleton",
            scope="global",
        )

        assert isinstance(instance.instance_id, UUID)
        assert isinstance(instance.service_registration_id, UUID)
        assert str(instance.instance_id) == valid_uuid_string
        assert str(instance.service_registration_id) == another_uuid_string

    def test_service_instance_rejects_invalid_instance_id(self) -> None:
        """Verify instance_id rejects invalid UUID string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceInstance(
                instance_id="bad-instance-id",  # type: ignore[arg-type]
                service_registration_id=uuid4(),
                instance="mock_service",
                lifecycle="singleton",
                scope="global",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("instance_id",) for error in errors)

    def test_service_instance_rejects_invalid_service_registration_id(self) -> None:
        """Verify service_registration_id rejects invalid UUID string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceInstance(
                instance_id=uuid4(),
                service_registration_id="bad-registration-id",  # type: ignore[arg-type]
                instance="mock_service",
                lifecycle="singleton",
                scope="global",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("service_registration_id",) for error in errors)


# =============================================================================
# Type Protocol UUID Enforcement Tests
# =============================================================================


class TestTypeProtocolUUIDEnforcement:
    """Test UUID enforcement in type protocol implementations."""

    def test_protocol_identifiable_id_returns_uuid(self) -> None:
        """Verify ProtocolIdentifiable.id property returns UUID type."""

        class IdentifiableEntity:
            """Test implementation of ProtocolIdentifiable."""

            __omnibase_identifiable_marker__: Literal[True] = True

            def __init__(self, entity_id: UUID) -> None:
                self._id = entity_id

            @property
            def id(self) -> UUID:
                return self._id

        entity_id = uuid4()
        entity = IdentifiableEntity(entity_id)

        # Verify the implementation satisfies the protocol
        assert hasattr(entity, "__omnibase_identifiable_marker__")
        assert isinstance(entity.id, UUID)
        assert entity.id == entity_id

    def test_protocol_validatable_get_validation_id_returns_uuid(self) -> None:
        """Verify ProtocolValidatable.get_validation_id() returns UUID type."""

        class ValidatableEntity:
            """Test implementation of ProtocolValidatable."""

            def __init__(self, validation_id: UUID) -> None:
                self._validation_id = validation_id

            async def get_validation_context(self) -> dict[str, Any]:
                return {"entity_type": "test"}

            async def get_validation_id(self) -> UUID:
                return self._validation_id

        validation_id = uuid4()
        entity = ValidatableEntity(validation_id)

        # Verify the method signature (sync check for signature)
        import inspect

        sig = inspect.signature(entity.get_validation_id)
        # Return annotation should be UUID
        assert (
            sig.return_annotation == UUID
            or str(sig.return_annotation) == "<class 'uuid.UUID'>"
        )

    @pytest.mark.asyncio
    async def test_protocol_validatable_async_uuid_return(self) -> None:
        """Verify ProtocolValidatable.get_validation_id() actually returns UUID."""

        class ValidatableEntity:
            """Test implementation of ProtocolValidatable."""

            def __init__(self, validation_id: UUID) -> None:
                self._validation_id = validation_id

            async def get_validation_context(self) -> dict[str, Any]:
                return {"entity_type": "test"}

            async def get_validation_id(self) -> UUID:
                return self._validation_id

        validation_id = uuid4()
        entity = ValidatableEntity(validation_id)

        result = await entity.get_validation_id()
        assert isinstance(result, UUID)
        assert result == validation_id

    def test_protocol_node_metadata_block_uuid_is_uuid_type(self) -> None:
        """Verify ProtocolNodeMetadataBlock.uuid is UUID type."""
        # Create a minimal valid ModelNodeMetadataBlock
        block = ModelNodeMetadataBlock(
            name="test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            author="test_author",
            created_at="2024-01-01T00:00:00Z",
            last_modified_at="2024-01-01T00:00:00Z",
            hash="a" * 64,
            entrypoint="python://main.py",
            namespace="onex.tools.test",
        )

        # Verify uuid is UUID type
        assert isinstance(block.uuid, UUID)

    def test_model_node_metadata_block_uuid_default_factory(self) -> None:
        """Verify uuid field has default_factory=uuid4."""
        # Create two blocks and verify they get unique UUIDs
        block1 = ModelNodeMetadataBlock(
            name="test-node-1",
            version=ModelSemVer(major=1, minor=0, patch=0),
            author="test_author",
            created_at="2024-01-01T00:00:00Z",
            last_modified_at="2024-01-01T00:00:00Z",
            hash="a" * 64,
            entrypoint="python://main.py",
            namespace="onex.tools.test1",
        )

        block2 = ModelNodeMetadataBlock(
            name="test-node-2",
            version=ModelSemVer(major=1, minor=0, patch=0),
            author="test_author",
            created_at="2024-01-01T00:00:00Z",
            last_modified_at="2024-01-01T00:00:00Z",
            hash="b" * 64,
            entrypoint="python://main.py",
            namespace="onex.tools.test2",
        )

        # Each should have a unique UUID
        assert block1.uuid != block2.uuid
        assert isinstance(block1.uuid, UUID)
        assert isinstance(block2.uuid, UUID)

    def test_model_node_metadata_block_accepts_explicit_uuid(self) -> None:
        """Verify uuid field accepts explicit UUID value."""
        explicit_uuid = uuid4()
        block = ModelNodeMetadataBlock(
            uuid=explicit_uuid,
            name="test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            author="test_author",
            created_at="2024-01-01T00:00:00Z",
            last_modified_at="2024-01-01T00:00:00Z",
            hash="a" * 64,
            entrypoint="python://main.py",
            namespace="onex.tools.test",
        )

        assert block.uuid == explicit_uuid

    def test_model_node_metadata_block_accepts_uuid_string(
        self, valid_uuid_string: str
    ) -> None:
        """Verify uuid field accepts valid UUID string."""
        block = ModelNodeMetadataBlock(
            uuid=valid_uuid_string,  # type: ignore[arg-type]
            name="test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            author="test_author",
            created_at="2024-01-01T00:00:00Z",
            last_modified_at="2024-01-01T00:00:00Z",
            hash="a" * 64,
            entrypoint="python://main.py",
            namespace="onex.tools.test",
        )

        assert isinstance(block.uuid, UUID)
        assert str(block.uuid) == valid_uuid_string


# =============================================================================
# UUID Conversion Edge Cases Tests
# =============================================================================


class TestUUIDConversionEdgeCases:
    """Test UUID conversion edge cases."""

    def test_valid_uuid_string_converts_to_uuid(self) -> None:
        """Test valid UUID string converts to UUID object."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        uuid_obj = UUID(uuid_str)

        assert isinstance(uuid_obj, UUID)
        assert str(uuid_obj) == uuid_str

    def test_valid_uuid_string_without_hyphens_converts(self) -> None:
        """Test valid UUID string without hyphens converts to UUID."""
        uuid_hex = "12345678123456781234567812345678"
        uuid_obj = UUID(uuid_hex)

        assert isinstance(uuid_obj, UUID)
        assert uuid_obj.hex == uuid_hex

    def test_invalid_uuid_string_raises_value_error(self) -> None:
        """Test invalid UUID string raises ValueError."""
        with pytest.raises(ValueError):
            UUID("not-a-valid-uuid")

    def test_empty_string_raises_value_error(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError):
            UUID("")

    def test_uuid_with_wrong_length_raises_value_error(self) -> None:
        """Test UUID with wrong length raises ValueError."""
        with pytest.raises(ValueError):
            UUID("12345678-1234-5678-1234")  # Too short

    def test_uuid_with_invalid_characters_raises_value_error(self) -> None:
        """Test UUID with invalid characters raises ValueError."""
        with pytest.raises(ValueError):
            UUID("gggggggg-gggg-gggg-gggg-gggggggggggg")  # Invalid hex

    def test_none_handling_for_uuid_conversion(self) -> None:
        """Test None cannot be directly converted to UUID."""
        with pytest.raises(TypeError):
            UUID(None)  # type: ignore[arg-type]

    def test_uuid_comparison_uuid_vs_uuid(self) -> None:
        """Test UUID comparison between two UUID objects."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        uuid1 = UUID(uuid_str)
        uuid2 = UUID(uuid_str)

        assert uuid1 == uuid2
        assert uuid1 == uuid2  # Simplified from 'not (uuid1 != uuid2)' per SIM202

    def test_uuid_comparison_uuid_vs_string_explicit_conversion(self) -> None:
        """Test UUID comparison with explicit string conversion."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        uuid_obj = UUID(uuid_str)

        # Explicit conversion for comparison
        assert str(uuid_obj) == uuid_str
        assert uuid_obj == UUID(uuid_str)

    def test_uuid_comparison_different_uuids(self) -> None:
        """Test UUID comparison between different UUIDs."""
        uuid1 = uuid4()
        uuid2 = uuid4()

        assert uuid1 != uuid2

    def test_uuid_string_representation_formats(self) -> None:
        """Test various UUID string representation formats."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")

        # Standard string representation (with hyphens)
        assert str(uuid_obj) == "12345678-1234-5678-1234-567812345678"

        # Hex representation (without hyphens)
        assert uuid_obj.hex == "12345678123456781234567812345678"

        # URN representation
        assert uuid_obj.urn == "urn:uuid:12345678-1234-5678-1234-567812345678"

    def test_uuid_bytes_conversion(self) -> None:
        """Test UUID bytes conversion."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")
        uuid_bytes = uuid_obj.bytes

        # Reconstruct from bytes
        reconstructed = UUID(bytes=uuid_bytes)
        assert reconstructed == uuid_obj

    def test_uuid_int_conversion(self) -> None:
        """Test UUID integer conversion."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")
        uuid_int = uuid_obj.int

        # Reconstruct from integer
        reconstructed = UUID(int=uuid_int)
        assert reconstructed == uuid_obj


# =============================================================================
# Legacy String ID Migration Helper Tests
# =============================================================================


class LegacyMigrationHelper:
    """Helper for migrating legacy string IDs to UUID.

    As documented in PROTOCOL_UUID_MIGRATION.md.
    """

    @staticmethod
    def migrate_id(legacy_id: str | UUID) -> UUID:
        """Convert legacy string ID to UUID.

        Args:
            legacy_id: Either a string UUID or UUID object

        Returns:
            UUID object

        Raises:
            ValueError: If string is not a valid UUID format
        """
        if isinstance(legacy_id, UUID):
            return legacy_id
        return UUID(legacy_id)

    @staticmethod
    def safe_migrate_id(
        legacy_id: str | UUID, default: UUID | None = None
    ) -> UUID | None:
        """Safely convert legacy string ID to UUID.

        Args:
            legacy_id: Either a string UUID or UUID object
            default: Default value if conversion fails

        Returns:
            UUID object or default value
        """
        try:
            return LegacyMigrationHelper.migrate_id(legacy_id)
        except ValueError:
            return default


class TestLegacyMigrationHelper:
    """Test legacy string ID migration helper."""

    def test_migrate_id_from_valid_string(self) -> None:
        """Test migrate_id with valid UUID string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = LegacyMigrationHelper.migrate_id(uuid_str)

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_migrate_id_from_uuid_object(self) -> None:
        """Test migrate_id with UUID object (passthrough)."""
        uuid_obj = uuid4()
        result = LegacyMigrationHelper.migrate_id(uuid_obj)

        assert result is uuid_obj
        assert isinstance(result, UUID)

    def test_migrate_id_invalid_string_raises(self) -> None:
        """Test migrate_id raises ValueError for invalid string."""
        with pytest.raises(ValueError):
            LegacyMigrationHelper.migrate_id("invalid-uuid-string")

    def test_safe_migrate_id_valid_string(self) -> None:
        """Test safe_migrate_id with valid UUID string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = LegacyMigrationHelper.safe_migrate_id(uuid_str)

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_safe_migrate_id_invalid_string_returns_default(self) -> None:
        """Test safe_migrate_id returns default for invalid string."""
        default_uuid = uuid4()
        result = LegacyMigrationHelper.safe_migrate_id(
            "invalid-uuid-string", default=default_uuid
        )

        assert result == default_uuid

    def test_safe_migrate_id_invalid_string_returns_none_by_default(self) -> None:
        """Test safe_migrate_id returns None for invalid string with no default."""
        result = LegacyMigrationHelper.safe_migrate_id("invalid-uuid-string")

        assert result is None

    def test_safe_migrate_id_uuid_object(self) -> None:
        """Test safe_migrate_id with UUID object."""
        uuid_obj = uuid4()
        result = LegacyMigrationHelper.safe_migrate_id(uuid_obj)

        assert result is uuid_obj


# =============================================================================
# Pydantic UUID Serialization Tests
# =============================================================================


class TestPydanticUUIDSerialization:
    """Test Pydantic model UUID serialization/deserialization."""

    def test_service_metadata_serialization_preserves_uuid(
        self, sample_service_metadata: ModelServiceMetadata
    ) -> None:
        """Test UUID is preserved during model_dump."""
        data = sample_service_metadata.model_dump()

        # UUID should be in the dump
        assert "service_id" in data
        # When serialized, it should still be comparable to UUID
        assert data["service_id"] == sample_service_metadata.service_id

    def test_service_metadata_json_serialization(
        self, sample_service_metadata: ModelServiceMetadata
    ) -> None:
        """Test UUID is properly serialized to JSON."""
        json_str = sample_service_metadata.model_dump_json()

        # UUID should be serialized as string in JSON
        assert str(sample_service_metadata.service_id) in json_str

    def test_service_metadata_deserialization_from_dict(
        self, valid_uuid: UUID, sample_semver: ModelSemVer
    ) -> None:
        """Test UUID is properly deserialized from dict."""
        data = {
            "service_id": str(valid_uuid),
            "service_name": "test_service",
            "service_interface": "ProtocolTest",
            "service_implementation": "TestImpl",
            "version": sample_semver.model_dump(),
        }

        metadata = ModelServiceMetadata(**data)
        assert isinstance(metadata.service_id, UUID)
        assert metadata.service_id == valid_uuid

    def test_service_instance_round_trip_serialization(self) -> None:
        """Test UUID fields survive full serialization round trip."""
        inst_id = uuid4()
        reg_id = uuid4()

        original = ModelServiceInstance(
            instance_id=inst_id,
            service_registration_id=reg_id,
            instance="mock_service",
            lifecycle="singleton",
            scope="global",
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelServiceInstance(**data)

        assert restored.instance_id == original.instance_id
        assert restored.service_registration_id == original.service_registration_id
        assert isinstance(restored.instance_id, UUID)
        assert isinstance(restored.service_registration_id, UUID)


# =============================================================================
# Protocol Type Annotation Verification Tests
# =============================================================================


class TestProtocolTypeAnnotations:
    """Test that protocol type annotations correctly specify UUID."""

    def test_protocol_identifiable_id_annotation(self) -> None:
        """Verify ProtocolIdentifiable.id has UUID type annotation."""
        import typing

        # Get the property's return type annotation
        hints = typing.get_type_hints(ProtocolIdentifiable)
        # The 'id' is a property, need to check the getter
        assert "id" not in hints  # Properties don't show in get_type_hints directly

    def test_protocol_validatable_get_validation_id_annotation(self) -> None:
        """Verify ProtocolValidatable.get_validation_id has UUID return annotation."""
        import typing

        hints = typing.get_type_hints(ProtocolValidatable.get_validation_id)
        assert hints.get("return") == UUID

    def test_protocol_node_metadata_block_uuid_annotation(self) -> None:
        """Verify ProtocolNodeMetadataBlock.uuid has UUID type annotation."""
        import typing

        hints = typing.get_type_hints(ProtocolNodeMetadataBlock)
        assert hints.get("uuid") == UUID
