# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for EnumHandlerCapability.

Tests all aspects of the handler capability enum including:
- Enum value validation
- String representation
- Serialization/deserialization
- Helper methods (values, assert_exhaustive)
- Pydantic integration
- JSON/YAML compatibility
"""

import json
from enum import Enum

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_handler_capability import EnumHandlerCapability


@pytest.mark.unit
class TestEnumHandlerCapability:
    """Test basic enum functionality."""

    def test_enum_values_exist(self):
        """Test that all expected enum values exist with correct string values."""
        expected_values = {
            "TRANSFORM": "transform",
            "VALIDATE": "validate",
            "CACHE": "cache",
            "RETRY": "retry",
            "BATCH": "batch",
            "STREAM": "stream",
            "ASYNC": "async",
            "IDEMPOTENT": "idempotent",
        }

        for name, value in expected_values.items():
            capability = getattr(EnumHandlerCapability, name)
            assert capability.value == value, f"{name} should have value '{value}'"

    def test_enum_value_transform(self):
        """Test TRANSFORM capability value."""
        assert EnumHandlerCapability.TRANSFORM == "transform"
        assert EnumHandlerCapability.TRANSFORM.value == "transform"

    def test_enum_value_validate(self):
        """Test VALIDATE capability value."""
        assert EnumHandlerCapability.VALIDATE == "validate"
        assert EnumHandlerCapability.VALIDATE.value == "validate"

    def test_enum_value_cache(self):
        """Test CACHE capability value."""
        assert EnumHandlerCapability.CACHE == "cache"
        assert EnumHandlerCapability.CACHE.value == "cache"

    def test_enum_value_retry(self):
        """Test RETRY capability value."""
        assert EnumHandlerCapability.RETRY == "retry"
        assert EnumHandlerCapability.RETRY.value == "retry"

    def test_enum_value_batch(self):
        """Test BATCH capability value."""
        assert EnumHandlerCapability.BATCH == "batch"
        assert EnumHandlerCapability.BATCH.value == "batch"

    def test_enum_value_stream(self):
        """Test STREAM capability value."""
        assert EnumHandlerCapability.STREAM == "stream"
        assert EnumHandlerCapability.STREAM.value == "stream"

    def test_enum_value_async(self):
        """Test ASYNC capability value."""
        assert EnumHandlerCapability.ASYNC == "async"
        assert EnumHandlerCapability.ASYNC.value == "async"

    def test_enum_value_idempotent(self):
        """Test IDEMPOTENT capability value."""
        assert EnumHandlerCapability.IDEMPOTENT == "idempotent"
        assert EnumHandlerCapability.IDEMPOTENT.value == "idempotent"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHandlerCapability, str)
        assert issubclass(EnumHandlerCapability, Enum)

    def test_enum_count(self):
        """Test that enum has exactly 8 values."""
        all_values = list(EnumHandlerCapability)
        assert len(all_values) == 8


@pytest.mark.unit
class TestEnumHandlerCapabilityStringBehavior:
    """Test string representation and behavior."""

    def test_str_method_returns_value(self):
        """Test that __str__ returns the enum value (not name)."""
        # The enum overrides __str__ to return the value
        assert str(EnumHandlerCapability.TRANSFORM) == "transform"
        assert str(EnumHandlerCapability.VALIDATE) == "validate"
        assert str(EnumHandlerCapability.CACHE) == "cache"
        assert str(EnumHandlerCapability.RETRY) == "retry"
        assert str(EnumHandlerCapability.BATCH) == "batch"
        assert str(EnumHandlerCapability.STREAM) == "stream"
        assert str(EnumHandlerCapability.ASYNC) == "async"
        assert str(EnumHandlerCapability.IDEMPOTENT) == "idempotent"

    def test_string_comparison(self):
        """Test that enum values can be compared to strings."""
        assert EnumHandlerCapability.TRANSFORM == "transform"
        assert EnumHandlerCapability.CACHE == "cache"
        assert EnumHandlerCapability.ASYNC != "sync"

    def test_string_operations(self):
        """Test that string operations work on enum values."""
        # Since it inherits from str, string methods should work
        assert EnumHandlerCapability.TRANSFORM.upper() == "TRANSFORM"
        assert EnumHandlerCapability.CACHE.startswith("cache")
        assert "form" in EnumHandlerCapability.TRANSFORM


@pytest.mark.unit
class TestEnumHandlerCapabilitySerialization:
    """Test serialization and deserialization."""

    def test_enum_serialization_via_value(self):
        """Test enum serialization through .value attribute."""
        assert EnumHandlerCapability.TRANSFORM.value == "transform"
        assert EnumHandlerCapability.VALIDATE.value == "validate"
        assert EnumHandlerCapability.CACHE.value == "cache"
        assert EnumHandlerCapability.RETRY.value == "retry"
        assert EnumHandlerCapability.BATCH.value == "batch"
        assert EnumHandlerCapability.STREAM.value == "stream"
        assert EnumHandlerCapability.ASYNC.value == "async"
        assert EnumHandlerCapability.IDEMPOTENT.value == "idempotent"

    def test_enum_deserialization(self):
        """Test enum deserialization from string values."""
        assert EnumHandlerCapability("transform") == EnumHandlerCapability.TRANSFORM
        assert EnumHandlerCapability("validate") == EnumHandlerCapability.VALIDATE
        assert EnumHandlerCapability("cache") == EnumHandlerCapability.CACHE
        assert EnumHandlerCapability("retry") == EnumHandlerCapability.RETRY
        assert EnumHandlerCapability("batch") == EnumHandlerCapability.BATCH
        assert EnumHandlerCapability("stream") == EnumHandlerCapability.STREAM
        assert EnumHandlerCapability("async") == EnumHandlerCapability.ASYNC
        assert EnumHandlerCapability("idempotent") == EnumHandlerCapability.IDEMPOTENT

    def test_enum_invalid_value_raises(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerCapability("invalid_capability")

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Using .value for direct JSON serialization
        data = {"capability": EnumHandlerCapability.CACHE.value}
        json_str = json.dumps(data)
        assert '"capability": "cache"' in json_str

        # Deserialize and compare
        loaded = json.loads(json_str)
        assert (
            EnumHandlerCapability(loaded["capability"]) == EnumHandlerCapability.CACHE
        )

    def test_json_serialization_with_str(self):
        """Test JSON serialization using str() method."""
        capability = EnumHandlerCapability.RETRY
        json_str = json.dumps({"cap": str(capability)})
        assert '"cap": "retry"' in json_str

    def test_yaml_serialization(self):
        """Test YAML serialization compatibility."""
        data = {"handler_capability": EnumHandlerCapability.STREAM.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "handler_capability: stream" in yaml_str

        # Deserialize and compare
        loaded = yaml.safe_load(yaml_str)
        assert loaded["handler_capability"] == "stream"
        assert (
            EnumHandlerCapability(loaded["handler_capability"])
            == EnumHandlerCapability.STREAM
        )


@pytest.mark.unit
class TestEnumHandlerCapabilityHelperMethods:
    """Test helper methods on the enum."""

    def test_values_class_method(self):
        """Test that values() returns all enum values as strings."""
        values = EnumHandlerCapability.values()

        assert isinstance(values, list)
        assert len(values) == 8
        assert "transform" in values
        assert "validate" in values
        assert "cache" in values
        assert "retry" in values
        assert "batch" in values
        assert "stream" in values
        assert "async" in values
        assert "idempotent" in values

    def test_values_returns_strings_not_enums(self):
        """Test that values() returns strings, not enum instances."""
        values = EnumHandlerCapability.values()

        for value in values:
            assert isinstance(value, str)
            assert not isinstance(value, EnumHandlerCapability)

    def test_values_matches_enum_iteration(self):
        """Test that values() matches iterating over enum."""
        values_method = EnumHandlerCapability.values()
        values_iteration = [member.value for member in EnumHandlerCapability]

        assert set(values_method) == set(values_iteration)

    def test_assert_exhaustive_raises_assertion_error(self) -> None:
        """Test that assert_exhaustive raises AssertionError.

        Note: Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # Create a mock "Never" type value - in practice this would be caught
        # by the type checker before runtime, but we test runtime behavior
        with pytest.raises(AssertionError) as exc_info:
            # We need to bypass type checking for this test
            EnumHandlerCapability.assert_exhaustive("unexpected_value")  # type: ignore[arg-type]

        assert "Unhandled enum value" in str(exc_info.value)
        assert "unexpected_value" in str(exc_info.value)

    def test_assert_exhaustive_error_message_format(self) -> None:
        """Test the error message format of assert_exhaustive."""
        with pytest.raises(AssertionError) as exc_info:
            EnumHandlerCapability.assert_exhaustive(42)  # type: ignore[arg-type]

        error_msg = str(exc_info.value)
        assert "Unhandled enum value: 42" in error_msg


@pytest.mark.unit
class TestEnumHandlerCapabilityIteration:
    """Test iteration and membership operations."""

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        capabilities = list(EnumHandlerCapability)

        assert len(capabilities) == 8
        assert EnumHandlerCapability.TRANSFORM in capabilities
        assert EnumHandlerCapability.VALIDATE in capabilities
        assert EnumHandlerCapability.CACHE in capabilities
        assert EnumHandlerCapability.RETRY in capabilities
        assert EnumHandlerCapability.BATCH in capabilities
        assert EnumHandlerCapability.STREAM in capabilities
        assert EnumHandlerCapability.ASYNC in capabilities
        assert EnumHandlerCapability.IDEMPOTENT in capabilities

    def test_enum_membership_by_value(self):
        """Test membership testing using string values."""
        assert "transform" in EnumHandlerCapability
        assert "validate" in EnumHandlerCapability
        assert "cache" in EnumHandlerCapability
        assert "retry" in EnumHandlerCapability
        assert "batch" in EnumHandlerCapability
        assert "stream" in EnumHandlerCapability
        assert "async" in EnumHandlerCapability
        assert "idempotent" in EnumHandlerCapability
        assert "invalid" not in EnumHandlerCapability

    def test_enum_membership_by_instance(self):
        """Test membership testing using enum instances."""
        assert EnumHandlerCapability.TRANSFORM in EnumHandlerCapability
        assert EnumHandlerCapability.ASYNC in EnumHandlerCapability


@pytest.mark.unit
class TestEnumHandlerCapabilityComparison:
    """Test comparison operations."""

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumHandlerCapability.CACHE == EnumHandlerCapability.CACHE
        assert EnumHandlerCapability.RETRY != EnumHandlerCapability.BATCH
        assert EnumHandlerCapability.TRANSFORM != EnumHandlerCapability.VALIDATE

    def test_enum_equality_with_string(self):
        """Test enum equality with string values."""
        assert EnumHandlerCapability.TRANSFORM == "transform"
        assert EnumHandlerCapability.ASYNC == "async"
        assert EnumHandlerCapability.CACHE != "invalid"

    def test_enum_identity(self):
        """Test enum identity (is operator)."""
        cap1 = EnumHandlerCapability.STREAM
        cap2 = EnumHandlerCapability.STREAM
        assert cap1 is cap2


@pytest.mark.unit
class TestEnumHandlerCapabilityPydantic:
    """Test Pydantic integration."""

    def test_pydantic_model_with_enum(self):
        """Test using enum in Pydantic model."""

        class HandlerConfig(BaseModel):
            capability: EnumHandlerCapability

        model = HandlerConfig(capability=EnumHandlerCapability.CACHE)
        assert model.capability == EnumHandlerCapability.CACHE

    def test_pydantic_model_with_string_value(self):
        """Test Pydantic model accepts string values."""

        class HandlerConfig(BaseModel):
            capability: EnumHandlerCapability

        model = HandlerConfig(capability="batch")
        assert model.capability == EnumHandlerCapability.BATCH

    def test_pydantic_model_invalid_value(self):
        """Test Pydantic model rejects invalid values."""

        class HandlerConfig(BaseModel):
            capability: EnumHandlerCapability

        with pytest.raises(ValidationError):
            HandlerConfig(capability="invalid_capability")

    def test_pydantic_model_serialization(self):
        """Test Pydantic model serialization."""

        class HandlerConfig(BaseModel):
            capability: EnumHandlerCapability

        model = HandlerConfig(capability=EnumHandlerCapability.IDEMPOTENT)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"capability": "idempotent"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"capability":"idempotent"}'

    def test_pydantic_model_multiple_capabilities(self):
        """Test Pydantic model with list of capabilities."""

        class HandlerCapabilities(BaseModel):
            capabilities: list[EnumHandlerCapability]

        model = HandlerCapabilities(
            capabilities=[
                EnumHandlerCapability.CACHE,
                EnumHandlerCapability.RETRY,
                EnumHandlerCapability.ASYNC,
            ]
        )

        assert len(model.capabilities) == 3
        assert EnumHandlerCapability.CACHE in model.capabilities
        assert EnumHandlerCapability.RETRY in model.capabilities
        assert EnumHandlerCapability.ASYNC in model.capabilities


@pytest.mark.unit
class TestEnumHandlerCapabilityEdgeCases:
    """Test edge cases and error conditions."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""
        assert EnumHandlerCapability.CACHE.value == "cache"
        assert EnumHandlerCapability.CACHE.value != "CACHE"
        assert EnumHandlerCapability.CACHE.value != "Cache"

    def test_case_sensitive_lookup(self):
        """Test that case-sensitive lookup works correctly."""
        # Lowercase works
        assert EnumHandlerCapability("cache") == EnumHandlerCapability.CACHE

        # Uppercase should fail
        with pytest.raises(ValueError):
            EnumHandlerCapability("CACHE")

    def test_empty_string_invalid(self):
        """Test that empty string is invalid."""
        with pytest.raises(ValueError):
            EnumHandlerCapability("")

    def test_whitespace_invalid(self):
        """Test that whitespace-padded values are invalid."""
        with pytest.raises(ValueError):
            EnumHandlerCapability(" cache")

        with pytest.raises(ValueError):
            EnumHandlerCapability("cache ")

    def test_none_invalid(self):
        """Test that None is invalid."""
        with pytest.raises((ValueError, TypeError)):
            EnumHandlerCapability(None)  # type: ignore[arg-type]

    def test_enum_name_vs_value(self):
        """Test distinction between enum name and value."""
        cap = EnumHandlerCapability.TRANSFORM
        assert cap.name == "TRANSFORM"
        assert cap.value == "transform"
        assert cap.name != cap.value


@pytest.mark.unit
class TestEnumHandlerCapabilityDocstring:
    """Test docstring and documentation."""

    def test_enum_has_docstring(self):
        """Test that enum class has a docstring."""
        assert EnumHandlerCapability.__doc__ is not None
        assert len(EnumHandlerCapability.__doc__) > 0

    def test_docstring_mentions_capabilities(self):
        """Test that docstring describes the capabilities."""
        docstring = EnumHandlerCapability.__doc__ or ""
        assert "TRANSFORM" in docstring
        assert "VALIDATE" in docstring
        assert "CACHE" in docstring
        assert "RETRY" in docstring

    def test_docstring_mentions_node_types(self):
        """Test that docstring mentions applicable node types."""
        docstring = EnumHandlerCapability.__doc__ or ""
        assert "COMPUTE" in docstring
        assert "EFFECT" in docstring
        assert "REDUCER" in docstring
        assert "ORCHESTRATOR" in docstring


@pytest.mark.unit
class TestEnumHandlerCapabilityExhaustiveness:
    """Test exhaustiveness - ensure all enum values are tested."""

    def test_exhaustive_value_coverage(self):
        """Test that all enum values are explicitly tested."""
        expected_capabilities = {
            "transform",
            "validate",
            "cache",
            "retry",
            "batch",
            "stream",
            "async",
            "idempotent",
        }

        actual_values = {cap.value for cap in EnumHandlerCapability}

        assert actual_values == expected_capabilities, (
            f"Enum values mismatch. "
            f"Missing: {expected_capabilities - actual_values}. "
            f"Extra: {actual_values - expected_capabilities}"
        )

    def test_exhaustive_match_statement(self):
        """Test using match statement for exhaustive handling."""

        def describe_capability(cap: EnumHandlerCapability) -> str:
            match cap:
                case EnumHandlerCapability.TRANSFORM:
                    return "Data transformation"
                case EnumHandlerCapability.VALIDATE:
                    return "Input/output validation"
                case EnumHandlerCapability.CACHE:
                    return "Result caching"
                case EnumHandlerCapability.RETRY:
                    return "Automatic retry"
                case EnumHandlerCapability.BATCH:
                    return "Batch processing"
                case EnumHandlerCapability.STREAM:
                    return "Streaming data"
                case EnumHandlerCapability.ASYNC:
                    return "Asynchronous execution"
                case EnumHandlerCapability.IDEMPOTENT:
                    return "Idempotent operation"
                case _:
                    EnumHandlerCapability.assert_exhaustive(cap)

        # Test all capabilities have descriptions
        for cap in EnumHandlerCapability:
            description = describe_capability(cap)
            assert isinstance(description, str)
            assert len(description) > 0


@pytest.mark.unit
class TestEnumHandlerCapabilityUseCases:
    """Test real-world usage scenarios."""

    def test_capability_set_operations(self):
        """Test using capabilities in set operations."""
        handler_caps = {
            EnumHandlerCapability.CACHE,
            EnumHandlerCapability.RETRY,
            EnumHandlerCapability.ASYNC,
        }

        required_caps = {
            EnumHandlerCapability.CACHE,
            EnumHandlerCapability.ASYNC,
        }

        # Test subset
        assert required_caps.issubset(handler_caps)

        # Test intersection
        common = handler_caps.intersection(required_caps)
        assert len(common) == 2

    def test_capability_filtering(self):
        """Test filtering handlers by capability."""
        handlers = [
            {
                "name": "http_handler",
                "capabilities": [
                    EnumHandlerCapability.ASYNC,
                    EnumHandlerCapability.RETRY,
                ],
            },
            {
                "name": "db_handler",
                "capabilities": [
                    EnumHandlerCapability.CACHE,
                    EnumHandlerCapability.BATCH,
                ],
            },
            {
                "name": "file_handler",
                "capabilities": [
                    EnumHandlerCapability.STREAM,
                    EnumHandlerCapability.IDEMPOTENT,
                ],
            },
        ]

        # Find handlers with CACHE capability
        cached_handlers = [
            h for h in handlers if EnumHandlerCapability.CACHE in h["capabilities"]
        ]
        assert len(cached_handlers) == 1
        assert cached_handlers[0]["name"] == "db_handler"

    def test_capability_dict_key(self):
        """Test using capability as dictionary key."""
        capability_descriptions = {
            EnumHandlerCapability.TRANSFORM: "Can transform data",
            EnumHandlerCapability.CACHE: "Supports caching",
            EnumHandlerCapability.ASYNC: "Runs asynchronously",
        }

        assert (
            capability_descriptions[EnumHandlerCapability.CACHE] == "Supports caching"
        )
        assert EnumHandlerCapability.TRANSFORM in capability_descriptions

    def test_values_method_for_validation(self):
        """Test using values() method for input validation."""
        valid_values = EnumHandlerCapability.values()

        # Validate user input
        user_input = "cache"
        assert user_input in valid_values

        invalid_input = "invalid"
        assert invalid_input not in valid_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
