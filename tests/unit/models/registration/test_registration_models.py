# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
- TestStatusConsistencyValidation: Status field consistency tests
- TestEdgeCases: Edge cases and boundary conditions
"""

import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

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
def simple_record() -> ModelRegistrationRecordBase:
    """Provide a minimal registration record."""

    class _SimpleRecord(ModelRegistrationRecordBase):
        node_id: str
        node_type: str

    return _SimpleRecord(node_id="node-123", node_type="compute")


@pytest.fixture
def basic_payload(
    node_id: UUID,
    deployment_id: UUID,
    simple_record: ModelRegistrationRecordBase,
) -> ModelRegistrationPayload:
    """Provide a standard ModelRegistrationPayload."""
    return ModelRegistrationPayload(
        node_id=node_id,
        deployment_id=deployment_id,
        environment="production",
        network_id="vpc-main",
        postgres_record=simple_record,
    )


@pytest.fixture
def success_outcome(
    node_id: UUID, correlation_id: UUID
) -> ModelDualRegistrationOutcome:
    """Provide a successful ModelDualRegistrationOutcome."""
    return ModelDualRegistrationOutcome(
        node_id=node_id,
        status="success",
        postgres_applied=True,
        correlation_id=correlation_id,
    )


# ---- TestModelRegistrationPayload ----


@pytest.mark.unit
class TestModelRegistrationPayload:
    """Tests for ModelRegistrationPayload construction and validation."""

    def test_basic_construction(self, basic_payload: ModelRegistrationPayload) -> None:
        """Test that a valid payload constructs without error."""
        assert basic_payload.environment == "production"
        assert basic_payload.network_id == "vpc-main"

    def test_fields_present(
        self,
        node_id: UUID,
        deployment_id: UUID,
        simple_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test all fields are accessible."""
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment="staging",
            network_id="internal",
            postgres_record=simple_record,
        )
        assert payload.node_id == node_id
        assert payload.deployment_id == deployment_id
        assert payload.environment == "staging"
        assert payload.network_id == "internal"
        assert payload.postgres_record == simple_record

    def test_environment_min_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        simple_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test environment min_length=1 validation."""
        with pytest.raises(ValidationError):
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="",
                network_id="vpc",
                postgres_record=simple_record,
            )

    def test_network_id_min_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        simple_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test network_id min_length=1 validation."""
        with pytest.raises(ValidationError):
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="production",
                network_id="",
                postgres_record=simple_record,
            )

    def test_immutability(self, basic_payload: ModelRegistrationPayload) -> None:
        """Test that payload is frozen (immutable)."""
        with pytest.raises(Exception):
            basic_payload.environment = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(
        self,
        node_id: UUID,
        deployment_id: UUID,
        simple_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelRegistrationPayload(
                node_id=node_id,
                deployment_id=deployment_id,
                environment="production",
                network_id="vpc",
                postgres_record=simple_record,
                unknown_field="value",  # type: ignore[call-arg]
            )


# ---- TestModelDualRegistrationOutcome ----


@pytest.mark.unit
class TestModelDualRegistrationOutcome:
    """Tests for ModelDualRegistrationOutcome construction."""

    def test_success_outcome(
        self, success_outcome: ModelDualRegistrationOutcome
    ) -> None:
        """Test a successful outcome."""
        assert success_outcome.status == "success"
        assert success_outcome.postgres_applied is True
        assert success_outcome.postgres_error is None

    def test_failed_outcome(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test a failed outcome."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            postgres_error="Connection refused",
            correlation_id=correlation_id,
        )
        assert outcome.status == "failed"
        assert outcome.postgres_applied is False
        assert outcome.postgres_error == "Connection refused"

    def test_partial_outcome(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test a partial outcome (postgres succeeded but overall partial)."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            correlation_id=correlation_id,
        )
        assert outcome.status == "partial"

    def test_default_error_fields(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test default values for optional error fields."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="success",
            postgres_applied=True,
            correlation_id=correlation_id,
        )
        assert outcome.postgres_error is None

    def test_immutability(self, success_outcome: ModelDualRegistrationOutcome) -> None:
        """Test that outcome is frozen."""
        with pytest.raises(Exception):
            success_outcome.status = "failed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=True,
                correlation_id=correlation_id,
                unknown_field="value",  # type: ignore[call-arg]
            )


# ---- TestStatusConsistencyValidation ----


@pytest.mark.unit
class TestStatusConsistencyValidation:
    """Tests for the status_consistency model_validator."""

    def test_success_requires_postgres_applied_true(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """status='success' with postgres_applied=False should raise."""
        with pytest.raises(ValidationError):
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="success",
                postgres_applied=False,
                correlation_id=correlation_id,
            )

    def test_failed_requires_postgres_applied_false(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """status='failed' with postgres_applied=True should raise."""
        with pytest.raises(ValidationError):
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="failed",
                postgres_applied=True,
                correlation_id=correlation_id,
            )

    def test_partial_postgres_succeeded(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """status='partial' with postgres_applied=True is valid."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            correlation_id=correlation_id,
        )
        assert outcome.status == "partial"

    def test_partial_postgres_failed(self, node_id: UUID, correlation_id: UUID) -> None:
        """status='partial' with postgres_applied=False is valid."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=False,
            postgres_error="Some error",
            correlation_id=correlation_id,
        )
        assert outcome.status == "partial"

    def test_failed_status_requires_both_operations_failed(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Confirm status='failed' with postgres_applied=False is valid."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            postgres_error="Timeout",
            correlation_id=correlation_id,
        )
        assert outcome.status == "failed"


# ---- TestSerializationRoundtrip ----


@pytest.mark.unit
class TestSerializationRoundtrip:
    """Tests for JSON serialization and deserialization."""

    def test_payload_roundtrip_serialization(
        self, basic_payload: ModelRegistrationPayload
    ) -> None:
        """Test that payload can be serialized and deserialized."""
        json_str = basic_payload.model_dump_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["environment"] == "production"
        assert data["network_id"] == "vpc-main"

    def test_outcome_roundtrip_serialization(
        self, success_outcome: ModelDualRegistrationOutcome
    ) -> None:
        """Test that outcome can be serialized."""
        json_str = success_outcome.model_dump_json()
        data = json.loads(json_str)
        assert data["status"] == "success"
        assert data["postgres_applied"] is True
        assert data["postgres_error"] is None


# ---- TestONEXPatterns ----


@pytest.mark.unit
class TestONEXPatterns:
    """Tests for ONEX-specific pattern compliance."""

    def test_payload_model_config_frozen(self) -> None:
        """Test payload model is frozen."""
        assert ModelRegistrationPayload.model_config.get("frozen") is True

    def test_payload_model_config_extra_forbid(self) -> None:
        """Test payload model forbids extra fields."""
        assert ModelRegistrationPayload.model_config.get("extra") == "forbid"

    def test_payload_model_config_from_attributes(self) -> None:
        """Test payload model has from_attributes=True."""
        assert ModelRegistrationPayload.model_config.get("from_attributes") is True

    def test_outcome_model_config_frozen(self) -> None:
        """Test outcome model is frozen."""
        assert ModelDualRegistrationOutcome.model_config.get("frozen") is True

    def test_outcome_model_config_extra_forbid(self) -> None:
        """Test outcome model forbids extra fields."""
        assert ModelDualRegistrationOutcome.model_config.get("extra") == "forbid"

    def test_payload_from_attributes_construction(
        self,
        node_id: UUID,
        deployment_id: UUID,
        simple_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test from_attributes allows ORM-like construction."""
        nid = node_id
        did = deployment_id
        rec = simple_record

        class FakeOrm:
            environment = "production"
            network_id = "vpc"

            def __init__(self) -> None:
                self.node_id = nid
                self.deployment_id = did
                self.postgres_record = rec

        payload = ModelRegistrationPayload.model_validate(
            FakeOrm(), from_attributes=True
        )
        assert payload.node_id == node_id
        assert payload.environment == "production"


# ---- TestEdgeCases ----


@pytest.mark.unit
class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_environment_at_max_length(
        self,
        node_id: UUID,
        deployment_id: UUID,
        simple_record: ModelRegistrationRecordBase,
    ) -> None:
        """Test environment at maximum allowed length (100 chars)."""
        max_env = "x" * 100
        payload = ModelRegistrationPayload(
            node_id=node_id,
            deployment_id=deployment_id,
            environment=max_env,
            network_id="vpc",
            postgres_record=simple_record,
        )
        assert len(payload.environment) == 100

    def test_error_message_at_max_length(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test postgres_error at maximum allowed length (2000 chars)."""
        long_error = "e" * 2000
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            postgres_error=long_error,
            correlation_id=correlation_id,
        )
        assert len(outcome.postgres_error) == 2000  # type: ignore[arg-type]

    def test_error_message_under_max_length(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test postgres_error under maximum length is accepted."""
        outcome = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            postgres_error="short error",
            correlation_id=correlation_id,
        )
        assert outcome.postgres_error == "short error"

    def test_outcome_all_status_values(
        self, node_id: UUID, correlation_id: UUID
    ) -> None:
        """Test all valid status values can be constructed."""
        success = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="success",
            postgres_applied=True,
            correlation_id=correlation_id,
        )
        failed = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="failed",
            postgres_applied=False,
            correlation_id=correlation_id,
        )
        partial = ModelDualRegistrationOutcome(
            node_id=node_id,
            status="partial",
            postgres_applied=True,
            correlation_id=correlation_id,
        )
        assert success.status == "success"
        assert failed.status == "failed"
        assert partial.status == "partial"

    def test_invalid_status_raises(self, node_id: UUID, correlation_id: UUID) -> None:
        """Test invalid status value raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelDualRegistrationOutcome(
                node_id=node_id,
                status="unknown",  # type: ignore[arg-type]
                postgres_applied=True,
                correlation_id=correlation_id,
            )
