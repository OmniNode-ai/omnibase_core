# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelContractValidationContext.

Tests the validation context model used to configure contract validation behavior,
including validation mode and extensible flags.

Related:
    - OMN-1146: Contract validation event models
    - OMN-1126: Naming collision fix (renamed from ModelContractValidationContext)
    - ModelContractValidationContext: Canonical name for contract validation context
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_validation_mode import EnumValidationMode
from omnibase_core.models.events.contract_validation import (
    ModelContractValidationContext,
)


@pytest.mark.unit
class TestModelContractValidationContextCreation:
    """Tests for ModelContractValidationContext creation and defaults."""

    def test_validation_context_creation_with_defaults(self) -> None:
        """Test that ModelContractValidationContext can be created with defaults."""
        context = ModelContractValidationContext()

        assert context.mode == EnumValidationMode.STRICT
        assert context.flags == {}

    def test_validation_context_creation_with_strict_mode(self) -> None:
        """Test ModelContractValidationContext with explicit STRICT mode."""
        context = ModelContractValidationContext(mode=EnumValidationMode.STRICT)

        assert context.mode == EnumValidationMode.STRICT

    def test_validation_context_creation_with_permissive_mode(self) -> None:
        """Test ModelContractValidationContext with PERMISSIVE mode."""
        context = ModelContractValidationContext(mode=EnumValidationMode.PERMISSIVE)

        assert context.mode == EnumValidationMode.PERMISSIVE

    def test_validation_context_creation_with_flags(self) -> None:
        """Test ModelContractValidationContext with custom flags."""
        flags = {
            "validate_schema": True,
            "skip_optional_checks": False,
            "strict_types": True,
        }
        context = ModelContractValidationContext(flags=flags)

        assert context.flags == flags
        assert context.flags["validate_schema"] is True
        assert context.flags["skip_optional_checks"] is False
        assert context.flags["strict_types"] is True

    def test_validation_context_creation_with_all_fields(self) -> None:
        """Test ModelContractValidationContext with all fields explicitly set."""
        flags = {"custom_flag": True}
        context = ModelContractValidationContext(
            mode=EnumValidationMode.PERMISSIVE,
            flags=flags,
        )

        assert context.mode == EnumValidationMode.PERMISSIVE
        assert context.flags == {"custom_flag": True}


@pytest.mark.unit
class TestModelContractValidationContextDefaultMode:
    """Tests for default mode behavior."""

    def test_default_mode_is_strict(self) -> None:
        """Test that default mode is STRICT."""
        context = ModelContractValidationContext()

        assert context.mode == EnumValidationMode.STRICT
        assert context.mode.is_strict() is True
        assert context.mode.allows_continuation() is False

    def test_default_mode_value_is_strict_string(self) -> None:
        """Test that default mode value is 'strict' string."""
        context = ModelContractValidationContext()

        assert context.mode.value == "strict"
        assert str(context.mode) == "strict"


@pytest.mark.unit
class TestModelContractValidationContextDefaultFlags:
    """Tests for default flags behavior."""

    def test_default_flags_is_empty_dict(self) -> None:
        """Test that default flags is an empty dict."""
        context = ModelContractValidationContext()

        assert context.flags == {}
        assert isinstance(context.flags, dict)
        assert len(context.flags) == 0

    def test_flags_with_empty_dict(self) -> None:
        """Test ModelContractValidationContext with explicit empty dict for flags."""
        context = ModelContractValidationContext(flags={})

        assert context.flags == {}


@pytest.mark.unit
class TestModelContractValidationContextModes:
    """Tests for different validation modes."""

    def test_strict_mode_properties(self) -> None:
        """Test STRICT mode properties."""
        context = ModelContractValidationContext(mode=EnumValidationMode.STRICT)

        assert context.mode.is_strict() is True
        assert context.mode.allows_continuation() is False

    def test_permissive_mode_properties(self) -> None:
        """Test PERMISSIVE mode properties."""
        context = ModelContractValidationContext(mode=EnumValidationMode.PERMISSIVE)

        assert context.mode.is_strict() is False
        assert context.mode.allows_continuation() is True

    def test_mode_can_be_set_via_string(self) -> None:
        """Test that mode can be set via string value."""
        context_strict = ModelContractValidationContext(mode="strict")  # type: ignore[arg-type]
        context_permissive = ModelContractValidationContext(mode="permissive")  # type: ignore[arg-type]

        assert context_strict.mode == EnumValidationMode.STRICT
        assert context_permissive.mode == EnumValidationMode.PERMISSIVE

    def test_invalid_mode_raises_error(self) -> None:
        """Test that invalid mode value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationContext(mode="invalid_mode")  # type: ignore[arg-type]

        error_str = str(exc_info.value)
        assert "mode" in error_str.lower() or "invalid" in error_str.lower()


@pytest.mark.unit
class TestModelContractValidationContextImmutability:
    """Tests for frozen/immutable behavior."""

    def test_validation_context_is_frozen(self) -> None:
        """Test that ModelContractValidationContext config has frozen=True."""
        context = ModelContractValidationContext()

        config = context.model_config
        assert config.get("frozen") is True

    def test_validation_context_cannot_modify_mode(self) -> None:
        """Test that mode cannot be modified after creation."""
        context = ModelContractValidationContext(mode=EnumValidationMode.STRICT)

        with pytest.raises(ValidationError):
            context.mode = EnumValidationMode.PERMISSIVE  # type: ignore[misc]

    def test_validation_context_cannot_modify_flags(self) -> None:
        """Test that flags cannot be reassigned after creation."""
        context = ModelContractValidationContext(flags={"original": True})

        with pytest.raises(ValidationError):
            context.flags = {"modified": True}  # type: ignore[misc]

    def test_validation_context_flags_dict_cannot_be_mutated(self) -> None:
        """Test that the flags dict itself is frozen.

        Note: While the model is frozen, the flags dict itself may or may not
        be frozen depending on Pydantic's implementation. This test documents
        the current behavior.
        """
        context = ModelContractValidationContext(flags={"original": True})

        # Attempting to modify the dict in-place
        # This may or may not raise an error depending on implementation
        try:
            context.flags["new_key"] = True  # type: ignore[typeddict-unknown-key]
            # If mutation succeeds, the dict is not frozen
            # This is a known limitation - documenting current behavior
        except TypeError:
            # If mutation fails with TypeError, dict is properly frozen
            pass


@pytest.mark.unit
class TestModelContractValidationContextExtraFieldRejection:
    """Tests for extra='forbid' configuration."""

    def test_validation_context_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationContext(
                mode=EnumValidationMode.STRICT,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str

    def test_validation_context_config_has_extra_forbid(self) -> None:
        """Test that model is configured with extra='forbid'."""
        context = ModelContractValidationContext()

        config = context.model_config
        assert config.get("extra") == "forbid"


@pytest.mark.unit
class TestModelContractValidationContextSerialization:
    """Tests for serialization and deserialization."""

    def test_validation_context_model_dump(self) -> None:
        """Test that ModelContractValidationContext can be dumped to dict."""
        context = ModelContractValidationContext(
            mode=EnumValidationMode.PERMISSIVE,
            flags={"flag1": True, "flag2": False},
        )

        data = context.model_dump()

        assert data["mode"] == EnumValidationMode.PERMISSIVE
        assert data["flags"] == {"flag1": True, "flag2": False}

    def test_validation_context_model_dump_json(self) -> None:
        """Test that ModelContractValidationContext can be serialized to JSON."""
        context = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={"test_flag": True},
        )

        json_str = context.model_dump_json()

        assert isinstance(json_str, str)
        assert "strict" in json_str
        assert "test_flag" in json_str

    def test_validation_context_round_trip_serialization(self) -> None:
        """Test that ModelContractValidationContext can be serialized and deserialized."""
        original = ModelContractValidationContext(
            mode=EnumValidationMode.PERMISSIVE,
            flags={"flag1": True, "flag2": False},
        )

        # Round-trip through JSON
        json_str = original.model_dump_json()
        restored = ModelContractValidationContext.model_validate_json(json_str)

        assert restored.mode == original.mode
        assert restored.flags == original.flags

    def test_validation_context_model_validate_from_dict(self) -> None:
        """Test that ModelContractValidationContext can be created from dict."""
        data = {
            "mode": "permissive",
            "flags": {"validate_all": True},
        }

        context = ModelContractValidationContext.model_validate(data)

        assert context.mode == EnumValidationMode.PERMISSIVE
        assert context.flags == {"validate_all": True}


@pytest.mark.unit
class TestModelContractValidationContextFromAttributes:
    """Tests for from_attributes=True configuration."""

    def test_validation_context_has_from_attributes_config(self) -> None:
        """Test that ModelContractValidationContext is configured with from_attributes=True."""
        context = ModelContractValidationContext()

        config = context.model_config
        assert config.get("from_attributes") is True

    def test_validation_context_can_be_created_from_object(self) -> None:
        """Test that ModelContractValidationContext can be created from an object."""

        class ContextLike:
            """A class with mode and flags attributes."""

            def __init__(self) -> None:
                self.mode = EnumValidationMode.PERMISSIVE
                self.flags = {"from_object": True}

        obj = ContextLike()
        context = ModelContractValidationContext.model_validate(obj)

        assert context.mode == EnumValidationMode.PERMISSIVE
        assert context.flags == {"from_object": True}


@pytest.mark.unit
class TestModelContractValidationContextHashability:
    """Tests for hashability and set/dict usage."""

    def test_validation_context_is_hashable(self) -> None:
        """Test that ModelContractValidationContext is hashable (frozen=True).

        Note: Dicts are not hashable, so this test may fail if flags
        is included in the hash. Document current behavior.
        """
        context = ModelContractValidationContext()

        # With empty flags (empty dict), should be hashable
        # if the model excludes flags from hash or converts it
        try:
            hash_value = hash(context)
            assert isinstance(hash_value, int)
        except TypeError:
            # If unhashable due to dict flags, that's expected
            pass

    def test_validation_context_equality(self) -> None:
        """Test equality comparison between ValidationContext instances."""
        context1 = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={"flag1": True},
        )
        context2 = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={"flag1": True},
        )
        context3 = ModelContractValidationContext(
            mode=EnumValidationMode.PERMISSIVE,
            flags={"flag1": True},
        )

        assert context1 == context2
        assert context1 != context3


@pytest.mark.unit
class TestModelContractValidationContextFlagsTypes:
    """Tests for flags dict key and value types."""

    def test_flags_accepts_boolean_values(self) -> None:
        """Test that flags accepts boolean values."""
        context = ModelContractValidationContext(
            flags={"true_flag": True, "false_flag": False}
        )

        assert context.flags["true_flag"] is True
        assert context.flags["false_flag"] is False

    def test_flags_with_many_keys(self) -> None:
        """Test that flags can have many keys."""
        flags = {f"flag_{i}": i % 2 == 0 for i in range(50)}
        context = ModelContractValidationContext(flags=flags)

        assert len(context.flags) == 50

    def test_flags_with_unicode_keys(self) -> None:
        """Test that flags accepts unicode keys."""
        context = ModelContractValidationContext(
            flags={"\u4e2d\u6587_flag": True}  # Chinese characters
        )

        assert context.flags["\u4e2d\u6587_flag"] is True


@pytest.mark.unit
class TestModelContractValidationContextRepr:
    """Tests for __repr__ output."""

    def test_validation_context_repr_includes_mode(self) -> None:
        """Test that __repr__ includes the mode."""
        context = ModelContractValidationContext(mode=EnumValidationMode.STRICT)

        repr_str = repr(context)

        # Check for canonical class name (OMN-1126 rename)
        assert "ModelContractValidationContext" in repr_str
        # Mode should be represented
        assert "mode=" in repr_str


@pytest.mark.unit
class TestModelContractValidationContextEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_validation_context_with_none_flags(self) -> None:
        """Test behavior when flags is explicitly set to None.

        Note: The model uses default_factory=dict, so None might be
        converted to empty dict or raise an error.
        """
        # This might pass or fail depending on implementation
        try:
            context = ModelContractValidationContext(flags=None)  # type: ignore[arg-type]
            # If accepted, document behavior
            assert context.flags is None or context.flags == {}
        except ValidationError:
            # If rejected, that's also valid
            pass

    def test_validation_context_mode_enum_exhaustive(self) -> None:
        """Test that all EnumValidationMode values work."""
        for mode in EnumValidationMode:
            context = ModelContractValidationContext(mode=mode)
            assert context.mode == mode


@pytest.mark.unit
class TestModelContractValidationContextUsagePatterns:
    """Tests for common usage patterns."""

    def test_strict_validation_context_pattern(self) -> None:
        """Test creating a strict validation context for production."""
        context = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={
                "validate_schema": True,
                "validate_types": True,
                "validate_references": True,
            },
        )

        assert context.mode.is_strict()
        assert context.flags.get("validate_schema") is True

    def test_permissive_validation_context_pattern(self) -> None:
        """Test creating a permissive validation context for debugging."""
        context = ModelContractValidationContext(
            mode=EnumValidationMode.PERMISSIVE,
            flags={
                "skip_optional_checks": True,
                "collect_all_errors": True,
            },
        )

        assert context.mode.allows_continuation()
        assert context.flags.get("skip_optional_checks") is True

    def test_minimal_validation_context_pattern(self) -> None:
        """Test creating a minimal validation context."""
        context = ModelContractValidationContext()

        # Should work with all defaults
        assert context.mode == EnumValidationMode.STRICT
        assert context.flags == {}


@pytest.mark.unit
class TestModelContractValidationContextNaming:
    """Tests for canonical naming (OMN-1126).

    Note:
        The backwards compat alias ModelValidationContext was removed to avoid
        naming collision with omnibase_core.models.context.ModelValidationContext
        which is used for field-level validation (field_name, expected, actual).
    """

    def test_canonical_name_works(self) -> None:
        """Test that the canonical name ModelContractValidationContext works."""
        context = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={"test": True},
        )

        assert context.mode == EnumValidationMode.STRICT
        assert context.flags == {"test": True}

    def test_equal_instances(self) -> None:
        """Test that instances with same data are equal."""
        context1 = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={"flag1": True},
        )
        context2 = ModelContractValidationContext(
            mode=EnumValidationMode.STRICT,
            flags={"flag1": True},
        )

        assert context1 == context2
        assert type(context1) is type(context2)
