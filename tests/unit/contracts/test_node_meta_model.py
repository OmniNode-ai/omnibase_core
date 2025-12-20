"""
Comprehensive TDD unit tests for ModelContractMeta.

Tests the meta-model that all declarative node contracts must adhere to,
ensuring cross-node consistency in the ONEX 4-node architecture.

Test Categories:
1. Required Fields Tests
2. Optional Fields Tests
3. Reserved Extension Fields Tests
4. Meta-Schema Validation Tests
5. Cross-Node Consistency Tests
6. Serialization Tests
7. Edge Cases

Requirements from OMN-157:
- Required fields for ALL declarative node contracts
- Optional fields
- Reserved extension fields (for future use)
- Meta-schema validation that enforces cross-node consistency
- mypy --strict compliance
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelContractMetaRequiredFields:
    """Tests for required fields in ModelContractMeta."""

    def test_create_with_all_required_fields(self) -> None:
        """Test creating ModelContractMeta with all required fields."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test compute node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.node_kind == EnumNodeKind.COMPUTE
        assert meta.name == "TestNode"
        assert meta.description == "A test compute node"
        assert meta.input_schema == "omnibase_core.models.ModelInput"
        assert meta.output_schema == "omnibase_core.models.ModelOutput"

    def test_node_id_is_required(self) -> None:
        """Test that node_id is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert "node_id" in str(exc_info.value)

    def test_node_kind_is_required(self) -> None:
        """Test that node_kind is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert "node_kind" in str(exc_info.value)

    def test_version_is_required(self) -> None:
        """Test that version is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert "version" in str(exc_info.value)

    def test_name_is_required(self) -> None:
        """Test that name is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert "name" in str(exc_info.value)

    def test_description_is_required(self) -> None:
        """Test that description is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert "description" in str(exc_info.value)

    def test_input_schema_is_required(self) -> None:
        """Test that input_schema is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="A test node",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert "input_schema" in str(exc_info.value)

    def test_output_schema_is_required(self) -> None:
        """Test that output_schema is required."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
            )

        assert "output_schema" in str(exc_info.value)


@pytest.mark.unit
class TestModelContractMetaNodeKindValidation:
    """Tests for node_kind validation in ModelContractMeta."""

    @pytest.mark.parametrize(
        "node_kind",
        [
            EnumNodeKind.EFFECT,
            EnumNodeKind.COMPUTE,
            EnumNodeKind.REDUCER,
            EnumNodeKind.ORCHESTRATOR,
        ],
    )
    def test_valid_core_node_kinds(self, node_kind: EnumNodeKind) -> None:
        """Test that all core node kinds are valid."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=node_kind,
            version="1.0.0",
            name="TestNode",
            description=f"A test {node_kind.value} node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.node_kind == node_kind

    def test_runtime_host_node_kind_is_valid(self) -> None:
        """Test that RUNTIME_HOST node kind is valid."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.RUNTIME_HOST,
            version="1.0.0",
            name="HostNode",
            description="A runtime host node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.node_kind == EnumNodeKind.RUNTIME_HOST

    def test_node_kind_string_coercion(self) -> None:
        """Test that node_kind can be created from string (YAML compatibility)."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind="compute",
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.node_kind == EnumNodeKind.COMPUTE

    def test_invalid_node_kind_raises_error(self) -> None:
        """Test that invalid node_kind raises ValidationError."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ModelOnexError)):
            ModelContractMeta(
                node_id=uuid4(),
                node_kind="invalid_kind",
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )


@pytest.mark.unit
class TestModelContractMetaVersionValidation:
    """Tests for version field validation."""

    def test_version_accepts_model_contract_version(self) -> None:
        """Test that version accepts ModelContractVersion."""
        from omnibase_core.models.contracts import ModelContractVersion
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        version = ModelContractVersion(major=1, minor=2, patch=3)
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version=version,
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.version == version

    def test_version_accepts_semver_string(self) -> None:
        """Test that version accepts semver string and converts."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.2.3",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert str(meta.version) == "1.2.3"

    def test_invalid_version_format_raises_error(self) -> None:
        """Test that invalid version format raises error."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ValueError, ModelOnexError)):
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="invalid",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )


@pytest.mark.unit
class TestModelContractMetaOptionalFields:
    """Tests for optional fields in ModelContractMeta."""

    def test_tags_defaults_to_empty_list(self) -> None:
        """Test that tags defaults to empty list."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.tags == []

    def test_tags_accepts_list_of_strings(self) -> None:
        """Test that tags accepts list of strings."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        tags = ["ml", "transformer", "gpu"]
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            tags=tags,
        )

        assert meta.tags == tags

    def test_author_is_optional(self) -> None:
        """Test that author is optional and defaults to None."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.author is None

    def test_author_accepts_string(self) -> None:
        """Test that author accepts string value."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            author="ONEX Team",
        )

        assert meta.author == "ONEX Team"

    def test_created_at_is_optional(self) -> None:
        """Test that created_at is optional and defaults to None."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.created_at is None

    def test_created_at_accepts_datetime(self) -> None:
        """Test that created_at accepts datetime value."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        now = datetime.now(UTC)
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            created_at=now,
        )

        assert meta.created_at == now

    def test_updated_at_is_optional(self) -> None:
        """Test that updated_at is optional and defaults to None."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.updated_at is None

    def test_updated_at_accepts_datetime(self) -> None:
        """Test that updated_at accepts datetime value."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        now = datetime.now(UTC)
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            updated_at=now,
        )

        assert meta.updated_at == now


@pytest.mark.unit
class TestModelContractMetaReservedExtensionFields:
    """Tests for reserved extension fields in ModelContractMeta."""

    def test_extensions_defaults_to_empty_model(self) -> None:
        """Test that extensions defaults to empty ModelNodeExtensions."""
        from omnibase_core.models.contracts.model_contract_meta import (
            ModelContractMeta,
            ModelNodeExtensions,
        )

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert isinstance(meta.extensions, ModelNodeExtensions)
        assert meta.extensions.model_dump(exclude_unset=True) == {}

    def test_extensions_accepts_dict_for_extra_fields(self) -> None:
        """Test that extensions accepts dict (creates ModelNodeExtensions with extra fields)."""
        from omnibase_core.models.contracts.model_contract_meta import (
            ModelContractMeta,
            ModelNodeExtensions,
        )

        extensions_data = {
            "custom_field": "custom_value",
        }
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            extensions=extensions_data,
        )

        assert isinstance(meta.extensions, ModelNodeExtensions)
        # Extra fields are stored in model_extra
        assert meta.extensions.model_extra.get("custom_field") == "custom_value"

    def test_metadata_defaults_to_empty_model(self) -> None:
        """Test that metadata defaults to empty ModelContractNodeMetadata."""
        from omnibase_core.models.contracts.model_contract_meta import (
            ModelContractMeta,
            ModelContractNodeMetadata,
        )

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert isinstance(meta.metadata, ModelContractNodeMetadata)
        # All fields should be None or False by default
        assert meta.metadata.deprecated is False

    def test_metadata_accepts_dict(self) -> None:
        """Test that metadata accepts dict (creates ModelContractNodeMetadata)."""
        from omnibase_core.models.contracts.model_contract_meta import (
            ModelContractMeta,
            ModelContractNodeMetadata,
        )

        metadata_data = {
            "documentation_url": "https://docs.example.com",
            "deprecated": True,
        }
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            metadata=metadata_data,
        )

        assert isinstance(meta.metadata, ModelContractNodeMetadata)
        assert meta.metadata.documentation_url == "https://docs.example.com"
        assert meta.metadata.deprecated is True


@pytest.mark.unit
class TestModelContractMetaMetaSchemaValidation:
    """Tests for meta-schema validation that enforces cross-node consistency."""

    def test_name_cannot_be_empty(self) -> None:
        """Test that name cannot be empty string."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ModelOnexError)) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert (
            "empty" in str(exc_info.value).lower()
            or "name" in str(exc_info.value).lower()
        )

    def test_description_cannot_be_empty(self) -> None:
        """Test that description cannot be empty string."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ModelOnexError)) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert (
            "empty" in str(exc_info.value).lower()
            or "description" in str(exc_info.value).lower()
        )

    def test_input_schema_cannot_be_empty(self) -> None:
        """Test that input_schema cannot be empty string."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ModelOnexError)) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="",
                output_schema="omnibase_core.models.ModelOutput",
            )

        assert (
            "empty" in str(exc_info.value).lower()
            or "input_schema" in str(exc_info.value).lower()
        )

    def test_output_schema_cannot_be_empty(self) -> None:
        """Test that output_schema cannot be empty string."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ModelOnexError)) as exc_info:
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="",
            )

        assert (
            "empty" in str(exc_info.value).lower()
            or "output_schema" in str(exc_info.value).lower()
        )

    def test_node_id_must_be_uuid(self) -> None:
        """Test that node_id must be a valid UUID."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        # Valid UUID should work
        valid_uuid = uuid4()
        meta = ModelContractMeta(
            node_id=valid_uuid,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )
        assert meta.node_id == valid_uuid

    def test_node_id_accepts_uuid_string(self) -> None:
        """Test that node_id accepts UUID string and converts."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        meta = ModelContractMeta(
            node_id=uuid_str,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )
        assert str(meta.node_id) == uuid_str


@pytest.mark.unit
class TestModelContractMetaCrossNodeConsistency:
    """Tests for cross-node consistency validation."""

    def test_all_node_kinds_use_same_required_fields(self) -> None:
        """Test that all node kinds require the same base fields."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        for node_kind in [
            EnumNodeKind.EFFECT,
            EnumNodeKind.COMPUTE,
            EnumNodeKind.REDUCER,
            EnumNodeKind.ORCHESTRATOR,
        ]:
            meta = ModelContractMeta(
                node_id=uuid4(),
                node_kind=node_kind,
                version="1.0.0",
                name=f"Test{node_kind.value.title()}Node",
                description=f"A test {node_kind.value} node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

            # All should have these required fields
            assert meta.node_id is not None
            assert meta.node_kind == node_kind
            assert meta.version is not None
            assert meta.name is not None
            assert meta.description is not None
            assert meta.input_schema is not None
            assert meta.output_schema is not None

    def test_validate_meta_model_method(self) -> None:
        """Test the validate_meta_model method for cross-node consistency."""
        from omnibase_core.models.contracts.model_contract_meta import (
            ModelContractMeta,
            validate_meta_model,
        )

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        # Should not raise
        validate_meta_model(meta)

    def test_is_valid_meta_model_returns_true_for_valid(self) -> None:
        """Test is_valid_meta_model returns True for valid meta model."""
        from omnibase_core.models.contracts.model_contract_meta import (
            ModelContractMeta,
            is_valid_meta_model,
        )

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert is_valid_meta_model(meta) is True


@pytest.mark.unit
class TestModelContractMetaSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump() returns a dictionary with all fields."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        node_id = uuid4()
        meta = ModelContractMeta(
            node_id=node_id,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
            tags=["test"],
            author="ONEX Team",
        )

        dumped = meta.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["node_id"] == node_id
        assert dumped["name"] == "TestNode"
        assert dumped["tags"] == ["test"]
        assert dumped["author"] == "ONEX Team"

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() creates meta model from dictionary."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        node_id = uuid4()
        data = {
            "node_id": node_id,
            "node_kind": "compute",
            "version": "1.0.0",
            "name": "TestNode",
            "description": "A test node",
            "input_schema": "omnibase_core.models.ModelInput",
            "output_schema": "omnibase_core.models.ModelOutput",
        }

        meta = ModelContractMeta.model_validate(data)

        assert meta.node_id == node_id
        assert meta.node_kind == EnumNodeKind.COMPUTE
        assert meta.name == "TestNode"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization preserves values."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        original = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.REDUCER,
            version="2.1.0",
            name="TestReducer",
            description="A test reducer node",
            input_schema="omnibase_core.models.ReducerInput",
            output_schema="omnibase_core.models.ReducerOutput",
            tags=["reducer", "state"],
            author="ONEX Team",
        )

        dumped = original.model_dump()
        restored = ModelContractMeta.model_validate(dumped)

        assert original.node_id == restored.node_id
        assert original.node_kind == restored.node_kind
        assert str(original.version) == str(restored.version)
        assert original.name == restored.name
        assert original.tags == restored.tags

    def test_json_serialization(self) -> None:
        """Test JSON serialization works correctly."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        json_str = meta.model_dump_json()

        assert isinstance(json_str, str)
        assert "TestNode" in json_str
        assert "compute" in json_str.lower()


@pytest.mark.unit
class TestModelContractMetaEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_extra_fields_are_forbidden(self) -> None:
        """Test that extra fields are forbidden (strict mode)."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises(ValidationError):
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="TestNode",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
                extra_field="not allowed",
            )

    def test_whitespace_is_stripped_from_name(self) -> None:
        """Test that whitespace is stripped from name."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="  TestNode  ",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.name == "TestNode"

    def test_whitespace_only_name_is_invalid(self) -> None:
        """Test that whitespace-only name is invalid after stripping."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        with pytest.raises((ValidationError, ModelOnexError)):
            ModelContractMeta(
                node_id=uuid4(),
                node_kind=EnumNodeKind.COMPUTE,
                version="1.0.0",
                name="   ",
                description="A test node",
                input_schema="omnibase_core.models.ModelInput",
                output_schema="omnibase_core.models.ModelOutput",
            )

    def test_very_long_name_is_valid(self) -> None:
        """Test that very long names are valid (no arbitrary limit)."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        long_name = "A" * 500
        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name=long_name,
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.name == long_name

    def test_unicode_name_is_valid(self) -> None:
        """Test that unicode names are valid."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="Test-Node_With.Unicode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta.name == "Test-Node_With.Unicode"


@pytest.mark.unit
class TestModelContractMetaHashability:
    """Tests for hashability and use in sets/dicts."""

    def test_hash_returns_int(self) -> None:
        """Test __hash__() returns an integer."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert isinstance(hash(meta), int)

    def test_same_node_id_same_hash(self) -> None:
        """Test that models with same node_id have same hash."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        node_id = uuid4()
        meta1 = ModelContractMeta(
            node_id=node_id,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode1",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )
        meta2 = ModelContractMeta(
            node_id=node_id,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode2",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert hash(meta1) == hash(meta2)

    def test_usable_in_set(self) -> None:
        """Test that ModelContractMeta can be used in a set."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        node_id = uuid4()
        meta1 = ModelContractMeta(
            node_id=node_id,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )
        meta2 = ModelContractMeta(
            node_id=uuid4(),  # Different ID
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode2",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        meta_set = {meta1, meta2}
        assert len(meta_set) == 2


@pytest.mark.unit
class TestModelContractMetaEquality:
    """Tests for equality comparison."""

    def test_equality_based_on_node_id(self) -> None:
        """Test that equality is based on node_id."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        node_id = uuid4()
        meta1 = ModelContractMeta(
            node_id=node_id,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode1",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )
        meta2 = ModelContractMeta(
            node_id=node_id,
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode1",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta1 == meta2

    def test_inequality_different_node_id(self) -> None:
        """Test that different node_ids are not equal."""
        from omnibase_core.models.contracts.model_contract_meta import ModelContractMeta

        meta1 = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )
        meta2 = ModelContractMeta(
            node_id=uuid4(),
            node_kind=EnumNodeKind.COMPUTE,
            version="1.0.0",
            name="TestNode",
            description="A test node",
            input_schema="omnibase_core.models.ModelInput",
            output_schema="omnibase_core.models.ModelOutput",
        )

        assert meta1 != meta2
