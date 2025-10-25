"""Tests for ModelService."""

from uuid import uuid4

import pytest

from omnibase_core.models.container.model_service import ModelService


class TestModelService:
    """Tests for ModelService model."""

    def test_initialization_with_required_fields(self):
        """Test service initialization with required fields."""
        service_id = uuid4()
        service = ModelService(
            service_id=service_id,
            service_name="test_service",
            service_type="compute",
        )

        assert service.service_id == service_id
        assert service.service_name == "test_service"
        assert service.service_type == "compute"
        assert service.protocol_name is None
        assert service.metadata == {}
        assert service.health_status == "unknown"

    def test_initialization_with_all_fields(self):
        """Test service initialization with all fields."""
        service_id = uuid4()
        metadata = {"version": "1.0.0", "region": "us-east-1"}

        service = ModelService(
            service_id=service_id,
            service_name="logger_service",
            service_type="effect",
            protocol_name="ProtocolLogger",
            metadata=metadata,
            health_status="healthy",
        )

        assert service.service_id == service_id
        assert service.service_name == "logger_service"
        assert service.service_type == "effect"
        assert service.protocol_name == "ProtocolLogger"
        assert service.metadata == metadata
        assert service.health_status == "healthy"

    def test_frozen_model(self):
        """Test that model is frozen (immutable)."""
        service = ModelService(
            service_id=uuid4(),
            service_name="test",
            service_type="compute",
        )

        with pytest.raises(Exception):  # ValidationError for frozen model
            service.service_name = "modified"  # type: ignore

    def test_service_types(self):
        """Test different service types."""
        service_id = uuid4()
        for service_type in ["effect", "compute", "reducer", "orchestrator"]:
            service = ModelService(
                service_id=service_id,
                service_name=f"{service_type}_service",
                service_type=service_type,
            )
            assert service.service_type == service_type

    def test_health_statuses(self):
        """Test different health status values."""
        service_id = uuid4()
        for status in ["healthy", "unhealthy", "degraded", "unknown"]:
            service = ModelService(
                service_id=service_id,
                service_name="test_service",
                service_type="compute",
                health_status=status,
            )
            assert service.health_status == status

    def test_metadata_tracking(self):
        """Test metadata dictionary."""
        service = ModelService(
            service_id=uuid4(),
            service_name="test_service",
            service_type="compute",
            metadata={
                "version": "2.1.0",
                "author": "ONEX Team",
                "region": "us-west-2",
                "environment": "production",
            },
        )

        assert service.metadata["version"] == "2.1.0"
        assert service.metadata["author"] == "ONEX Team"
        assert service.metadata["region"] == "us-west-2"
        assert service.metadata["environment"] == "production"

    def test_protocol_name_optional(self):
        """Test protocol_name is optional."""
        # Without protocol_name
        service1 = ModelService(
            service_id=uuid4(),
            service_name="simple_service",
            service_type="compute",
        )
        assert service1.protocol_name is None

        # With protocol_name
        service2 = ModelService(
            service_id=uuid4(),
            service_name="protocol_service",
            service_type="effect",
            protocol_name="ProtocolLogger",
        )
        assert service2.protocol_name == "ProtocolLogger"

    def test_serialization_deserialization(self):
        """Test model can be serialized and deserialized."""
        service_id = uuid4()
        service = ModelService(
            service_id=service_id,
            service_name="serializable_service",
            service_type="reducer",
            protocol_name="ProtocolDatabase",
            metadata={"key": "value"},
            health_status="healthy",
        )

        # Serialize to dict
        data = service.model_dump()

        # Deserialize from dict
        restored = ModelService(**data)

        assert restored.service_id == service.service_id
        assert restored.service_name == service.service_name
        assert restored.service_type == service.service_type
        assert restored.protocol_name == service.protocol_name
        assert restored.metadata == service.metadata
        assert restored.health_status == service.health_status

    def test_different_service_configurations(self):
        """Test various service configurations."""
        # Effect service with protocol
        effect_service = ModelService(
            service_id=uuid4(),
            service_name="database_writer",
            service_type="effect",
            protocol_name="ProtocolDatabaseWriter",
            health_status="healthy",
        )
        assert effect_service.service_type == "effect"
        assert effect_service.protocol_name == "ProtocolDatabaseWriter"

        # Compute service without protocol
        compute_service = ModelService(
            service_id=uuid4(),
            service_name="data_transformer",
            service_type="compute",
            health_status="healthy",
        )
        assert compute_service.service_type == "compute"
        assert compute_service.protocol_name is None

        # Reducer service
        reducer_service = ModelService(
            service_id=uuid4(),
            service_name="state_aggregator",
            service_type="reducer",
            health_status="degraded",
            metadata={"retry_count": "3"},
        )
        assert reducer_service.service_type == "reducer"
        assert reducer_service.health_status == "degraded"

        # Orchestrator service
        orchestrator_service = ModelService(
            service_id=uuid4(),
            service_name="workflow_coordinator",
            service_type="orchestrator",
            health_status="healthy",
            metadata={"max_concurrent": "10"},
        )
        assert orchestrator_service.service_type == "orchestrator"
