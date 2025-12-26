# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for context models.

Tests all context model functionality including:
- Basic instantiation
- Frozen behavior (immutability)
- from_attributes behavior
- JSON serialization/deserialization
- Field validation
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import (
    ModelOperationalContext,
    ModelResourceContext,
    ModelRetryContext,
    ModelTraceContext,
    ModelUserContext,
    ModelValidationContext,
)


@pytest.mark.unit
class TestModelTraceContext:
    """Tests for ModelTraceContext."""

    def test_basic_instantiation(self) -> None:
        """Test basic creation with all fields."""
        trace_id = uuid4()
        span_id = uuid4()
        correlation_id = uuid4()

        context = ModelTraceContext(
            trace_id=trace_id,
            span_id=span_id,
            correlation_id=correlation_id,
        )

        assert context.trace_id == trace_id
        assert context.span_id == span_id
        assert context.correlation_id == correlation_id

    def test_default_values(self) -> None:
        """Test that all fields default to None."""
        context = ModelTraceContext()

        assert context.trace_id is None
        assert context.span_id is None
        assert context.correlation_id is None

    def test_partial_instantiation(self) -> None:
        """Test creation with only some fields."""
        trace_id = uuid4()
        context = ModelTraceContext(trace_id=trace_id)

        assert context.trace_id == trace_id
        assert context.span_id is None
        assert context.correlation_id is None

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelTraceContext(trace_id=uuid4())

        with pytest.raises(ValidationError):
            context.trace_id = uuid4()  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            ModelTraceContext(trace_id=uuid4(), extra_field="not_allowed")  # type: ignore[call-arg]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        trace_id = uuid4()
        context = ModelTraceContext(trace_id=trace_id)

        json_data = context.model_dump()
        assert json_data["trace_id"] == trace_id
        assert json_data["span_id"] is None

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization."""
        trace_id = uuid4()
        json_data = {"trace_id": str(trace_id), "span_id": None, "correlation_id": None}

        context = ModelTraceContext.model_validate(json_data)
        assert context.trace_id == trace_id

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelTraceContext(
            trace_id=uuid4(),
            span_id=uuid4(),
            correlation_id=uuid4(),
        )

        json_str = original.model_dump_json()
        restored = ModelTraceContext.model_validate_json(json_str)

        assert restored == original

    def test_from_attributes(self) -> None:
        """Test from_attributes behavior for ORM-like access."""

        class MockORMObject:
            def __init__(self) -> None:
                self.trace_id = uuid4()
                self.span_id = uuid4()
                self.correlation_id = None

        mock_obj = MockORMObject()
        context = ModelTraceContext.model_validate(mock_obj)

        assert context.trace_id == mock_obj.trace_id
        assert context.span_id == mock_obj.span_id
        assert context.correlation_id is None


@pytest.mark.unit
class TestModelOperationalContext:
    """Tests for ModelOperationalContext."""

    def test_basic_instantiation(self) -> None:
        """Test basic creation with all fields."""
        operation_id = uuid4()

        context = ModelOperationalContext(
            operation_id=operation_id,
            operation_name="create_user",
            timeout_ms=5000,
        )

        assert context.operation_id == operation_id
        assert context.operation_name == "create_user"
        assert context.timeout_ms == 5000

    def test_default_values(self) -> None:
        """Test that all fields default to None."""
        context = ModelOperationalContext()

        assert context.operation_id is None
        assert context.operation_name is None
        assert context.timeout_ms is None

    def test_timeout_validation(self) -> None:
        """Test timeout_ms validation (must be >= 0)."""
        # Valid timeout
        context = ModelOperationalContext(timeout_ms=0)
        assert context.timeout_ms == 0

        # Invalid timeout (negative)
        with pytest.raises(ValidationError):
            ModelOperationalContext(timeout_ms=-1)

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelOperationalContext(operation_name="test")

        with pytest.raises(ValidationError):
            context.operation_name = "changed"  # type: ignore[misc]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        context = ModelOperationalContext(
            operation_name="validate_input",
            timeout_ms=1000,
        )

        json_data = context.model_dump()
        assert json_data["operation_name"] == "validate_input"
        assert json_data["timeout_ms"] == 1000

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelOperationalContext(
            operation_id=uuid4(),
            operation_name="process",
            timeout_ms=3000,
        )

        json_str = original.model_dump_json()
        restored = ModelOperationalContext.model_validate_json(json_str)

        assert restored == original


@pytest.mark.unit
class TestModelRetryContext:
    """Tests for ModelRetryContext."""

    def test_basic_instantiation(self) -> None:
        """Test basic creation with all fields."""
        next_retry = datetime.now(UTC) + timedelta(seconds=30)

        context = ModelRetryContext(
            attempt=2,
            retryable=True,
            next_retry_at=next_retry,
        )

        assert context.attempt == 2
        assert context.retryable is True
        assert context.next_retry_at == next_retry

    def test_default_values(self) -> None:
        """Test default values."""
        context = ModelRetryContext()

        assert context.attempt == 1
        assert context.retryable is True
        assert context.next_retry_at is None

    def test_attempt_validation(self) -> None:
        """Test attempt validation (must be >= 1)."""
        # Valid attempt
        context = ModelRetryContext(attempt=1)
        assert context.attempt == 1

        # Invalid attempt (zero)
        with pytest.raises(ValidationError):
            ModelRetryContext(attempt=0)

        # Invalid attempt (negative)
        with pytest.raises(ValidationError):
            ModelRetryContext(attempt=-1)

    def test_non_retryable_context(self) -> None:
        """Test non-retryable context."""
        context = ModelRetryContext(
            attempt=1,
            retryable=False,
        )

        assert context.retryable is False

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelRetryContext(attempt=1)

        with pytest.raises(ValidationError):
            context.attempt = 2  # type: ignore[misc]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        next_retry = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        context = ModelRetryContext(
            attempt=3,
            retryable=True,
            next_retry_at=next_retry,
        )

        json_data = context.model_dump()
        assert json_data["attempt"] == 3
        assert json_data["retryable"] is True

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelRetryContext(
            attempt=5,
            retryable=False,
            next_retry_at=datetime.now(UTC),
        )

        json_str = original.model_dump_json()
        restored = ModelRetryContext.model_validate_json(json_str)

        assert restored.attempt == original.attempt
        assert restored.retryable == original.retryable


@pytest.mark.unit
class TestModelResourceContext:
    """Tests for ModelResourceContext."""

    def test_basic_instantiation(self) -> None:
        """Test basic creation with all fields."""
        resource_id = uuid4()
        context = ModelResourceContext(
            resource_id=resource_id,
            resource_type="document",
            namespace="workspace/engineering",
        )

        assert context.resource_id == resource_id
        assert context.resource_type == "document"
        assert context.namespace == "workspace/engineering"

    def test_default_values(self) -> None:
        """Test that all fields default to None."""
        context = ModelResourceContext()

        assert context.resource_id is None
        assert context.resource_type is None
        assert context.namespace is None

    def test_partial_instantiation(self) -> None:
        """Test creation with only some fields."""
        resource_id = uuid4()
        context = ModelResourceContext(
            resource_id=resource_id,
            resource_type="user",
        )

        assert context.resource_id == resource_id
        assert context.resource_type == "user"
        assert context.namespace is None

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelResourceContext(resource_id=uuid4())

        with pytest.raises(ValidationError):
            context.resource_id = uuid4()  # type: ignore[misc]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        resource_id = uuid4()
        context = ModelResourceContext(
            resource_id=resource_id,
            resource_type="item",
            namespace="production",
        )

        json_data = context.model_dump()
        assert json_data["resource_id"] == resource_id
        assert json_data["resource_type"] == "item"
        assert json_data["namespace"] == "production"

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelResourceContext(
            resource_id=uuid4(),
            resource_type="configuration",
            namespace="global",
        )

        json_str = original.model_dump_json()
        restored = ModelResourceContext.model_validate_json(json_str)

        assert restored == original


@pytest.mark.unit
class TestModelUserContext:
    """Tests for ModelUserContext."""

    def test_basic_instantiation(self) -> None:
        """Test basic creation with all fields."""
        user_id = uuid4()
        session_id = uuid4()
        tenant_id = uuid4()

        context = ModelUserContext(
            user_id=user_id,
            session_id=session_id,
            tenant_id=tenant_id,
        )

        assert context.user_id == user_id
        assert context.session_id == session_id
        assert context.tenant_id == tenant_id

    def test_default_values(self) -> None:
        """Test that all fields default to None."""
        context = ModelUserContext()

        assert context.user_id is None
        assert context.session_id is None
        assert context.tenant_id is None

    def test_anonymous_session(self) -> None:
        """Test anonymous session without user_id."""
        session_id = uuid4()
        tenant_id = uuid4()
        context = ModelUserContext(
            session_id=session_id,
            tenant_id=tenant_id,
        )

        assert context.user_id is None
        assert context.session_id == session_id
        assert context.tenant_id == tenant_id

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelUserContext(tenant_id=uuid4())

        with pytest.raises(ValidationError):
            context.tenant_id = uuid4()  # type: ignore[misc]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        user_id = uuid4()
        tenant_id = uuid4()
        context = ModelUserContext(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        json_data = context.model_dump()
        assert json_data["user_id"] == user_id
        assert json_data["tenant_id"] == tenant_id

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelUserContext(
            user_id=uuid4(),
            session_id=uuid4(),
            tenant_id=uuid4(),
        )

        json_str = original.model_dump_json()
        restored = ModelUserContext.model_validate_json(json_str)

        assert restored == original


@pytest.mark.unit
class TestModelValidationContext:
    """Tests for ModelValidationContext."""

    def test_basic_instantiation(self) -> None:
        """Test basic creation with all fields."""
        context = ModelValidationContext(
            field_name="email",
            expected="valid email format",
            actual="not-an-email",
        )

        assert context.field_name == "email"
        assert context.expected == "valid email format"
        assert context.actual == "not-an-email"

    def test_default_values(self) -> None:
        """Test that all fields default to None."""
        context = ModelValidationContext()

        assert context.field_name is None
        assert context.expected is None
        assert context.actual is None

    def test_type_mismatch_context(self) -> None:
        """Test validation context for type mismatch."""
        context = ModelValidationContext(
            field_name="age",
            expected="integer >= 0",
            actual="-5",
        )

        assert context.field_name == "age"
        assert context.expected == "integer >= 0"
        assert context.actual == "-5"

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelValidationContext(field_name="test")

        with pytest.raises(ValidationError):
            context.field_name = "changed"  # type: ignore[misc]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        context = ModelValidationContext(
            field_name="username",
            expected="3-20 alphanumeric characters",
            actual="ab",
        )

        json_data = context.model_dump()
        assert json_data["field_name"] == "username"
        assert json_data["expected"] == "3-20 alphanumeric characters"
        assert json_data["actual"] == "ab"

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelValidationContext(
            field_name="password",
            expected="minimum 8 characters",
            actual="short",
        )

        json_str = original.model_dump_json()
        restored = ModelValidationContext.model_validate_json(json_str)

        assert restored == original


@pytest.mark.unit
class TestContextModelsIntegration:
    """Integration tests for context models."""

    def test_all_models_have_frozen_config(self) -> None:
        """Verify all context models are frozen."""
        models = [
            ModelTraceContext,
            ModelOperationalContext,
            ModelRetryContext,
            ModelResourceContext,
            ModelUserContext,
            ModelValidationContext,
        ]

        for model in models:
            config = model.model_config
            assert config.get("frozen") is True, f"{model.__name__} should be frozen"

    def test_all_models_have_from_attributes(self) -> None:
        """Verify all context models have from_attributes=True."""
        models = [
            ModelTraceContext,
            ModelOperationalContext,
            ModelRetryContext,
            ModelResourceContext,
            ModelUserContext,
            ModelValidationContext,
        ]

        for model in models:
            config = model.model_config
            assert config.get("from_attributes") is True, (
                f"{model.__name__} should have from_attributes=True"
            )

    def test_all_models_forbid_extra(self) -> None:
        """Verify all context models forbid extra fields."""
        models = [
            ModelTraceContext,
            ModelOperationalContext,
            ModelRetryContext,
            ModelResourceContext,
            ModelUserContext,
            ModelValidationContext,
        ]

        for model in models:
            config = model.model_config
            assert config.get("extra") == "forbid", (
                f"{model.__name__} should forbid extra fields"
            )

    def test_models_can_be_used_as_dict_values(self) -> None:
        """Test that context models can be stored in dictionaries."""
        resource_id = uuid4()
        tenant_id = uuid4()
        contexts = {
            "trace": ModelTraceContext(trace_id=uuid4()),
            "operation": ModelOperationalContext(operation_name="test"),
            "retry": ModelRetryContext(attempt=1),
            "resource": ModelResourceContext(resource_id=resource_id),
            "user": ModelUserContext(tenant_id=tenant_id),
            "validation": ModelValidationContext(field_name="email"),
        }

        # All should be accessible
        assert contexts["trace"].trace_id is not None
        assert contexts["operation"].operation_name == "test"
        assert contexts["retry"].attempt == 1
        assert contexts["resource"].resource_id == resource_id
        assert contexts["user"].tenant_id == tenant_id
        assert contexts["validation"].field_name == "email"

    def test_models_equality(self) -> None:
        """Test that equal models compare as equal."""
        trace_id = uuid4()

        ctx1 = ModelTraceContext(trace_id=trace_id)
        ctx2 = ModelTraceContext(trace_id=trace_id)

        assert ctx1 == ctx2

    def test_models_hash(self) -> None:
        """Test that frozen models are hashable."""
        trace_id = uuid4()
        ctx = ModelTraceContext(trace_id=trace_id)

        # Should be hashable
        hash_value = hash(ctx)
        assert isinstance(hash_value, int)

        # Same content should have same hash
        ctx2 = ModelTraceContext(trace_id=trace_id)
        assert hash(ctx) == hash(ctx2)
