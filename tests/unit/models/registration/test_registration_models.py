import pytest

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Unit tests for registration domain models.

Tests verify:
- ModelRegistrationPayload construction and validation
- ModelDualRegistrationOutcome construction and validation
- Immutability and ConfigDict settings
- JSON serialization and deserialization
- ONEX pattern compliance (frozen, extra="forbid", from_attributes)

Test Organization:
- TestModelRegistrationPayload: Payload model tests
- TestModelDualRegistrationOutcome: Outcome model tests
- TestSerializationRoundtrip: Serialization tests for both models
- TestONEXPatterns: ONEX-specific pattern compliance tests

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- These are pure Pydantic validation tests with no I/O
"""

import json
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError

from omnibase_core.models.intents import ModelRegistrationRecordBase
from omnibase_core.models.registration import (
    ModelDualRegistrationOutcome,
    ModelRegistrationPayload,
)

# ---- Fixtures ----


@pytest.fixture
def node_id() -> UUID:
    """Provide a fresh node ID for each test."""
    return uuid4()


@pytest.fixture
def deployment_id() -> UUID:
    """Provide a fresh deployment ID for each test."""
    return uuid4()


@pytest.fixture
def correlation_id() -> UUID:
    """Provide a fresh correlation ID for each test."""
    return uuid4()


@pytest.fixture
def sample_record() -> ModelRegistrationRecordBase:
    """Provide a sample Pydantic record for payload tests."""

    class SampleRecord(ModelRegistrationRecordBase):
        node_id: str
        node_type: str
        status: str

    return SampleRecord(node_id="node-123", node_type="compute", status="active")


@pytest.fixture
def sample_payload(
    node_id: UUID, deployment_id: UUID, sample_record: ModelRegistrationRecordBase
) -> ModelRegistrationPayload:
    """Provide a fully populated ModelRegistrationPayload."""
    return ModelRegistrationPayload(
        node_id=node_id,
        deployment_id=deployment_id,
        environment="production",
        network_id="vpc-main",
        consul_service_id="node-compute-123",
        consul_service_name="onex-compute",
        consul_tags=["node_type:compute", "env:production"],
        consul_health_check={"http": "http://localhost:8080/health"},
        postgres_record=sample_record,
    )


@pytest.fixture
def sample_success_outcome(
    node_id: UUID, correlation_id: UUID
) -> ModelDualRegistrationOutcome:
    """Provide a successful outcome."""
    return ModelDualRegistrationOutcome(
        node_id=node_id,
        status="success",
        postgres_applied=True,
        consul_applied=True,
        correlation_id=correlation_id,
    )


@pytest.fixture
def sample_partial_outcome(
    node_id: UUID, correlation_id: UUID
) -> ModelDualRegistrationOutcome:
    """Provide a partial outcome (Postgres success, Consul failure)."""
    return ModelDualRegistrationOutcome(
        node_id=node_id,
        status="partial",
        postgres_applied=True,
        consul_applied=False,
        consul_error="Connection timeout",
        correlation_id=correlation_id,
    )


@pytest.fixture
def sample_failed_outcome(
    node_id: UUID, correlation_id: UUID
) -> ModelDualRegistrationOutcome:
    """Provide a failed outcome."""
    return ModelDualRegistrationOutcome(
        node_id=node_id,
        status="failed",
        postgres_applied=False,
        consul_applied=False,
        postgres_error="Database connection refused",
        consul_error="Service unavailable",
        correlation_id=correlation_id,
    )


# ---- Test ModelRegistrationPayload ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelRegistrationPayload:
    """Tests for ModelRegistrationPayload."""

    def test_valid_construction(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test valid payload construction with all required fields."""
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="production",
            network_id="vpc-main",
            consul_service_id="node-123",
            consul_service_name="onex-compute",
            consul_tags=["tag1"],
            consul_health_check=None,
            postgres_record=sample_record,
        )
        assert payload.node_id == node_id
        assert payload.deployment_id == deployment_id
        assert payload.environment == "production"
        assert payload.network_id == "vpc-main"
        assert payload.consul_service_id == "node-123"
        assert payload.consul_service_name == "onex-compute"
        assert payload.consul_tags == ["tag1"]
        assert payload.consul_health_check is None
        assert payload.postgres_record == sample_record

    def test_default_consul_tags(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test consul_tags defaults to empty list."""
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="staging",
            network_id="internal",
            consul_service_id="svc-123",
            consul_service_name="test-service",
            postgres_record=sample_record,
        )
        assert payload.consul_tags == []

    def test_default_health_check(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test consul_health_check defaults to None."""
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="staging",
            network_id="internal",
            consul_service_id="svc-123",
            consul_service_name="test-service",
            postgres_record=sample_record,
        )
        assert payload.consul_health_check is None

    def test_immutability(self, sample_payload: ModelRegistrationPayload) -> None:
        """Test payload is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_payload.environment = "changed"

    def test_missing_required_field(self, node_id: UUID, deployment_id: UUID) -> None:
        """Test missing required field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="production",
                network_id="vpc-main",
                consul_service_id="node-123",
                consul_service_name="onex-compute",
                # Missing postgres_record
            )
        assert "postgres_record" in str(exc_info.value)

    def test_environment_min_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test environment minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="",  # Empty string
                network_id="vpc-main",
                consul_service_id="node-123",
                consul_service_name="test",
                postgres_record=sample_record,
            )
        assert "environment" in str(exc_info.value)

    def test_network_id_min_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test network_id minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="prod",
                network_id="",  # Empty string
                consul_service_id="node-123",
                consul_service_name="test",
                postgres_record=sample_record,
            )
        assert "network_id" in str(exc_info.value)

    def test_consul_service_id_min_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test consul_service_id minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="prod",
                network_id="vpc",
                consul_service_id="",  # Empty string
                consul_service_name="test",
                postgres_record=sample_record,
            )
        assert "consul_service_id" in str(exc_info.value)

    def test_consul_service_name_min_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test consul_service_name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="prod",
                network_id="vpc",
                consul_service_id="node-123",
                consul_service_name="",  # Empty string
                postgres_record=sample_record,
            )
        assert "consul_service_name" in str(exc_info.value)

    def test_extra_fields_forbidden(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="prod",
                network_id="vpc",
                consul_service_id="node-123",
                consul_service_name="test",
                postgres_record=sample_record,
                unknown_field="value",  # Extra field
            )
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str

    def test_health_check_with_config(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test payload with health check configuration."""
        health_config = {"http": "http://localhost:8080/health", "interval": "10s"}
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="prod",
            network_id="vpc",
            consul_service_id="node-123",
            consul_service_name="test",
            consul_health_check=health_config,
            postgres_record=sample_record,
        )
        assert payload.consul_health_check == health_config

    def test_multiple_tags(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test payload with multiple consul tags."""
        tags = ["node_type:compute", "version:1.0", "env:prod"]
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="prod",
            network_id="vpc",
            consul_service_id="node-123",
            consul_service_name="test",
            consul_tags=tags,
            postgres_record=sample_record,
        )
        assert payload.consul_tags == tags
        assert len(payload.consul_tags) == 3


# ---- Test ModelDualRegistrationOutcome ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelDualRegistrationOutcome:
    """Tests for ModelDualRegistrationOutcome."""

    def test_valid_success_construction(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test valid success outcome construction."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="success",
            postgres_applied=True,
            consul_applied=True,
            correlation_id=correlation_id,
        )
        assert outcome.node_id == node_id
        assert outcome.status == "success"
        assert outcome.postgres_applied is True
        assert outcome.consul_applied is True
        assert outcome.postgres_error is None
        assert outcome.consul_error is None
        assert outcome.correlation_id == correlation_id

    def test_valid_partial_construction(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test valid partial outcome construction."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            consul_applied=False,
            consul_error="Timeout",
            correlation_id=correlation_id,
        )
        assert outcome.status == "partial"
        assert outcome.postgres_applied is True
        assert outcome.consul_applied is False
        assert outcome.consul_error == "Timeout"

    def test_valid_failed_construction(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test valid failed outcome construction."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            consul_applied=False,
            postgres_error="DB error",
            consul_error="Service unavailable",
            correlation_id=correlation_id,
        )
        assert outcome.status == "failed"
        assert outcome.postgres_applied is False
        assert outcome.consul_applied is False
        assert outcome.postgres_error == "DB error"
        assert outcome.consul_error == "Service unavailable"

    def test_immutability(
        self, sample_success_outcome: ModelDualRegistrationOutcome
    ) -> None:
        """Test outcome is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_success_outcome.status = "failed"

    def test_missing_required_field(self, node_id: UUID) -> None:
        """Test missing required field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=True,
                consul_applied=True,
                # Missing correlation_id
            )
        assert "correlation_id" in str(exc_info.value)

    def test_invalid_status_rejected(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test invalid status value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="invalid",  # Not success/partial/failed
                postgres_applied=True,
                consul_applied=True,
                correlation_id=correlation_id,
            )
        assert "status" in str(exc_info.value)

    def test_extra_fields_forbidden(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=True,
                consul_applied=True,
                correlation_id=correlation_id,
                extra_field="not_allowed",
            )
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "extra_field" in error_str

    def test_default_error_fields(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test error fields default to None."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="success",
            postgres_applied=True,
            consul_applied=True,
            correlation_id=correlation_id,
        )
        assert outcome.postgres_error is None
        assert outcome.consul_error is None


# ---- Test Serialization ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestSerializationRoundtrip:
    """Tests for JSON serialization and round-trip."""

    def test_payload_model_dump_json_mode(
        self, sample_payload: ModelRegistrationPayload
    ) -> None:
        """Test payload model_dump with mode='json' produces valid JSON types."""
        data = sample_payload.model_dump(mode="json")
        assert isinstance(data, dict)
        assert isinstance(data["node_id"], str)  # UUID as string
        assert isinstance(data["deployment_id"], str)
        assert isinstance(data["environment"], str)
        assert isinstance(data["consul_tags"], list)
        assert isinstance(data["postgres_record"], dict)

    def test_outcome_model_dump_json_mode(
        self, sample_success_outcome: ModelDualRegistrationOutcome
    ) -> None:
        """Test outcome model_dump with mode='json' produces valid JSON types."""
        data = sample_success_outcome.model_dump(mode="json")
        assert isinstance(data, dict)
        assert isinstance(data["node_id"], str)  # UUID as string
        assert isinstance(data["correlation_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["postgres_applied"], bool)
        assert isinstance(data["consul_applied"], bool)

    def test_payload_roundtrip_serialization(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test payload can be serialized and deserialized."""
        original = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="production",
            network_id="vpc-main",
            consul_service_id="node-123",
            consul_service_name="onex-compute",
            consul_tags=["test"],
            consul_health_check={"http": "http://localhost/health"},
            postgres_record=sample_record,
        )
        data = original.model_dump(mode="json")
        restored = ModelRegistrationPayload.model_validate(data)

        assert str(restored.node_id) == str(original.node_id)
        assert str(restored.deployment_id) == str(original.deployment_id)
        assert restored.environment == original.environment
        assert restored.network_id == original.network_id
        assert restored.consul_service_id == original.consul_service_id
        assert restored.consul_service_name == original.consul_service_name
        assert restored.consul_tags == original.consul_tags
        assert restored.consul_health_check == original.consul_health_check

    def test_outcome_roundtrip_serialization(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test outcome can be serialized and deserialized."""
        original = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            consul_applied=False,
            consul_error="Connection failed",
            correlation_id=correlation_id,
        )
        data = original.model_dump(mode="json")
        restored = ModelDualRegistrationOutcome.model_validate(data)

        assert str(restored.node_id) == str(original.node_id)
        assert restored.status == original.status
        assert restored.postgres_applied == original.postgres_applied
        assert restored.consul_applied == original.consul_applied
        assert restored.consul_error == original.consul_error
        assert str(restored.correlation_id) == str(original.correlation_id)

    def test_payload_json_string_roundtrip(
        self, sample_payload: ModelRegistrationPayload
    ) -> None:
        """Test payload survives JSON string round-trip."""
        json_str = sample_payload.model_dump_json()
        dict_data = json.loads(json_str)
        restored = ModelRegistrationPayload.model_validate(dict_data)

        assert str(restored.node_id) == str(sample_payload.node_id)
        assert restored.environment == sample_payload.environment

    def test_outcome_json_string_roundtrip(
        self, sample_partial_outcome: ModelDualRegistrationOutcome
    ) -> None:
        """Test outcome survives JSON string round-trip."""
        json_str = sample_partial_outcome.model_dump_json()
        dict_data = json.loads(json_str)
        restored = ModelDualRegistrationOutcome.model_validate(dict_data)

        assert str(restored.node_id) == str(sample_partial_outcome.node_id)
        assert restored.status == sample_partial_outcome.status
        assert restored.consul_error == sample_partial_outcome.consul_error


# ---- Test ONEX Patterns ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestONEXPatterns:
    """Tests for ONEX-specific patterns and configurations."""

    def test_payload_config_frozen(self) -> None:
        """Test ModelRegistrationPayload is configured as frozen."""
        assert ModelRegistrationPayload.model_config.get("frozen") is True

    def test_payload_config_extra_forbid(self) -> None:
        """Test ModelRegistrationPayload forbids extra fields."""
        assert ModelRegistrationPayload.model_config.get("extra") == "forbid"

    def test_payload_config_from_attributes(self) -> None:
        """Test ModelRegistrationPayload has from_attributes enabled."""
        assert ModelRegistrationPayload.model_config.get("from_attributes") is True

    def test_payload_config_validate_assignment_not_needed(self) -> None:
        """Test ModelRegistrationPayload does NOT need validate_assignment when frozen.

        Per Pydantic docs: validate_assignment=True is redundant when frozen=True.
        Frozen models cannot be mutated at all (any assignment raises ValidationError),
        so there's no assignment to validate. Immutability is already tested in
        test_immutability() which verifies assignment raises ValidationError.
        """
        # Verify frozen=True is set (makes validate_assignment redundant)
        assert ModelRegistrationPayload.model_config.get("frozen") is True
        # validate_assignment should NOT be set - it's redundant with frozen=True
        assert ModelRegistrationPayload.model_config.get("validate_assignment") is None

    def test_outcome_config_frozen(self) -> None:
        """Test ModelDualRegistrationOutcome is configured as frozen."""
        assert ModelDualRegistrationOutcome.model_config.get("frozen") is True

    def test_outcome_config_extra_forbid(self) -> None:
        """Test ModelDualRegistrationOutcome forbids extra fields."""
        assert ModelDualRegistrationOutcome.model_config.get("extra") == "forbid"

    def test_outcome_config_from_attributes(self) -> None:
        """Test ModelDualRegistrationOutcome has from_attributes enabled."""
        assert ModelDualRegistrationOutcome.model_config.get("from_attributes") is True

    def test_outcome_config_validate_assignment_not_needed(self) -> None:
        """Test ModelDualRegistrationOutcome does NOT need validate_assignment when frozen.

        Per Pydantic docs: validate_assignment=True is redundant when frozen=True.
        Frozen models cannot be mutated at all (any assignment raises ValidationError),
        so there's no assignment to validate. Immutability is already tested in
        test_immutability() which verifies assignment raises ValidationError.
        """
        # Verify frozen=True is set (makes validate_assignment redundant)
        assert ModelDualRegistrationOutcome.model_config.get("frozen") is True
        # validate_assignment should NOT be set - it's redundant with frozen=True
        assert (
            ModelDualRegistrationOutcome.model_config.get("validate_assignment") is None
        )

    def test_payload_from_attributes_construction(
        self, node_id: UUID, deployment_id: UUID
    ) -> None:
        """Test from_attributes allows attribute-based construction."""
        nid = node_id
        did = deployment_id

        class PayloadLike:
            environment = "production"
            network_id = "vpc-main"
            consul_service_id = "svc-123"
            consul_service_name = "test"
            consul_tags: list[str] = []
            consul_health_check = None

            def __init__(self) -> None:
                self.node_id = nid
                self.deployment_id = did

                class Record(BaseModel):
                    val: str = "test"

                self.postgres_record = Record()

        payload = ModelRegistrationPayload.model_validate(PayloadLike())
        assert payload.environment == "production"
        assert payload.consul_service_id == "svc-123"

    def test_outcome_from_attributes_construction(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test from_attributes allows attribute-based construction."""
        nid = node_id
        cid = correlation_id

        class OutcomeLike:
            status = "success"
            postgres_applied = True
            consul_applied = True
            postgres_error = None
            consul_error = None

            def __init__(self) -> None:
                self.node_id = nid
                self.correlation_id = cid

        outcome = ModelDualRegistrationOutcome.model_validate(OutcomeLike())
        assert outcome.status == "success"
        assert outcome.postgres_applied is True


# ---- Test Status Consistency Validation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestStatusConsistencyValidation:
    """Tests for status consistency validator in ModelDualRegistrationOutcome.

    The validator enforces domain invariants that prevent construction of
    inconsistent outcome states. It ensures the status field always matches
    the actual operation outcomes (postgres_applied and consul_applied flags).
    """

    def test_success_status_requires_both_operations_succeeded(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='success' requires both postgres_applied=True and consul_applied=True."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="success",
            postgres_applied=True,
            consul_applied=True,
            correlation_id=correlation_id,
        )
        assert outcome.status == "success"
        assert outcome.postgres_applied is True
        assert outcome.consul_applied is True

    def test_success_status_postgres_failed_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='success' with postgres_applied=False raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=False,  # Inconsistent with success
                consul_applied=True,
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='success' requires both" in error_msg
        assert "postgres_applied and consul_applied to be True" in error_msg

    def test_success_status_consul_failed_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='success' with consul_applied=False raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=True,
                consul_applied=False,  # Inconsistent with success
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='success' requires both" in error_msg

    def test_success_status_both_failed_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='success' with both operations failed raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=False,  # Inconsistent
                consul_applied=False,  # Inconsistent
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='success' requires both" in error_msg

    def test_failed_status_requires_both_operations_failed(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='failed' requires both postgres_applied=False and consul_applied=False."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            consul_applied=False,
            postgres_error="DB connection lost",
            consul_error="Service unavailable",
            correlation_id=correlation_id,
        )
        assert outcome.status == "failed"
        assert outcome.postgres_applied is False
        assert outcome.consul_applied is False

    def test_failed_status_postgres_succeeded_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='failed' with postgres_applied=True raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="failed",
                postgres_applied=True,  # Inconsistent with failed
                consul_applied=False,
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='failed' requires both" in error_msg
        assert "postgres_applied and consul_applied to be False" in error_msg

    def test_failed_status_consul_succeeded_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='failed' with consul_applied=True raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="failed",
                postgres_applied=False,
                consul_applied=True,  # Inconsistent with failed
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='failed' requires both" in error_msg

    def test_failed_status_both_succeeded_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='failed' with both operations succeeded raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="failed",
                postgres_applied=True,  # Inconsistent
                consul_applied=True,  # Inconsistent
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='failed' requires both" in error_msg

    def test_partial_status_postgres_succeeded_consul_failed(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='partial' with postgres succeeded, consul failed."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            consul_applied=False,
            consul_error="Connection timeout",
            correlation_id=correlation_id,
        )
        assert outcome.status == "partial"
        assert outcome.postgres_applied is True
        assert outcome.consul_applied is False

    def test_partial_status_consul_succeeded_postgres_failed(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='partial' with consul succeeded, postgres failed."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=False,
            consul_applied=True,
            postgres_error="Database locked",
            correlation_id=correlation_id,
        )
        assert outcome.status == "partial"
        assert outcome.postgres_applied is False
        assert outcome.consul_applied is True

    def test_partial_status_both_succeeded_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='partial' with both operations succeeded raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="partial",
                postgres_applied=True,  # Inconsistent - both succeeded
                consul_applied=True,  # Inconsistent - both succeeded
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='partial' requires exactly one operation to succeed" in error_msg

    def test_partial_status_both_failed_raises_validation_error(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test status='partial' with both operations failed raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="partial",
                postgres_applied=False,  # Inconsistent - both failed
                consul_applied=False,  # Inconsistent - both failed
                correlation_id=correlation_id,
            )
        error_msg = str(exc_info.value)
        assert "status='partial' requires exactly one operation to succeed" in error_msg


# ---- Test Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_uuid_as_string_accepted_payload(
        self, sample_record: ModelRegistrationRecordBase
    ) -> None:
        """Test UUID can be provided as string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        payload = ModelRegistrationPayload(
            node_id=uuid_str,
            deployment_id=uuid_str,
            environment="test",
            network_id="vpc",
            consul_service_id="svc",
            consul_service_name="test",
            postgres_record=sample_record,
        )
        assert str(payload.node_id) == uuid_str

    def test_uuid_as_string_accepted_outcome(self) -> None:
        """Test UUID can be provided as string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        outcome = ModelDualRegistrationOutcome(
            node_id=uuid_str,
            status="success",
            postgres_applied=True,
            consul_applied=True,
            correlation_id=uuid_str,
        )
        assert str(outcome.node_id) == uuid_str

    def test_invalid_uuid_rejected(
        self, sample_record: ModelRegistrationRecordBase
    ) -> None:
        """Test invalid UUID format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id="not-a-uuid",
                deployment_id=uuid4(),
                environment="test",
                network_id="vpc",
                consul_service_id="svc",
                consul_service_name="test",
                postgres_record=sample_record,
            )
        assert "node_id" in str(exc_info.value)

    def test_environment_at_max_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test environment at max length (100)."""
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="x" * 100,
            network_id="vpc",
            consul_service_id="svc",
            consul_service_name="test",
            postgres_record=sample_record,
        )
        assert len(payload.environment) == 100

    def test_environment_over_max_length_rejected(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test environment over max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="x" * 101,
                network_id="vpc",
                consul_service_id="svc",
                consul_service_name="test",
                postgres_record=sample_record,
            )
        assert "environment" in str(exc_info.value)

    def test_empty_consul_health_check_dict(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test empty health check dict is valid."""
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="test",
            network_id="vpc",
            consul_service_id="svc",
            consul_service_name="test",
            consul_health_check={},
            postgres_record=sample_record,
        )
        assert payload.consul_health_check == {}

    def test_special_characters_in_tags(
        self,
        node_id: UUID,
        deployment_id: UUID,
        sample_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test tags with special characters."""
        tags = ["env:prod", "team:platform/core", "version:1.0.0-beta+build.123"]
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="test",
            network_id="vpc",
            consul_service_id="svc",
            consul_service_name="test",
            consul_tags=tags,
            postgres_record=sample_record,
        )
        assert payload.consul_tags == tags

    def test_error_message_under_max_length(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test error message under 2000 chars is accepted."""
        error_msg = "x" * 1999
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            consul_applied=False,
            postgres_error=error_msg,
            consul_error=error_msg,
            correlation_id=correlation_id,
        )
        assert outcome.postgres_error == error_msg
        assert len(outcome.postgres_error) == 1999
        assert outcome.consul_error == error_msg
        assert len(outcome.consul_error) == 1999

    def test_error_message_at_max_length(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test error message exactly at 2000 chars is accepted."""
        error_msg = "x" * 2000
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            consul_applied=False,
            postgres_error=error_msg,
            consul_error=error_msg,
            correlation_id=correlation_id,
        )
        assert outcome.postgres_error == error_msg
        assert len(outcome.postgres_error) == 2000
        assert outcome.consul_error == error_msg
        assert len(outcome.consul_error) == 2000

    def test_postgres_error_over_max_length_rejected(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test postgres_error over 2000 chars raises ValidationError."""
        error_msg = "x" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="failed",
                postgres_applied=False,
                consul_applied=True,
                postgres_error=error_msg,
                correlation_id=correlation_id,
            )
        assert "postgres_error" in str(exc_info.value)

    def test_consul_error_over_max_length_rejected(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test consul_error over 2000 chars raises ValidationError."""
        error_msg = "x" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="failed",
                postgres_applied=True,
                consul_applied=False,
                consul_error=error_msg,
                correlation_id=correlation_id,
            )
        assert "consul_error" in str(exc_info.value)

    def test_outcome_all_status_values(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test all valid status values with correct applied flags."""
        # Success: both operations succeeded
        success = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="success",
            postgres_applied=True,
            consul_applied=True,
            correlation_id=correlation_id,
        )
        assert success.status == "success"

        # Partial: one succeeded, one failed
        partial = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            consul_applied=False,
            correlation_id=correlation_id,
        )
        assert partial.status == "partial"

        # Failed: both operations failed
        failed = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            consul_applied=False,
            correlation_id=correlation_id,
        )
        assert failed.status == "failed"
