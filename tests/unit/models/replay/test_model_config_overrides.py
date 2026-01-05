# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelConfigOverride and ModelConfigOverrideSet.

Tests cover:
- Model immutability (frozen)
- Field validation (path min_length)
- Default values
- Injection point grouping (by_injection_point property)
- Immutable update pattern (with_override method)
- Serialization roundtrip (JSON export/import)

.. versionadded:: 0.4.0
    Added as part of Configuration Override Injection (OMN-1205)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from omnibase_core.models.replay import ModelConfigOverride


@pytest.fixture
def handler_config_override() -> ModelConfigOverride:
    """Create a sample handler config override."""
    from omnibase_core.enums.replay.enum_override_injection_point import (
        EnumOverrideInjectionPoint,
    )
    from omnibase_core.models.replay import ModelConfigOverride

    return ModelConfigOverride(
        path="llm.temperature",
        value=0.7,
        injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
    )


@pytest.fixture
def environment_override() -> ModelConfigOverride:
    """Create a sample environment override."""
    from omnibase_core.enums.replay.enum_override_injection_point import (
        EnumOverrideInjectionPoint,
    )
    from omnibase_core.models.replay import ModelConfigOverride

    return ModelConfigOverride(
        path="API_KEY",
        value="secret-key-123",
        injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
    )


@pytest.fixture
def context_override() -> ModelConfigOverride:
    """Create a sample context override."""
    from omnibase_core.enums.replay.enum_override_injection_point import (
        EnumOverrideInjectionPoint,
    )
    from omnibase_core.models.replay import ModelConfigOverride

    return ModelConfigOverride(
        path="replay.timeout_seconds",
        value=60,
        injection_point=EnumOverrideInjectionPoint.CONTEXT,
    )


@pytest.mark.unit
class TestModelConfigOverrideCreation:
    """Test ModelConfigOverride creation and defaults."""

    def test_create_with_defaults(self) -> None:
        """Can create override with default injection point."""
        from omnibase_core.enums.replay.enum_override_injection_point import (
            EnumOverrideInjectionPoint,
        )
        from omnibase_core.models.replay import ModelConfigOverride

        override = ModelConfigOverride(path="test.path", value=42)
        assert override.path == "test.path"
        assert override.value == 42
        assert override.injection_point == EnumOverrideInjectionPoint.HANDLER_CONFIG

    def test_create_with_explicit_injection_point(self) -> None:
        """Can specify injection point explicitly."""
        from omnibase_core.enums.replay.enum_override_injection_point import (
            EnumOverrideInjectionPoint,
        )
        from omnibase_core.models.replay import ModelConfigOverride

        override = ModelConfigOverride(
            path="API_KEY",
            value="secret",
            injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
        )
        assert override.injection_point == EnumOverrideInjectionPoint.ENVIRONMENT

    def test_create_with_complex_value(self) -> None:
        """Can create override with complex nested value."""
        from omnibase_core.models.replay import ModelConfigOverride

        complex_value: dict[str, Any] = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }
        override = ModelConfigOverride(path="config.section", value=complex_value)
        assert override.value == complex_value

    def test_create_with_none_value(self) -> None:
        """Can create override with None value (to clear a config)."""
        from omnibase_core.models.replay import ModelConfigOverride

        override = ModelConfigOverride(path="optional.field", value=None)
        assert override.value is None


@pytest.mark.unit
class TestModelConfigOverrideImmutability:
    """Test ModelConfigOverride immutability characteristics."""

    def test_model_is_frozen(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Test that ModelConfigOverride is frozen (immutable)."""
        with pytest.raises(ValidationError):
            handler_config_override.path = "modified.path"

    def test_cannot_modify_value(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Test that value field cannot be reassigned."""
        with pytest.raises(ValidationError):
            handler_config_override.value = 999

    def test_cannot_modify_injection_point(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Test that injection_point field cannot be reassigned."""
        from omnibase_core.enums.replay.enum_override_injection_point import (
            EnumOverrideInjectionPoint,
        )

        with pytest.raises(ValidationError):
            handler_config_override.injection_point = (
                EnumOverrideInjectionPoint.ENVIRONMENT
            )


@pytest.mark.unit
class TestModelConfigOverrideValidation:
    """Test ModelConfigOverride field validation."""

    def test_path_min_length_empty_string(self) -> None:
        """Path must be at least 1 character - empty string rejected."""
        from omnibase_core.models.replay import ModelConfigOverride

        with pytest.raises(ValidationError) as exc_info:
            ModelConfigOverride(path="", value=1)

        assert "path" in str(exc_info.value).lower()

    def test_path_min_length_single_char_valid(self) -> None:
        """Path with single character is valid."""
        from omnibase_core.models.replay import ModelConfigOverride

        override = ModelConfigOverride(path="x", value=1)
        assert override.path == "x"

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        from omnibase_core.models.replay import ModelConfigOverride

        with pytest.raises(ValidationError) as exc_info:
            ModelConfigOverride(
                path="test",
                value=1,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )

    def test_path_required(self) -> None:
        """Test that path is required."""
        from omnibase_core.models.replay import ModelConfigOverride

        with pytest.raises(ValidationError) as exc_info:
            ModelConfigOverride(value=1)  # type: ignore[call-arg]

        assert "path" in str(exc_info.value)

    def test_value_required(self) -> None:
        """Test that value is required."""
        from omnibase_core.models.replay import ModelConfigOverride

        with pytest.raises(ValidationError) as exc_info:
            ModelConfigOverride(path="test")  # type: ignore[call-arg]

        assert "value" in str(exc_info.value)


@pytest.mark.unit
class TestModelConfigOverrideSerialization:
    """Test ModelConfigOverride serialization and deserialization."""

    def test_serialization_roundtrip(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Test that model can be serialized and deserialized."""
        from omnibase_core.models.replay import ModelConfigOverride

        # Serialize to dict
        data = handler_config_override.model_dump()

        # Deserialize back
        restored = ModelConfigOverride.model_validate(data)

        assert restored.path == handler_config_override.path
        assert restored.value == handler_config_override.value
        assert restored.injection_point == handler_config_override.injection_point

    def test_json_serialization_roundtrip(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Test that model can be serialized to JSON and back."""
        from omnibase_core.models.replay import ModelConfigOverride

        # Serialize to JSON
        json_str = handler_config_override.model_dump_json()

        # Deserialize back
        restored = ModelConfigOverride.model_validate_json(json_str)

        assert restored.path == handler_config_override.path
        assert restored.value == handler_config_override.value


@pytest.mark.unit
class TestModelConfigOverrideSetCreation:
    """Test ModelConfigOverrideSet creation."""

    def test_create_empty(self) -> None:
        """Can create empty override set."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet()
        assert len(override_set.overrides) == 0

    def test_create_with_single_override(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Can create with single override."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet(overrides=(handler_config_override,))
        assert len(override_set.overrides) == 1
        assert override_set.overrides[0] == handler_config_override

    def test_create_with_multiple_overrides(
        self,
        handler_config_override: ModelConfigOverride,
        environment_override: ModelConfigOverride,
        context_override: ModelConfigOverride,
    ) -> None:
        """Can create with multiple overrides."""
        overrides = (
            handler_config_override,
            environment_override,
            context_override,
        )
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet(overrides=overrides)
        assert len(override_set.overrides) == 3


@pytest.mark.unit
class TestModelConfigOverrideSetImmutability:
    """Test ModelConfigOverrideSet immutability characteristics."""

    def test_model_is_frozen(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """Test that ModelConfigOverrideSet is frozen (immutable)."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet(overrides=(handler_config_override,))
        with pytest.raises(ValidationError):
            override_set.overrides = ()


@pytest.mark.unit
class TestModelConfigOverrideSetByInjectionPoint:
    """Test ModelConfigOverrideSet.by_injection_point property."""

    def test_by_injection_point_groups_correctly(
        self,
        handler_config_override: ModelConfigOverride,
        environment_override: ModelConfigOverride,
        context_override: ModelConfigOverride,
    ) -> None:
        """by_injection_point property groups overrides by type."""
        from omnibase_core.enums.replay.enum_override_injection_point import (
            EnumOverrideInjectionPoint,
        )
        from omnibase_core.models.replay import (
            ModelConfigOverride,
            ModelConfigOverrideSet,
        )

        # Add another handler config override
        second_handler = ModelConfigOverride(
            path="llm.max_tokens",
            value=1000,
            injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        )
        overrides = (
            handler_config_override,
            environment_override,
            context_override,
            second_handler,
        )
        override_set = ModelConfigOverrideSet(overrides=overrides)
        by_point = override_set.by_injection_point

        assert len(by_point[EnumOverrideInjectionPoint.HANDLER_CONFIG]) == 2
        assert len(by_point[EnumOverrideInjectionPoint.ENVIRONMENT]) == 1
        assert len(by_point[EnumOverrideInjectionPoint.CONTEXT]) == 1

    def test_by_injection_point_empty_set(self) -> None:
        """by_injection_point returns empty dict for empty set."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet()
        by_point = override_set.by_injection_point

        assert by_point == {}

    def test_by_injection_point_single_type_only(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """by_injection_point works with single injection point type."""
        from omnibase_core.enums.replay.enum_override_injection_point import (
            EnumOverrideInjectionPoint,
        )
        from omnibase_core.models.replay import (
            ModelConfigOverride,
            ModelConfigOverrideSet,
        )

        second_handler = ModelConfigOverride(
            path="another.path",
            value="value",
            injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        )
        override_set = ModelConfigOverrideSet(
            overrides=(handler_config_override, second_handler)
        )
        by_point = override_set.by_injection_point

        assert len(by_point) == 1
        assert len(by_point[EnumOverrideInjectionPoint.HANDLER_CONFIG]) == 2


@pytest.mark.unit
class TestModelConfigOverrideSetWithOverride:
    """Test ModelConfigOverrideSet.with_override method."""

    def test_with_override_returns_new_set(
        self, handler_config_override: ModelConfigOverride
    ) -> None:
        """with_override returns new set (immutable update)."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        original = ModelConfigOverrideSet()
        updated = original.with_override(handler_config_override)

        assert len(original.overrides) == 0  # Original unchanged
        assert len(updated.overrides) == 1
        assert updated is not original

    def test_with_override_appends_to_existing(
        self,
        handler_config_override: ModelConfigOverride,
        environment_override: ModelConfigOverride,
    ) -> None:
        """with_override appends to existing overrides."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        original = ModelConfigOverrideSet(overrides=(handler_config_override,))
        updated = original.with_override(environment_override)

        assert len(original.overrides) == 1  # Original unchanged
        assert len(updated.overrides) == 2
        assert updated.overrides[0] == handler_config_override
        assert updated.overrides[1] == environment_override

    def test_with_override_preserves_order(
        self,
        handler_config_override: ModelConfigOverride,
        environment_override: ModelConfigOverride,
        context_override: ModelConfigOverride,
    ) -> None:
        """with_override preserves insertion order."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        set1 = ModelConfigOverrideSet().with_override(handler_config_override)
        set2 = set1.with_override(environment_override)
        set3 = set2.with_override(context_override)

        assert set3.overrides[0] == handler_config_override
        assert set3.overrides[1] == environment_override
        assert set3.overrides[2] == context_override


@pytest.mark.unit
class TestModelConfigOverrideSetSerialization:
    """Test ModelConfigOverrideSet serialization and deserialization."""

    def test_serialization_roundtrip(
        self,
        handler_config_override: ModelConfigOverride,
        environment_override: ModelConfigOverride,
    ) -> None:
        """Test that model can be serialized and deserialized."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet(
            overrides=(handler_config_override, environment_override)
        )

        # Serialize to dict
        data = override_set.model_dump()

        # Deserialize back
        restored = ModelConfigOverrideSet.model_validate(data)

        assert len(restored.overrides) == 2
        assert restored.overrides[0].path == handler_config_override.path
        assert restored.overrides[1].path == environment_override.path

    def test_json_serialization_roundtrip(
        self,
        handler_config_override: ModelConfigOverride,
        environment_override: ModelConfigOverride,
    ) -> None:
        """Test that model can be serialized to JSON and back."""
        from omnibase_core.models.replay import ModelConfigOverrideSet

        override_set = ModelConfigOverrideSet(
            overrides=(handler_config_override, environment_override)
        )

        # Serialize to JSON
        json_str = override_set.model_dump_json()

        # Deserialize back
        restored = ModelConfigOverrideSet.model_validate_json(json_str)

        assert len(restored.overrides) == 2
