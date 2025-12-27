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

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import (
    EnumAuthenticationMethod,
    EnumCheckpointType,
    EnumLikelihood,
    EnumTokenType,
    EnumTriggerEvent,
)
from omnibase_core.models.context import (
    ModelAuditMetadata,
    ModelAuthorizationContext,
    ModelCheckpointMetadata,
    ModelDetectionMetadata,
    ModelHttpRequestMetadata,
    ModelNodeInitMetadata,
    ModelOperationalContext,
    ModelResourceContext,
    ModelRetryContext,
    ModelSessionContext,
    ModelTraceContext,
    ModelUserContext,
    ModelValidationContext,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Helper classes for from_attributes testing (Metadata models)
# =============================================================================


@dataclass
class SessionContextAttrs:
    """Helper dataclass for testing from_attributes on ModelSessionContext."""

    session_id: UUID | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    device_fingerprint: str | None = None
    locale: str | None = None
    authentication_method: str | None = None


@dataclass
class HttpRequestMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelHttpRequestMetadata."""

    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    content_type: str | None = None
    accept: str | None = None


@dataclass
class AuthorizationContextAttrs:
    """Helper dataclass for testing from_attributes on ModelAuthorizationContext.

    Note: roles, permissions, and scopes must be lists (not None) because
    ModelAuthorizationContext uses default_factory=list without Optional.
    """

    roles: list[str] | None = None
    permissions: list[str] | None = None
    scopes: list[str] | None = None
    token_type: str | None = None
    expiry: str | None = None
    client_id: str | None = None

    def __post_init__(self) -> None:
        """Convert None to empty lists for list fields."""
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.scopes is None:
            self.scopes = []


@dataclass
class AuditMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelAuditMetadata."""

    audit_id: str | None = None
    auditor: str | None = None
    audit_category: str | None = None
    retention_period: str | None = None
    compliance_tag: str | None = None


@dataclass
class CheckpointMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelCheckpointMetadata."""

    checkpoint_type: str | None = None
    source_node: str | None = None
    trigger_event: str | None = None
    workflow_stage: str | None = None
    parent_checkpoint_id: str | None = None


@dataclass
class DetectionMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelDetectionMetadata."""

    pattern_category: str | None = None
    detection_source: str | None = None
    rule_version: str | None = None
    false_positive_likelihood: str | None = None
    remediation_hint: str | None = None


@dataclass
class NodeInitMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelNodeInitMetadata."""

    init_source: str | None = None
    init_timestamp: str | None = None
    config_hash: str | None = None
    dependency_versions: str | None = None
    feature_flags: str | None = None


# =============================================================================
# Error/Retry Context Model Tests
# =============================================================================


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

    def test_required_field(self) -> None:
        """Test that trace_id is required."""
        with pytest.raises(ValidationError):
            ModelTraceContext()  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelTraceContext(trace_id=uuid4())

        assert context.trace_id is not None
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

    def test_required_field(self) -> None:
        """Test that operation_name is required."""
        with pytest.raises(ValidationError):
            ModelOperationalContext()  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelOperationalContext(operation_name="test")

        assert context.operation_name == "test"
        assert context.operation_id is None
        assert context.timeout_ms is None

    def test_timeout_validation(self) -> None:
        """Test timeout_ms validation (must be >= 0)."""
        # Valid timeout
        context = ModelOperationalContext(operation_name="test", timeout_ms=0)
        assert context.timeout_ms == 0

        # Invalid timeout (negative)
        with pytest.raises(ValidationError):
            ModelOperationalContext(operation_name="test", timeout_ms=-1)

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

    def test_next_retry_at_accepts_past_datetime(self) -> None:
        """Test that next_retry_at accepts past datetime values.

        This is intentional behavior to support:
        - Historical tracking of missed retry windows
        - Recording when a retry was originally scheduled
        - Testing scenarios with deterministic timestamps

        No future-time validation is enforced because the field
        documents scheduling intent, not current validity.
        """
        past_time = datetime.now(UTC) - timedelta(hours=1)

        # Should not raise - past times are valid
        context = ModelRetryContext(
            attempt=2,
            retryable=True,
            next_retry_at=past_time,
        )

        assert context.next_retry_at == past_time
        assert context.attempt == 2
        assert context.retryable is True


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

    def test_required_field(self) -> None:
        """Test that resource_id is required."""
        with pytest.raises(ValidationError):
            ModelResourceContext()  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelResourceContext(resource_id=uuid4())

        assert context.resource_id is not None
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

    def test_required_field(self) -> None:
        """Test that user_id is required."""
        with pytest.raises(ValidationError):
            ModelUserContext()  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelUserContext(user_id=uuid4())

        assert context.user_id is not None
        assert context.session_id is None
        assert context.tenant_id is None

    def test_minimal_user_context(self) -> None:
        """Test minimal user context with only user_id."""
        user_id = uuid4()
        context = ModelUserContext(user_id=user_id)

        assert context.user_id == user_id
        assert context.session_id is None
        assert context.tenant_id is None

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable (frozen)."""
        context = ModelUserContext(user_id=uuid4(), tenant_id=uuid4())

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

    def test_required_field(self) -> None:
        """Test that field_name is required."""
        with pytest.raises(ValidationError):
            ModelValidationContext()  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelValidationContext(field_name="test")

        assert context.field_name == "test"
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


# =============================================================================
# Metadata Context Model Tests
# =============================================================================


@pytest.mark.unit
class TestModelSessionContextInstantiation:
    """Tests for ModelSessionContext instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating session context with all fields populated."""
        test_session_id = uuid4()
        context = ModelSessionContext(
            session_id=test_session_id,
            client_ip="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint="fp_xyz789",
            locale="en-US",
            authentication_method="oauth2",
        )
        assert context.session_id == test_session_id
        assert context.client_ip == "192.168.1.100"
        assert context.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        assert context.device_fingerprint == "fp_xyz789"
        assert context.locale == "en-US"
        assert context.authentication_method == EnumAuthenticationMethod.OAUTH2

    def test_create_with_partial_fields(self) -> None:
        """Test creating session context with partial fields."""
        test_session_id = uuid4()
        context = ModelSessionContext(
            session_id=test_session_id,
            locale="fr-FR",
        )
        assert context.session_id == test_session_id
        assert context.locale == "fr-FR"
        assert context.client_ip is None
        assert context.user_agent is None


@pytest.mark.unit
class TestModelSessionContextDefaults:
    """Tests for ModelSessionContext default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        context = ModelSessionContext()
        assert context.session_id is None
        assert context.client_ip is None
        assert context.user_agent is None
        assert context.device_fingerprint is None
        assert context.locale is None
        assert context.authentication_method is None


@pytest.mark.unit
class TestModelSessionContextImmutability:
    """Tests for ModelSessionContext immutability (frozen=True)."""

    def test_cannot_modify_session_id(self) -> None:
        """Test that session_id cannot be modified after creation."""
        test_session_id = uuid4()
        context = ModelSessionContext(session_id=test_session_id)
        with pytest.raises(ValidationError):
            context.session_id = uuid4()

    def test_cannot_modify_client_ip(self) -> None:
        """Test that client_ip cannot be modified after creation."""
        context = ModelSessionContext(client_ip="192.168.1.1")
        with pytest.raises(ValidationError):
            context.client_ip = "10.0.0.1"

    def test_cannot_modify_locale(self) -> None:
        """Test that locale cannot be modified after creation."""
        context = ModelSessionContext(locale="en-US")
        with pytest.raises(ValidationError):
            context.locale = "de-DE"


@pytest.mark.unit
class TestModelSessionContextFromAttributes:
    """Tests for ModelSessionContext from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelSessionContext from an object with attributes."""
        test_session_id = uuid4()
        attrs = SessionContextAttrs(
            session_id=test_session_id,
            client_ip="10.0.0.1",
            locale="ja-JP",
        )
        context = ModelSessionContext.model_validate(attrs)
        assert context.session_id == test_session_id
        assert context.client_ip == "10.0.0.1"
        assert context.locale == "ja-JP"

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        test_session_id = uuid4()
        attrs = SessionContextAttrs(
            session_id=test_session_id,
            client_ip="172.16.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="fp_test",
            locale="es-ES",
            authentication_method="saml",
        )
        context = ModelSessionContext.model_validate(attrs)
        assert context.session_id == test_session_id
        assert context.authentication_method == EnumAuthenticationMethod.SAML


@pytest.mark.unit
class TestModelSessionContextExtraForbid:
    """Tests for ModelSessionContext extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSessionContext(
                session_id=uuid4(),
                unknown_field="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelHttpRequestMetadataInstantiation:
    """Tests for ModelHttpRequestMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating HTTP request metadata with all fields populated."""
        metadata = ModelHttpRequestMetadata(
            request_id="req_xyz789",
            method="POST",
            path="/api/v1/nodes/execute",
            content_type="application/json",
            accept="application/json",
        )
        assert metadata.request_id == "req_xyz789"
        assert metadata.method == "POST"
        assert metadata.path == "/api/v1/nodes/execute"
        assert metadata.content_type == "application/json"
        assert metadata.accept == "application/json"

    def test_create_with_partial_fields(self) -> None:
        """Test creating HTTP request metadata with partial fields."""
        metadata = ModelHttpRequestMetadata(
            method="GET",
            path="/api/health",
        )
        assert metadata.method == "GET"
        assert metadata.path == "/api/health"
        assert metadata.request_id is None
        assert metadata.content_type is None


@pytest.mark.unit
class TestModelHttpRequestMetadataDefaults:
    """Tests for ModelHttpRequestMetadata default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        metadata = ModelHttpRequestMetadata()
        assert metadata.request_id is None
        assert metadata.method is None
        assert metadata.path is None
        assert metadata.content_type is None
        assert metadata.accept is None


@pytest.mark.unit
class TestModelHttpRequestMetadataImmutability:
    """Tests for ModelHttpRequestMetadata immutability (frozen=True)."""

    def test_cannot_modify_method(self) -> None:
        """Test that method cannot be modified after creation."""
        metadata = ModelHttpRequestMetadata(method="GET")
        with pytest.raises(ValidationError):
            metadata.method = "POST"

    def test_cannot_modify_path(self) -> None:
        """Test that path cannot be modified after creation."""
        metadata = ModelHttpRequestMetadata(path="/original")
        with pytest.raises(ValidationError):
            metadata.path = "/modified"


@pytest.mark.unit
class TestModelHttpRequestMetadataFromAttributes:
    """Tests for ModelHttpRequestMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelHttpRequestMetadata from an object with attributes."""
        attrs = HttpRequestMetadataAttrs(
            request_id="req_from_attrs",
            method="PUT",
            path="/api/v1/update",
        )
        metadata = ModelHttpRequestMetadata.model_validate(attrs)
        assert metadata.request_id == "req_from_attrs"
        assert metadata.method == "PUT"
        assert metadata.path == "/api/v1/update"


@pytest.mark.unit
class TestModelHttpRequestMetadataExtraForbid:
    """Tests for ModelHttpRequestMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHttpRequestMetadata(
                method="GET",
                extra_header="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelAuthorizationContextInstantiation:
    """Tests for ModelAuthorizationContext instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating authorization context with all fields populated."""
        context = ModelAuthorizationContext(
            roles=["admin", "operator"],
            permissions=["read:nodes", "write:nodes", "execute:workflows"],
            scopes=["openid", "profile", "api:full"],
            token_type="Bearer",
            expiry="2025-01-15T12:00:00Z",
            client_id="client_app_123",
        )
        assert context.roles == ["admin", "operator"]
        assert context.permissions == ["read:nodes", "write:nodes", "execute:workflows"]
        assert context.scopes == ["openid", "profile", "api:full"]
        # token_type is now normalized to EnumTokenType
        assert context.token_type == EnumTokenType.BEARER
        assert context.expiry == "2025-01-15T12:00:00Z"
        assert context.client_id == "client_app_123"

    def test_create_with_partial_fields(self) -> None:
        """Test creating authorization context with partial fields."""
        context = ModelAuthorizationContext(
            roles=["user"],
            token_type="Bearer",
        )
        assert context.roles == ["user"]
        # token_type is now normalized to EnumTokenType
        assert context.token_type == EnumTokenType.BEARER
        assert context.permissions == []
        assert context.scopes == []

    def test_admin_role_check(self) -> None:
        """Test checking if admin role is present."""
        context = ModelAuthorizationContext(
            roles=["admin", "operator"],
        )
        assert "admin" in context.roles


@pytest.mark.unit
class TestModelAuthorizationContextDefaults:
    """Tests for ModelAuthorizationContext default values."""

    def test_list_fields_default_to_empty_list(self) -> None:
        """Test that list fields default to empty lists."""
        context = ModelAuthorizationContext()
        assert context.roles == []
        assert context.permissions == []
        assert context.scopes == []

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelAuthorizationContext()
        assert context.token_type is None
        assert context.expiry is None
        assert context.client_id is None


@pytest.mark.unit
class TestModelAuthorizationContextImmutability:
    """Tests for ModelAuthorizationContext immutability (frozen=True)."""

    def test_cannot_modify_roles(self) -> None:
        """Test that roles cannot be modified after creation."""
        context = ModelAuthorizationContext(roles=["user"])
        with pytest.raises(ValidationError):
            context.roles = ["admin"]

    def test_cannot_modify_token_type(self) -> None:
        """Test that token_type cannot be modified after creation."""
        context = ModelAuthorizationContext(token_type="Bearer")
        with pytest.raises(ValidationError):
            context.token_type = "Basic"


@pytest.mark.unit
class TestModelAuthorizationContextFromAttributes:
    """Tests for ModelAuthorizationContext from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelAuthorizationContext from an object with attributes."""
        attrs = AuthorizationContextAttrs(
            roles=["editor"],
            permissions=["read:all"],
            token_type="api_key",
        )
        context = ModelAuthorizationContext.model_validate(attrs)
        assert context.roles == ["editor"]
        assert context.permissions == ["read:all"]
        assert context.token_type == EnumTokenType.API_KEY


@pytest.mark.unit
class TestModelAuthorizationContextExtraForbid:
    """Tests for ModelAuthorizationContext extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuthorizationContext(
                roles=["user"],
                secret_key="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelAuditMetadataInstantiation:
    """Tests for ModelAuditMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating audit metadata with all fields populated."""
        metadata = ModelAuditMetadata(
            audit_id="audit_abc123",
            auditor="service:onex-gateway",
            audit_category="security",
            retention_period="1y",
            compliance_tag="SOC2",
        )
        assert metadata.audit_id == "audit_abc123"
        assert metadata.auditor == "service:onex-gateway"
        assert metadata.audit_category == "security"
        assert metadata.retention_period == "1y"
        assert metadata.compliance_tag == "SOC2"

    def test_create_with_partial_fields(self) -> None:
        """Test creating audit metadata with partial fields."""
        metadata = ModelAuditMetadata(
            audit_category="access",
            compliance_tag="GDPR",
        )
        assert metadata.audit_category == "access"
        assert metadata.compliance_tag == "GDPR"
        assert metadata.audit_id is None


@pytest.mark.unit
class TestModelAuditMetadataDefaults:
    """Tests for ModelAuditMetadata default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        metadata = ModelAuditMetadata()
        assert metadata.audit_id is None
        assert metadata.auditor is None
        assert metadata.audit_category is None
        assert metadata.retention_period is None
        assert metadata.compliance_tag is None


@pytest.mark.unit
class TestModelAuditMetadataImmutability:
    """Tests for ModelAuditMetadata immutability (frozen=True)."""

    def test_cannot_modify_audit_id(self) -> None:
        """Test that audit_id cannot be modified after creation."""
        metadata = ModelAuditMetadata(audit_id="original")
        with pytest.raises(ValidationError):
            metadata.audit_id = "modified"

    def test_cannot_modify_compliance_tag(self) -> None:
        """Test that compliance_tag cannot be modified after creation."""
        metadata = ModelAuditMetadata(compliance_tag="SOC2")
        with pytest.raises(ValidationError):
            metadata.compliance_tag = "HIPAA"


@pytest.mark.unit
class TestModelAuditMetadataFromAttributes:
    """Tests for ModelAuditMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelAuditMetadata from an object with attributes."""
        attrs = AuditMetadataAttrs(
            audit_id="audit_from_attrs",
            auditor="user:admin",
            audit_category="data_change",
        )
        metadata = ModelAuditMetadata.model_validate(attrs)
        assert metadata.audit_id == "audit_from_attrs"
        assert metadata.auditor == "user:admin"
        assert metadata.audit_category == "data_change"


@pytest.mark.unit
class TestModelAuditMetadataExtraForbid:
    """Tests for ModelAuditMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditMetadata(
                audit_id="audit_123",
                internal_note="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelCheckpointMetadataInstantiation:
    """Tests for ModelCheckpointMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating checkpoint metadata with all fields populated."""
        parent_id = uuid4()
        metadata = ModelCheckpointMetadata(
            checkpoint_type="automatic",
            source_node="node_compute_transform",
            trigger_event="stage_complete",
            workflow_stage="processing",
            parent_checkpoint_id=parent_id,
        )
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC
        assert metadata.source_node == "node_compute_transform"
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE
        assert metadata.workflow_stage == "processing"
        assert metadata.parent_checkpoint_id == parent_id

    def test_create_with_partial_fields(self) -> None:
        """Test creating checkpoint metadata with partial fields."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type="manual",
            workflow_stage="validation",
        )
        assert metadata.checkpoint_type == "manual"
        assert metadata.workflow_stage == "validation"
        assert metadata.source_node is None


@pytest.mark.unit
class TestModelCheckpointMetadataDefaults:
    """Tests for ModelCheckpointMetadata default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        metadata = ModelCheckpointMetadata()
        assert metadata.checkpoint_type is None
        assert metadata.source_node is None
        assert metadata.trigger_event is None
        assert metadata.workflow_stage is None
        assert metadata.parent_checkpoint_id is None


@pytest.mark.unit
class TestModelCheckpointMetadataImmutability:
    """Tests for ModelCheckpointMetadata immutability (frozen=True)."""

    def test_cannot_modify_checkpoint_type(self) -> None:
        """Test that checkpoint_type cannot be modified after creation."""
        metadata = ModelCheckpointMetadata(checkpoint_type="automatic")
        with pytest.raises(ValidationError):
            metadata.checkpoint_type = "manual"

    def test_cannot_modify_workflow_stage(self) -> None:
        """Test that workflow_stage cannot be modified after creation."""
        metadata = ModelCheckpointMetadata(workflow_stage="processing")
        with pytest.raises(ValidationError):
            metadata.workflow_stage = "completion"


@pytest.mark.unit
class TestModelCheckpointMetadataFromAttributes:
    """Tests for ModelCheckpointMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelCheckpointMetadata from an object with attributes."""
        attrs = CheckpointMetadataAttrs(
            checkpoint_type="recovery",
            source_node="node_effect_io",
            trigger_event="error",
        )
        metadata = ModelCheckpointMetadata.model_validate(attrs)
        assert metadata.checkpoint_type == "recovery"
        assert metadata.source_node == "node_effect_io"
        assert metadata.trigger_event == "error"


@pytest.mark.unit
class TestModelCheckpointMetadataExtraForbid:
    """Tests for ModelCheckpointMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCheckpointMetadata(
                checkpoint_type="automatic",
                internal_state="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelDetectionMetadataInstantiation:
    """Tests for ModelDetectionMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating detection metadata with all fields populated."""
        metadata = ModelDetectionMetadata(
            pattern_category="credential_exposure",
            detection_source="regex_scanner",
            rule_version="2.1.0",
            false_positive_likelihood="low",
            remediation_hint="Rotate exposed credentials immediately",
        )
        assert metadata.pattern_category == "credential_exposure"
        assert metadata.detection_source == "regex_scanner"
        assert metadata.rule_version == ModelSemVer(major=2, minor=1, patch=0)
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW
        assert metadata.remediation_hint == "Rotate exposed credentials immediately"

    def test_create_with_partial_fields(self) -> None:
        """Test creating detection metadata with partial fields."""
        metadata = ModelDetectionMetadata(
            pattern_category="injection",
            false_positive_likelihood="medium",
        )
        assert metadata.pattern_category == "injection"
        assert metadata.false_positive_likelihood == "medium"
        assert metadata.detection_source is None


@pytest.mark.unit
class TestModelDetectionMetadataDefaults:
    """Tests for ModelDetectionMetadata default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        metadata = ModelDetectionMetadata()
        assert metadata.pattern_category is None
        assert metadata.detection_source is None
        assert metadata.rule_version is None
        assert metadata.false_positive_likelihood is None
        assert metadata.remediation_hint is None


@pytest.mark.unit
class TestModelDetectionMetadataImmutability:
    """Tests for ModelDetectionMetadata immutability (frozen=True)."""

    def test_cannot_modify_pattern_category(self) -> None:
        """Test that pattern_category cannot be modified after creation."""
        metadata = ModelDetectionMetadata(pattern_category="injection")
        with pytest.raises(ValidationError):
            metadata.pattern_category = "xss"

    def test_cannot_modify_rule_version(self) -> None:
        """Test that rule_version cannot be modified after creation."""
        metadata = ModelDetectionMetadata(rule_version="1.0.0")
        with pytest.raises(ValidationError):
            metadata.rule_version = "2.0.0"


@pytest.mark.unit
class TestModelDetectionMetadataFromAttributes:
    """Tests for ModelDetectionMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelDetectionMetadata from an object with attributes."""
        attrs = DetectionMetadataAttrs(
            pattern_category="malware",
            detection_source="ml_classifier",
            rule_version="3.0.0",
        )
        metadata = ModelDetectionMetadata.model_validate(attrs)
        assert metadata.pattern_category == "malware"
        assert metadata.detection_source == "ml_classifier"
        assert metadata.rule_version == ModelSemVer(major=3, minor=0, patch=0)


@pytest.mark.unit
class TestModelDetectionMetadataExtraForbid:
    """Tests for ModelDetectionMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDetectionMetadata(
                pattern_category="injection",
                raw_match="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelNodeInitMetadataInstantiation:
    """Tests for ModelNodeInitMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating node init metadata with all fields populated."""
        metadata = ModelNodeInitMetadata(
            init_source="container",
            init_timestamp="2025-01-15T10:30:00Z",
            config_hash="sha256:abc123def456",
            dependency_versions='{"pydantic": "2.11.0", "fastapi": "0.120.0"}',
            feature_flags="experimental_caching,async_processing",
        )
        assert metadata.init_source == "container"
        assert metadata.init_timestamp == "2025-01-15T10:30:00Z"
        assert metadata.config_hash == "sha256:abc123def456"
        assert (
            metadata.dependency_versions
            == '{"pydantic": "2.11.0", "fastapi": "0.120.0"}'
        )
        assert metadata.feature_flags == "experimental_caching,async_processing"

    def test_create_with_partial_fields(self) -> None:
        """Test creating node init metadata with partial fields."""
        metadata = ModelNodeInitMetadata(
            init_source="test_fixture",
            init_timestamp="2025-01-15T12:00:00Z",
        )
        assert metadata.init_source == "test_fixture"
        assert metadata.init_timestamp == "2025-01-15T12:00:00Z"
        assert metadata.config_hash is None


@pytest.mark.unit
class TestModelNodeInitMetadataDefaults:
    """Tests for ModelNodeInitMetadata default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        metadata = ModelNodeInitMetadata()
        assert metadata.init_source is None
        assert metadata.init_timestamp is None
        assert metadata.config_hash is None
        assert metadata.dependency_versions is None
        assert metadata.feature_flags is None


@pytest.mark.unit
class TestModelNodeInitMetadataImmutability:
    """Tests for ModelNodeInitMetadata immutability (frozen=True)."""

    def test_cannot_modify_init_source(self) -> None:
        """Test that init_source cannot be modified after creation."""
        metadata = ModelNodeInitMetadata(init_source="container")
        with pytest.raises(ValidationError):
            metadata.init_source = "manual"

    def test_cannot_modify_config_hash(self) -> None:
        """Test that config_hash cannot be modified after creation."""
        metadata = ModelNodeInitMetadata(config_hash="sha256:original")
        with pytest.raises(ValidationError):
            metadata.config_hash = "sha256:modified"


@pytest.mark.unit
class TestModelNodeInitMetadataFromAttributes:
    """Tests for ModelNodeInitMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelNodeInitMetadata from an object with attributes."""
        attrs = NodeInitMetadataAttrs(
            init_source="hot_reload",
            init_timestamp="2025-01-15T14:00:00Z",
            feature_flags="beta_feature",
        )
        metadata = ModelNodeInitMetadata.model_validate(attrs)
        assert metadata.init_source == "hot_reload"
        assert metadata.init_timestamp == "2025-01-15T14:00:00Z"
        assert metadata.feature_flags == "beta_feature"


@pytest.mark.unit
class TestModelNodeInitMetadataExtraForbid:
    """Tests for ModelNodeInitMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeInitMetadata(
                init_source="container",
                internal_state="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestContextModelsIntegration:
    """Integration tests for error/retry context models."""

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
        user_id = uuid4()
        tenant_id = uuid4()
        contexts = {
            "trace": ModelTraceContext(trace_id=uuid4()),
            "operation": ModelOperationalContext(operation_name="test"),
            "retry": ModelRetryContext(attempt=1),
            "resource": ModelResourceContext(resource_id=resource_id),
            "user": ModelUserContext(user_id=user_id, tenant_id=tenant_id),
            "validation": ModelValidationContext(field_name="email"),
        }

        # All should be accessible
        assert contexts["trace"].trace_id is not None
        assert contexts["operation"].operation_name == "test"
        assert contexts["retry"].attempt == 1
        assert contexts["resource"].resource_id == resource_id
        assert contexts["user"].user_id == user_id
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


@pytest.mark.unit
class TestMetadataModelsCommonBehavior:
    """Tests for common behavior across all metadata models."""

    def test_all_models_are_hashable(self) -> None:
        """Test that all frozen models can be hashed (for use in sets/dicts)."""
        session = ModelSessionContext(session_id=uuid4())
        http = ModelHttpRequestMetadata(method="GET")
        audit = ModelAuditMetadata(audit_id="audit_123")
        checkpoint = ModelCheckpointMetadata(checkpoint_type="automatic")
        detection = ModelDetectionMetadata(pattern_category="sql")
        node_init = ModelNodeInitMetadata(init_source="container")

        # All should be hashable (no exception raised)
        hash(session)
        hash(http)
        # Note: ModelAuthorizationContext is NOT hashed here because
        # Pydantic frozen models with mutable fields (lists) are not hashable.
        hash(audit)
        hash(checkpoint)
        hash(detection)
        hash(node_init)

    def test_all_models_support_model_dump(self) -> None:
        """Test that all models support model_dump serialization."""
        models = [
            ModelSessionContext(session_id=uuid4()),
            ModelHttpRequestMetadata(method="GET"),
            ModelAuthorizationContext(roles=["user"]),
            ModelAuditMetadata(audit_id="audit_123"),
            ModelCheckpointMetadata(checkpoint_type="automatic"),
            ModelDetectionMetadata(pattern_category="sql"),
            ModelNodeInitMetadata(init_source="container"),
        ]

        for model in models:
            data = model.model_dump()
            assert isinstance(data, dict)

    def test_all_models_support_model_dump_json(self) -> None:
        """Test that all models support model_dump_json serialization."""
        models = [
            ModelSessionContext(session_id=uuid4()),
            ModelHttpRequestMetadata(method="GET"),
            ModelAuthorizationContext(roles=["user"]),
            ModelAuditMetadata(audit_id="audit_123"),
            ModelCheckpointMetadata(checkpoint_type="automatic"),
            ModelDetectionMetadata(pattern_category="sql"),
            ModelNodeInitMetadata(init_source="container"),
        ]

        for model in models:
            json_str = model.model_dump_json()
            assert isinstance(json_str, str)
            assert len(json_str) > 0

    def test_all_models_support_equality(self) -> None:
        """Test that models with same values are equal."""
        test_session_id = uuid4()
        session1 = ModelSessionContext(session_id=test_session_id, locale="en-US")
        session2 = ModelSessionContext(session_id=test_session_id, locale="en-US")
        assert session1 == session2

        http1 = ModelHttpRequestMetadata(method="GET", path="/api")
        http2 = ModelHttpRequestMetadata(method="GET", path="/api")
        assert http1 == http2

    def test_all_models_support_copy(self) -> None:
        """Test that models can be copied with model_copy."""
        test_session_id = uuid4()
        session = ModelSessionContext(session_id=test_session_id)
        session_copy = session.model_copy()
        assert session == session_copy
        assert session is not session_copy

        # Test copy with update
        session_updated = session.model_copy(update={"locale": "fr-FR"})
        assert session_updated.session_id == test_session_id
        assert session_updated.locale == "fr-FR"


# =============================================================================
# Enum Backward Compatibility Tests (OMN-1054)
# =============================================================================


@pytest.mark.unit
class TestModelAuthorizationContextEnumSupport:
    """Tests for ModelAuthorizationContext enum support with backward compatibility."""

    def test_token_type_accepts_enum_value(self) -> None:
        """Test that token_type accepts EnumTokenType directly."""
        context = ModelAuthorizationContext(
            token_type=EnumTokenType.BEARER,
        )
        assert context.token_type == EnumTokenType.BEARER
        assert isinstance(context.token_type, EnumTokenType)

    def test_token_type_accepts_string_and_normalizes_to_enum(self) -> None:
        """Test that token_type accepts string and normalizes to enum."""
        context = ModelAuthorizationContext(
            token_type="bearer",
        )
        assert context.token_type == EnumTokenType.BEARER
        assert isinstance(context.token_type, EnumTokenType)

    def test_token_type_accepts_uppercase_string(self) -> None:
        """Test that token_type accepts uppercase string and normalizes."""
        context = ModelAuthorizationContext(
            token_type="BEARER",
        )
        assert context.token_type == EnumTokenType.BEARER

    def test_token_type_rejects_unknown_string(self) -> None:
        """Test that unknown strings raise ValidationError (strict validation)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuthorizationContext(
                token_type="CustomToken",
            )
        # Unknown strings are rejected with a helpful error message
        assert "Invalid token_type" in str(exc_info.value)

    def test_token_type_none_allowed(self) -> None:
        """Test that token_type accepts None."""
        context = ModelAuthorizationContext(token_type=None)
        assert context.token_type is None

    def test_existing_bearer_string_still_works(self) -> None:
        """Test backward compatibility: existing 'Bearer' string still works."""
        # This is a common existing usage pattern
        context = ModelAuthorizationContext(
            roles=["admin"],
            token_type="Bearer",
        )
        # Should normalize to enum
        assert context.token_type == EnumTokenType.BEARER


@pytest.mark.unit
class TestModelSessionContextEnumSupport:
    """Tests for ModelSessionContext enum support with backward compatibility."""

    def test_authentication_method_accepts_enum_value(self) -> None:
        """Test that authentication_method accepts EnumAuthenticationMethod directly."""
        context = ModelSessionContext(
            authentication_method=EnumAuthenticationMethod.OAUTH2,
        )
        assert context.authentication_method == EnumAuthenticationMethod.OAUTH2
        assert isinstance(context.authentication_method, EnumAuthenticationMethod)

    def test_authentication_method_accepts_string_and_normalizes(self) -> None:
        """Test that authentication_method accepts string and normalizes to enum."""
        context = ModelSessionContext(
            authentication_method="oauth2",
        )
        assert context.authentication_method == EnumAuthenticationMethod.OAUTH2
        assert isinstance(context.authentication_method, EnumAuthenticationMethod)

    def test_authentication_method_accepts_saml_string(self) -> None:
        """Test that authentication_method accepts 'saml' string."""
        context = ModelSessionContext(
            authentication_method="saml",
        )
        assert context.authentication_method == EnumAuthenticationMethod.SAML

    def test_authentication_method_rejects_unknown_string(self) -> None:
        """Test that unknown strings raise ValidationError (strict validation)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSessionContext(
                authentication_method="custom_sso",
            )
        # Unknown strings are rejected with a helpful error message
        assert "Invalid authentication method" in str(exc_info.value)

    def test_authentication_method_none_allowed(self) -> None:
        """Test that authentication_method accepts None."""
        context = ModelSessionContext(authentication_method=None)
        assert context.authentication_method is None

    def test_existing_oauth2_string_still_works(self) -> None:
        """Test backward compatibility: existing usage patterns still work."""
        test_session_id = uuid4()
        context = ModelSessionContext(
            session_id=test_session_id,
            authentication_method="oauth2",
        )
        assert context.authentication_method == EnumAuthenticationMethod.OAUTH2


@pytest.mark.unit
class TestModelCheckpointMetadataEnumSupport:
    """Tests for ModelCheckpointMetadata enum support with backward compatibility."""

    def test_checkpoint_type_accepts_enum_value(self) -> None:
        """Test that checkpoint_type accepts EnumCheckpointType directly."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type=EnumCheckpointType.AUTOMATIC,
        )
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC
        assert isinstance(metadata.checkpoint_type, EnumCheckpointType)

    def test_checkpoint_type_accepts_string_and_normalizes(self) -> None:
        """Test that checkpoint_type accepts string and normalizes to enum."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type="automatic",
        )
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC

    def test_checkpoint_type_manual_string(self) -> None:
        """Test that checkpoint_type accepts 'manual' string."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type="manual",
        )
        assert metadata.checkpoint_type == EnumCheckpointType.MANUAL

    def test_checkpoint_type_rejects_unknown_string(self) -> None:
        """Test that unknown strings raise ValidationError (strict validation)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCheckpointMetadata(
                checkpoint_type="custom_checkpoint",
            )
        # Unknown strings are rejected with a helpful error message
        assert "Invalid checkpoint_type" in str(exc_info.value)

    def test_trigger_event_accepts_enum_value(self) -> None:
        """Test that trigger_event accepts EnumTriggerEvent directly."""
        metadata = ModelCheckpointMetadata(
            trigger_event=EnumTriggerEvent.STAGE_COMPLETE,
        )
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE
        assert isinstance(metadata.trigger_event, EnumTriggerEvent)

    def test_trigger_event_accepts_string_and_normalizes(self) -> None:
        """Test that trigger_event accepts string and normalizes to enum."""
        metadata = ModelCheckpointMetadata(
            trigger_event="stage_complete",
        )
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE

    def test_trigger_event_error_string(self) -> None:
        """Test that trigger_event accepts 'error' string."""
        metadata = ModelCheckpointMetadata(
            trigger_event="error",
        )
        assert metadata.trigger_event == EnumTriggerEvent.ERROR

    def test_trigger_event_rejects_unknown_string(self) -> None:
        """Test that unknown strings raise ValidationError (strict validation)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCheckpointMetadata(
                trigger_event="custom_trigger",
            )
        # Unknown strings are rejected with a helpful error message
        assert "Invalid trigger_event" in str(exc_info.value)

    def test_both_fields_accept_none(self) -> None:
        """Test that both fields accept None."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type=None,
            trigger_event=None,
        )
        assert metadata.checkpoint_type is None
        assert metadata.trigger_event is None

    def test_existing_string_usage_still_works(self) -> None:
        """Test backward compatibility: existing usage patterns still work."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type="automatic",
            source_node="node_compute_transform",
            trigger_event="stage_complete",
            workflow_stage="processing",
        )
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE


@pytest.mark.unit
class TestModelDetectionMetadataEnumSupport:
    """Tests for ModelDetectionMetadata enum support with backward compatibility."""

    def test_false_positive_likelihood_accepts_enum_value(self) -> None:
        """Test that false_positive_likelihood accepts EnumLikelihood directly."""
        metadata = ModelDetectionMetadata(
            false_positive_likelihood=EnumLikelihood.LOW,
        )
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW
        assert isinstance(metadata.false_positive_likelihood, EnumLikelihood)

    def test_false_positive_likelihood_accepts_string_and_normalizes(self) -> None:
        """Test that false_positive_likelihood accepts string and normalizes."""
        metadata = ModelDetectionMetadata(
            false_positive_likelihood="low",
        )
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW

    def test_false_positive_likelihood_medium_string(self) -> None:
        """Test that false_positive_likelihood accepts 'medium' string."""
        metadata = ModelDetectionMetadata(
            false_positive_likelihood="medium",
        )
        assert metadata.false_positive_likelihood == EnumLikelihood.MEDIUM

    def test_false_positive_likelihood_high_string(self) -> None:
        """Test that false_positive_likelihood accepts 'high' string."""
        metadata = ModelDetectionMetadata(
            false_positive_likelihood="high",
        )
        assert metadata.false_positive_likelihood == EnumLikelihood.HIGH

    def test_false_positive_likelihood_very_low_string(self) -> None:
        """Test that false_positive_likelihood accepts 'very_low' string."""
        metadata = ModelDetectionMetadata(
            false_positive_likelihood="very_low",
        )
        assert metadata.false_positive_likelihood == EnumLikelihood.VERY_LOW

    def test_false_positive_likelihood_rejects_invalid_string(self) -> None:
        """Test that unknown strings raise ValueError for strict validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDetectionMetadata(
                false_positive_likelihood="negligible",
            )
        assert "is not a valid EnumLikelihood" in str(exc_info.value)

    def test_false_positive_likelihood_none_allowed(self) -> None:
        """Test that false_positive_likelihood accepts None."""
        metadata = ModelDetectionMetadata(false_positive_likelihood=None)
        assert metadata.false_positive_likelihood is None

    def test_string_normalization_to_enum(self) -> None:
        """Test that valid string values are normalized to enum."""
        metadata = ModelDetectionMetadata(
            pattern_category="credential_exposure",
            detection_source="regex_scanner",
            rule_version="2.1.0",
            false_positive_likelihood="low",
            remediation_hint="Rotate exposed credentials immediately",
        )
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW
        assert metadata.pattern_category == "credential_exposure"


@pytest.mark.unit
class TestEnumSerializationRoundTrip:
    """Tests for enum serialization and deserialization round-trip."""

    def test_authorization_context_enum_serialization(self) -> None:
        """Test that enum values serialize correctly."""
        context = ModelAuthorizationContext(
            token_type=EnumTokenType.JWT,
        )
        data = context.model_dump()
        assert data["token_type"] == "jwt"

        # Round-trip: recreate from serialized data
        context2 = ModelAuthorizationContext.model_validate(data)
        assert context2.token_type == EnumTokenType.JWT

    def test_session_context_enum_serialization(self) -> None:
        """Test that authentication_method enum serializes correctly."""
        context = ModelSessionContext(
            authentication_method=EnumAuthenticationMethod.SAML,
        )
        data = context.model_dump()
        assert data["authentication_method"] == "saml"

        # Round-trip
        context2 = ModelSessionContext.model_validate(data)
        assert context2.authentication_method == EnumAuthenticationMethod.SAML

    def test_checkpoint_metadata_enum_serialization(self) -> None:
        """Test that checkpoint enums serialize correctly."""
        metadata = ModelCheckpointMetadata(
            checkpoint_type=EnumCheckpointType.RECOVERY,
            trigger_event=EnumTriggerEvent.ERROR,
        )
        data = metadata.model_dump()
        assert data["checkpoint_type"] == "recovery"
        assert data["trigger_event"] == "error"

        # Round-trip
        metadata2 = ModelCheckpointMetadata.model_validate(data)
        assert metadata2.checkpoint_type == EnumCheckpointType.RECOVERY
        assert metadata2.trigger_event == EnumTriggerEvent.ERROR

    def test_detection_metadata_enum_serialization(self) -> None:
        """Test that likelihood enum serializes correctly."""
        metadata = ModelDetectionMetadata(
            false_positive_likelihood=EnumLikelihood.VERY_HIGH,
        )
        data = metadata.model_dump()
        assert data["false_positive_likelihood"] == "very_high"

        # Round-trip
        metadata2 = ModelDetectionMetadata.model_validate(data)
        assert metadata2.false_positive_likelihood == EnumLikelihood.VERY_HIGH

    def test_json_serialization_round_trip(self) -> None:
        """Test that enum values survive JSON serialization round-trip."""
        context = ModelAuthorizationContext(
            roles=["admin"],
            token_type=EnumTokenType.OAUTH2,
        )
        json_str = context.model_dump_json()
        assert '"oauth2"' in json_str

        # Round-trip from JSON
        context2 = ModelAuthorizationContext.model_validate_json(json_str)
        assert context2.token_type == EnumTokenType.OAUTH2
