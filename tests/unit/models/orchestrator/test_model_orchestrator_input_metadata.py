# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelOrchestratorInputMetadata.

Tests verify that ModelOrchestratorInputMetadata provides:
1. Pure type safety (no dict fallback)
2. IDE autocomplete support
3. Proper defaults for all fields
4. Validation of field types
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.orchestrator.model_orchestrator_input_metadata import (
    ModelOrchestratorInputMetadata,
)


@pytest.mark.unit
class TestModelOrchestratorInputMetadataBasicCreation:
    """Test basic ModelOrchestratorInputMetadata creation and validation."""

    def test_metadata_minimal_creation(self) -> None:
        """Test creating metadata with no fields (all defaults)."""
        metadata = ModelOrchestratorInputMetadata()

        assert metadata.source is None
        assert metadata.environment is None
        assert metadata.correlation_id is None
        assert metadata.trigger == "process"
        assert metadata.persist_result is False

    def test_metadata_full_creation(self) -> None:
        """Test creating metadata with all fields specified."""
        correlation_id = uuid4()

        metadata = ModelOrchestratorInputMetadata(
            source="api_gateway",
            environment="production",
            correlation_id=correlation_id,
            trigger="start",
            persist_result=True,
        )

        assert metadata.source == "api_gateway"
        assert metadata.environment == "production"
        assert metadata.correlation_id == correlation_id
        assert metadata.trigger == "start"
        assert metadata.persist_result is True

    def test_metadata_partial_creation(self) -> None:
        """Test creating metadata with partial fields."""
        metadata = ModelOrchestratorInputMetadata(
            source="scheduler",
            trigger="process_batch",
        )

        assert metadata.source == "scheduler"
        assert metadata.environment is None
        assert metadata.correlation_id is None
        assert metadata.trigger == "process_batch"
        assert metadata.persist_result is False


@pytest.mark.unit
class TestModelOrchestratorInputMetadataMutability:
    """Test ModelOrchestratorInputMetadata mutability."""

    def test_metadata_is_mutable(self) -> None:
        """Test that metadata is mutable (frozen=False)."""
        metadata = ModelOrchestratorInputMetadata()

        # Should not raise - model is mutable
        metadata.source = "updated_source"
        metadata.environment = "staging"
        metadata.trigger = "new_trigger"
        metadata.persist_result = True

        assert metadata.source == "updated_source"
        assert metadata.environment == "staging"
        assert metadata.trigger == "new_trigger"
        assert metadata.persist_result is True

    def test_metadata_correlation_id_can_be_updated(self) -> None:
        """Test that correlation_id can be updated after creation."""
        metadata = ModelOrchestratorInputMetadata()
        new_correlation_id = uuid4()

        metadata.correlation_id = new_correlation_id

        assert metadata.correlation_id == new_correlation_id


@pytest.mark.unit
class TestModelOrchestratorInputMetadataValidation:
    """Test ModelOrchestratorInputMetadata field validation."""

    def test_metadata_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelOrchestratorInputMetadata(
                source="test",
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_metadata_correlation_id_must_be_uuid(self) -> None:
        """Test that correlation_id must be a valid UUID."""
        with pytest.raises(ValidationError):
            ModelOrchestratorInputMetadata(
                correlation_id="not-a-uuid",  # type: ignore[arg-type]
            )

    def test_metadata_correlation_id_accepts_uuid_string(self) -> None:
        """Test that correlation_id accepts string UUID (Pydantic coercion)."""
        test_uuid = uuid4()
        metadata = ModelOrchestratorInputMetadata(
            correlation_id=str(test_uuid),  # type: ignore[arg-type]
        )

        assert metadata.correlation_id == test_uuid
        assert isinstance(metadata.correlation_id, UUID)

    def test_metadata_trigger_must_be_string(self) -> None:
        """Test that trigger must be a string."""
        with pytest.raises(ValidationError):
            ModelOrchestratorInputMetadata(
                trigger=123,  # type: ignore[arg-type]
            )

    def test_metadata_persist_result_must_be_bool(self) -> None:
        """Test that persist_result must be a boolean-coercible value."""
        # Pydantic coerces strings to bool, so test with non-coercible type
        with pytest.raises(ValidationError):
            ModelOrchestratorInputMetadata(
                persist_result={"invalid": "type"},  # type: ignore[arg-type]
            )


@pytest.mark.unit
class TestModelOrchestratorInputMetadataSerialization:
    """Test ModelOrchestratorInputMetadata serialization and deserialization."""

    def test_metadata_to_dict(self) -> None:
        """Test serializing metadata to dict."""
        correlation_id = uuid4()
        metadata = ModelOrchestratorInputMetadata(
            source="api",
            environment="test",
            correlation_id=correlation_id,
            trigger="validate",
            persist_result=True,
        )

        data = metadata.model_dump()

        assert data["source"] == "api"
        assert data["environment"] == "test"
        assert data["correlation_id"] == correlation_id
        assert data["trigger"] == "validate"
        assert data["persist_result"] is True

    def test_metadata_from_dict(self) -> None:
        """Test deserializing metadata from dict."""
        correlation_id = uuid4()
        data = {
            "source": "scheduler",
            "environment": "staging",
            "correlation_id": correlation_id,
            "trigger": "batch_process",
            "persist_result": False,
        }

        metadata = ModelOrchestratorInputMetadata.model_validate(data)

        assert metadata.source == "scheduler"
        assert metadata.environment == "staging"
        assert metadata.correlation_id == correlation_id
        assert metadata.trigger == "batch_process"
        assert metadata.persist_result is False

    def test_metadata_roundtrip(self) -> None:
        """Test roundtrip serialization preserves data."""
        original = ModelOrchestratorInputMetadata(
            source="worker",
            environment="production",
            correlation_id=uuid4(),
            trigger="execute",
            persist_result=True,
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelOrchestratorInputMetadata.model_validate(data)

        assert restored.source == original.source
        assert restored.environment == original.environment
        assert restored.correlation_id == original.correlation_id
        assert restored.trigger == original.trigger
        assert restored.persist_result == original.persist_result

    def test_metadata_to_json(self) -> None:
        """Test JSON serialization."""
        correlation_id = uuid4()
        metadata = ModelOrchestratorInputMetadata(
            source="api",
            correlation_id=correlation_id,
        )

        json_str = metadata.model_dump_json()

        assert '"source":"api"' in json_str
        assert str(correlation_id) in json_str


@pytest.mark.unit
class TestModelOrchestratorInputMetadataFromAttributes:
    """Test ModelOrchestratorInputMetadata from_attributes support."""

    def test_metadata_from_attributes(self) -> None:
        """Test creating metadata from object with attributes."""

        class MockMetadata:
            source = "mock_source"
            environment = "mock_env"
            correlation_id = uuid4()
            trigger = "mock_trigger"
            persist_result = True

        mock = MockMetadata()
        metadata = ModelOrchestratorInputMetadata.model_validate(mock)

        assert metadata.source == mock.source
        assert metadata.environment == mock.environment
        assert metadata.correlation_id == mock.correlation_id
        assert metadata.trigger == mock.trigger
        assert metadata.persist_result == mock.persist_result


@pytest.mark.unit
class TestModelOrchestratorInputMetadataDefaultFactory:
    """Test ModelOrchestratorInputMetadata default_factory behavior."""

    def test_metadata_independent_instances(self) -> None:
        """Test that each metadata instance is independent."""
        metadata1 = ModelOrchestratorInputMetadata()
        metadata2 = ModelOrchestratorInputMetadata()

        # Modify one instance
        metadata1.source = "source1"
        metadata2.source = "source2"

        # Each should have independent values
        assert metadata1.source == "source1"
        assert metadata2.source == "source2"
        assert metadata1 is not metadata2
