# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelActionExecutionContext.

Tests all ModelActionExecutionContext functionality including:
- Basic instantiation with all fields
- Partial instantiation with optional fields
- Default value verification
- Field validation (environment, timeout, retries)
- Frozen behavior (immutability)
- Extra fields forbidden
- JSON serialization/deserialization
- from_attributes behavior
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelActionExecutionContext

# =============================================================================
# Helper classes for from_attributes testing
# =============================================================================


@dataclass
class ActionExecutionContextAttrs:
    """Helper dataclass for testing from_attributes on ModelActionExecutionContext."""

    node_id: str | None = None
    workflow_id: UUID | None = None
    environment: str = "development"
    timeout_ms: int = 30000
    retry_count: int = 0
    max_retries: int = 3
    dry_run: bool = False
    debug_mode: bool = False
    trace_enabled: bool = False
    correlation_id: str | None = None


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextInstantiation:
    """Tests for ModelActionExecutionContext instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating context with all fields populated."""
        workflow_id = uuid4()
        context = ModelActionExecutionContext(
            node_id="node_compute_abc123",
            workflow_id=workflow_id,
            environment="production",
            timeout_ms=60000,
            retry_count=2,
            max_retries=5,
            dry_run=True,
            debug_mode=True,
            trace_enabled=True,
            correlation_id="corr-xyz-789",
        )

        assert context.node_id == "node_compute_abc123"
        assert context.workflow_id == workflow_id
        assert context.environment == "production"
        assert context.timeout_ms == 60000
        assert context.retry_count == 2
        assert context.max_retries == 5
        assert context.dry_run is True
        assert context.debug_mode is True
        assert context.trace_enabled is True
        assert context.correlation_id == "corr-xyz-789"

    def test_create_with_partial_fields(self) -> None:
        """Test creating context with only some fields."""
        context = ModelActionExecutionContext(
            node_id="node_effect_io",
            environment="staging",
        )

        assert context.node_id == "node_effect_io"
        assert context.environment == "staging"
        assert context.workflow_id is None
        assert context.timeout_ms == 30000  # default
        assert context.dry_run is False  # default

    def test_create_with_no_fields(self) -> None:
        """Test creating context with all defaults."""
        context = ModelActionExecutionContext()

        assert context.node_id is None
        assert context.workflow_id is None
        assert context.environment == "development"
        assert context.timeout_ms == 30000
        assert context.retry_count == 0
        assert context.max_retries == 3
        assert context.dry_run is False
        assert context.debug_mode is False
        assert context.trace_enabled is False
        assert context.correlation_id is None


# =============================================================================
# Default Value Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextDefaults:
    """Tests for ModelActionExecutionContext default values."""

    def test_environment_defaults_to_development(self) -> None:
        """Test that environment defaults to 'development'."""
        context = ModelActionExecutionContext()
        assert context.environment == "development"

    def test_timeout_ms_defaults_to_30000(self) -> None:
        """Test that timeout_ms defaults to 30000 milliseconds."""
        context = ModelActionExecutionContext()
        assert context.timeout_ms == 30000

    def test_retry_count_defaults_to_0(self) -> None:
        """Test that retry_count defaults to 0."""
        context = ModelActionExecutionContext()
        assert context.retry_count == 0

    def test_max_retries_defaults_to_3(self) -> None:
        """Test that max_retries defaults to 3."""
        context = ModelActionExecutionContext()
        assert context.max_retries == 3

    def test_boolean_fields_default_to_false(self) -> None:
        """Test that boolean fields default to False."""
        context = ModelActionExecutionContext()
        assert context.dry_run is False
        assert context.debug_mode is False
        assert context.trace_enabled is False

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        context = ModelActionExecutionContext()
        assert context.node_id is None
        assert context.workflow_id is None
        assert context.correlation_id is None


# =============================================================================
# Field Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextValidation:
    """Tests for ModelActionExecutionContext field validation."""

    def test_environment_accepts_development(self) -> None:
        """Test that environment accepts 'development'."""
        context = ModelActionExecutionContext(environment="development")
        assert context.environment == "development"

    def test_environment_accepts_staging(self) -> None:
        """Test that environment accepts 'staging'."""
        context = ModelActionExecutionContext(environment="staging")
        assert context.environment == "staging"

    def test_environment_accepts_production(self) -> None:
        """Test that environment accepts 'production'."""
        context = ModelActionExecutionContext(environment="production")
        assert context.environment == "production"

    def test_environment_case_insensitive(self) -> None:
        """Test that environment validation is case-insensitive."""
        context_upper = ModelActionExecutionContext(environment="PRODUCTION")
        assert context_upper.environment == "production"

        context_mixed = ModelActionExecutionContext(environment="Staging")
        assert context_mixed.environment == "staging"

    def test_environment_rejects_invalid_value(self) -> None:
        """Test that invalid environment values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(environment="invalid")
        assert "environment" in str(exc_info.value).lower()

    def test_environment_rejects_empty_string(self) -> None:
        """Test that empty string environment is rejected."""
        with pytest.raises(ValidationError):
            ModelActionExecutionContext(environment="")

    def test_timeout_ms_minimum_is_1(self) -> None:
        """Test that timeout_ms must be at least 1 millisecond."""
        # Valid minimum
        context = ModelActionExecutionContext(timeout_ms=1)
        assert context.timeout_ms == 1

        # Invalid (zero)
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(timeout_ms=0)
        assert "timeout_ms" in str(exc_info.value).lower()

        # Invalid (negative)
        with pytest.raises(ValidationError):
            ModelActionExecutionContext(timeout_ms=-1)

    def test_retry_count_minimum_is_0(self) -> None:
        """Test that retry_count must be at least 0."""
        # Valid minimum
        context = ModelActionExecutionContext(retry_count=0)
        assert context.retry_count == 0

        # Invalid (negative)
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(retry_count=-1)
        assert "retry_count" in str(exc_info.value).lower()

    def test_max_retries_minimum_is_0(self) -> None:
        """Test that max_retries must be at least 0."""
        # Valid minimum (disable retries)
        context = ModelActionExecutionContext(max_retries=0)
        assert context.max_retries == 0

        # Invalid (negative)
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(max_retries=-1)
        assert "max_retries" in str(exc_info.value).lower()

    def test_workflow_id_accepts_valid_uuid(self) -> None:
        """Test that workflow_id accepts valid UUID."""
        workflow_id = uuid4()
        context = ModelActionExecutionContext(workflow_id=workflow_id)
        assert context.workflow_id == workflow_id

    def test_workflow_id_accepts_uuid_string(self) -> None:
        """Test that workflow_id accepts UUID as string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        context = ModelActionExecutionContext(workflow_id=uuid_str)  # type: ignore[arg-type]
        assert context.workflow_id == UUID(uuid_str)

    def test_environment_rejects_non_string_integer(self) -> None:
        """Test that environment rejects integer with clear error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(environment=123)  # type: ignore[arg-type]
        # Should mention environment field and the invalid type
        error_str = str(exc_info.value).lower()
        assert "environment" in error_str
        assert "int" in error_str

    def test_environment_rejects_non_string_list(self) -> None:
        """Test that environment rejects list with clear error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(environment=["production"])  # type: ignore[arg-type]
        error_str = str(exc_info.value).lower()
        assert "environment" in error_str
        assert "list" in error_str

    def test_environment_rejects_non_string_dict(self) -> None:
        """Test that environment rejects dict with clear error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(environment={"env": "production"})  # type: ignore[arg-type]
        error_str = str(exc_info.value).lower()
        assert "environment" in error_str
        assert "dict" in error_str

    def test_environment_rejects_none_explicitly(self) -> None:
        """Test that environment rejects None value explicitly passed."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(environment=None)  # type: ignore[arg-type]
        error_str = str(exc_info.value).lower()
        assert "environment" in error_str
        assert "nonetype" in error_str

    def test_environment_normalizes_uppercase(self) -> None:
        """Test that environment normalizes all-uppercase to lowercase."""
        context = ModelActionExecutionContext(environment="DEVELOPMENT")
        assert context.environment == "development"

    def test_environment_normalizes_mixed_case(self) -> None:
        """Test that environment normalizes mixed case to lowercase."""
        context = ModelActionExecutionContext(environment="PrOdUcTiOn")
        assert context.environment == "production"

    def test_environment_strips_leading_whitespace(self) -> None:
        """Test that environment strips leading whitespace."""
        context = ModelActionExecutionContext(environment="  production")
        assert context.environment == "production"

    def test_environment_strips_trailing_whitespace(self) -> None:
        """Test that environment strips trailing whitespace."""
        context = ModelActionExecutionContext(environment="staging  ")
        assert context.environment == "staging"

    def test_environment_strips_both_whitespace(self) -> None:
        """Test that environment strips both leading and trailing whitespace."""
        context = ModelActionExecutionContext(environment="  development  ")
        assert context.environment == "development"

    def test_environment_strips_whitespace_with_mixed_case(self) -> None:
        """Test that environment handles whitespace and case normalization together."""
        context = ModelActionExecutionContext(environment="  PRODUCTION  ")
        assert context.environment == "production"


# =============================================================================
# Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextImmutability:
    """Tests for ModelActionExecutionContext immutability (frozen=True)."""

    def test_cannot_modify_node_id(self) -> None:
        """Test that node_id cannot be modified after creation."""
        context = ModelActionExecutionContext(node_id="original")
        with pytest.raises(ValidationError):
            context.node_id = "modified"  # type: ignore[misc]

    def test_cannot_modify_environment(self) -> None:
        """Test that environment cannot be modified after creation."""
        context = ModelActionExecutionContext(environment="development")
        with pytest.raises(ValidationError):
            context.environment = "production"  # type: ignore[misc]

    def test_cannot_modify_timeout_ms(self) -> None:
        """Test that timeout_ms cannot be modified after creation."""
        context = ModelActionExecutionContext(timeout_ms=30000)
        with pytest.raises(ValidationError):
            context.timeout_ms = 60000  # type: ignore[misc]

    def test_cannot_modify_dry_run(self) -> None:
        """Test that dry_run cannot be modified after creation."""
        context = ModelActionExecutionContext(dry_run=False)
        with pytest.raises(ValidationError):
            context.dry_run = True  # type: ignore[misc]


# =============================================================================
# Extra Fields Forbidden Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextExtraForbid:
    """Tests for ModelActionExecutionContext extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionExecutionContext(
                node_id="node_123",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# From Attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextFromAttributes:
    """Tests for ModelActionExecutionContext from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelActionExecutionContext from an object with attributes."""
        attrs = ActionExecutionContextAttrs(
            node_id="node_from_attrs",
            environment="staging",
            timeout_ms=45000,
        )
        context = ModelActionExecutionContext.model_validate(attrs)
        assert context.node_id == "node_from_attrs"
        assert context.environment == "staging"
        assert context.timeout_ms == 45000

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        workflow_id = uuid4()
        attrs = ActionExecutionContextAttrs(
            node_id="node_full",
            workflow_id=workflow_id,
            environment="production",
            timeout_ms=120000,
            retry_count=1,
            max_retries=5,
            dry_run=True,
            debug_mode=True,
            trace_enabled=True,
            correlation_id="corr-full",
        )
        context = ModelActionExecutionContext.model_validate(attrs)
        assert context.node_id == "node_full"
        assert context.workflow_id == workflow_id
        assert context.environment == "production"
        assert context.dry_run is True


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextSerialization:
    """Tests for ModelActionExecutionContext serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump serialization."""
        workflow_id = uuid4()
        context = ModelActionExecutionContext(
            node_id="node_serialize",
            workflow_id=workflow_id,
            environment="production",
            timeout_ms=60000,
        )

        data = context.model_dump()
        assert data["node_id"] == "node_serialize"
        assert data["workflow_id"] == workflow_id
        assert data["environment"] == "production"
        assert data["timeout_ms"] == 60000

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        context = ModelActionExecutionContext(
            node_id="node_json",
            environment="staging",
        )

        json_str = context.model_dump_json()
        assert isinstance(json_str, str)
        assert "node_json" in json_str
        assert "staging" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        data = {
            "node_id": "node_from_dict",
            "environment": "development",
            "timeout_ms": 45000,
            "dry_run": True,
        }

        context = ModelActionExecutionContext.model_validate(data)
        assert context.node_id == "node_from_dict"
        assert context.environment == "development"
        assert context.timeout_ms == 45000
        assert context.dry_run is True

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelActionExecutionContext(
            node_id="node_roundtrip",
            workflow_id=uuid4(),
            environment="production",
            timeout_ms=90000,
            retry_count=1,
            max_retries=5,
            dry_run=True,
            debug_mode=True,
            trace_enabled=True,
            correlation_id="corr-roundtrip",
        )

        json_str = original.model_dump_json()
        restored = ModelActionExecutionContext.model_validate_json(json_str)

        assert restored == original


# =============================================================================
# Edge Cases and Additional Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextEdgeCases:
    """Tests for edge cases and additional scenarios."""

    def test_large_timeout_value(self) -> None:
        """Test that large timeout values are accepted."""
        context = ModelActionExecutionContext(timeout_ms=86400000)  # 24 hours in ms
        assert context.timeout_ms == 86400000

    def test_high_retry_count(self) -> None:
        """Test that high retry counts are accepted."""
        context = ModelActionExecutionContext(retry_count=100, max_retries=100)
        assert context.retry_count == 100
        assert context.max_retries == 100

    def test_empty_string_node_id(self) -> None:
        """Test that empty string node_id is accepted (no min_length constraint)."""
        context = ModelActionExecutionContext(node_id="")
        assert context.node_id == ""

    def test_empty_string_correlation_id(self) -> None:
        """Test that empty string correlation_id is accepted."""
        context = ModelActionExecutionContext(correlation_id="")
        assert context.correlation_id == ""

    def test_model_is_hashable(self) -> None:
        """Test that frozen model is hashable (for use in sets/dicts)."""
        context = ModelActionExecutionContext(
            node_id="node_hash",
            environment="development",
        )
        # Should be hashable (no exception raised)
        hash_value = hash(context)
        assert isinstance(hash_value, int)

    def test_equal_contexts_have_same_hash(self) -> None:
        """Test that equal contexts have the same hash."""
        ctx1 = ModelActionExecutionContext(
            node_id="node_same",
            environment="production",
            timeout_ms=60000,
        )
        ctx2 = ModelActionExecutionContext(
            node_id="node_same",
            environment="production",
            timeout_ms=60000,
        )

        assert ctx1 == ctx2
        assert hash(ctx1) == hash(ctx2)

    def test_different_contexts_are_not_equal(self) -> None:
        """Test that different contexts are not equal."""
        ctx1 = ModelActionExecutionContext(environment="development")
        ctx2 = ModelActionExecutionContext(environment="production")

        assert ctx1 != ctx2

    def test_model_copy_with_update(self) -> None:
        """Test model_copy with update for creating modified copies."""
        original = ModelActionExecutionContext(
            node_id="node_original",
            environment="development",
            timeout_ms=30000,
        )

        modified = original.model_copy(
            update={"environment": "production", "timeout_ms": 60000}
        )

        assert modified.node_id == "node_original"
        assert modified.environment == "production"
        assert modified.timeout_ms == 60000
        assert original.environment == "development"  # Original unchanged


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionExecutionContextIntegration:
    """Integration tests for ModelActionExecutionContext."""

    def test_model_config_is_correct(self) -> None:
        """Verify model configuration is correct."""
        config = ModelActionExecutionContext.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_can_be_used_in_dict(self) -> None:
        """Test that context can be stored in dictionary."""
        context = ModelActionExecutionContext(
            node_id="node_dict",
            environment="staging",
        )
        contexts = {"execution": context}
        assert contexts["execution"].node_id == "node_dict"
        assert contexts["execution"].environment == "staging"

    def test_can_be_used_in_set(self) -> None:
        """Test that context can be stored in set (hashable)."""
        ctx1 = ModelActionExecutionContext(environment="development")
        ctx2 = ModelActionExecutionContext(environment="staging")
        ctx3 = ModelActionExecutionContext(environment="development")  # Same as ctx1

        context_set = {ctx1, ctx2, ctx3}
        assert len(context_set) == 2  # ctx1 and ctx3 are equal
