"""Tests for ModelIdempotencyConfig.

Tests cover:
1. Valid configuration creation
2. Frozen/immutable behavior
3. Extra fields rejected (extra="forbid")
4. Default values
5. Field validation
6. Serialization roundtrip
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelIdempotencyConfigCreation:
    """Tests for ModelIdempotencyConfig creation and validation."""

    def test_valid_config_with_all_fields(self) -> None:
        """Valid configuration with all fields specified."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        config = ModelIdempotencyConfig(enabled=True, key="sequence_number")

        assert config.enabled is True
        assert config.key == "sequence_number"

    def test_valid_config_with_disabled(self) -> None:
        """Valid configuration with idempotency disabled."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        config = ModelIdempotencyConfig(enabled=False, key="event_id")

        assert config.enabled is False
        assert config.key == "event_id"

    def test_default_enabled_value(self) -> None:
        """Default enabled value is True."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        config = ModelIdempotencyConfig(key="sequence_number")

        assert config.enabled is True

    def test_key_is_required(self) -> None:
        """Key field is required."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelIdempotencyConfig()

        assert "key" in str(exc_info.value)


@pytest.mark.unit
class TestModelIdempotencyConfigImmutability:
    """Tests for frozen/immutable behavior."""

    def test_config_is_frozen(self) -> None:
        """Config should be immutable after creation."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        config = ModelIdempotencyConfig(enabled=True, key="sequence_number")

        with pytest.raises(ValidationError):
            config.enabled = False  # type: ignore[misc]

    def test_config_is_hashable(self) -> None:
        """Frozen config should be hashable."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        config = ModelIdempotencyConfig(enabled=True, key="sequence_number")

        # Should not raise
        hash_value = hash(config)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelIdempotencyConfigExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected (extra='forbid')."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelIdempotencyConfig(
                enabled=True,
                key="sequence_number",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelIdempotencyConfigSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        original = ModelIdempotencyConfig(enabled=True, key="sequence_number")
        data = original.model_dump()
        restored = ModelIdempotencyConfig.model_validate(data)

        assert restored == original

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelIdempotencyConfig

        original = ModelIdempotencyConfig(enabled=False, key="event_id")
        json_str = original.model_dump_json()
        restored = ModelIdempotencyConfig.model_validate_json(json_str)

        assert restored == original
