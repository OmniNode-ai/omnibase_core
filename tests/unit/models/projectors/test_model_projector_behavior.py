# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProjectorBehavior.

Tests cover:
1. Valid behavior creation
2. Mode validation (upsert, insert_only, append only)
3. Default mode is "upsert"
4. Upsert key validation
5. Idempotency config integration
6. Frozen/immutable behavior
7. Extra fields rejected
8. Serialization roundtrip
9. Upsert mode without key emits warning
"""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelProjectorBehaviorCreation:
    """Tests for ModelProjectorBehavior creation and validation."""

    def test_valid_behavior_minimal(self) -> None:
        """Valid behavior with defaults."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        behavior = ModelProjectorBehavior()

        assert behavior.mode == "upsert"
        assert behavior.upsert_key is None
        assert behavior.idempotency is None

    def test_valid_behavior_with_upsert_key(self) -> None:
        """Valid behavior with upsert key specified."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")

        assert behavior.mode == "upsert"
        assert behavior.upsert_key == "node_id"

    def test_valid_insert_only_mode(self) -> None:
        """Valid insert_only mode."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        behavior = ModelProjectorBehavior(mode="insert_only")

        assert behavior.mode == "insert_only"

    def test_valid_append_mode(self) -> None:
        """Valid append mode."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        behavior = ModelProjectorBehavior(mode="append")

        assert behavior.mode == "append"

    def test_valid_behavior_with_idempotency(self) -> None:
        """Valid behavior with idempotency config."""
        from omnibase_core.models.projectors import (
            ModelIdempotencyConfig,
            ModelProjectorBehavior,
        )

        idempotency = ModelIdempotencyConfig(enabled=True, key="sequence_number")
        behavior = ModelProjectorBehavior(mode="upsert", idempotency=idempotency)

        assert behavior.idempotency is not None
        assert behavior.idempotency.enabled is True
        assert behavior.idempotency.key == "sequence_number"


@pytest.mark.unit
class TestModelProjectorBehaviorModeValidation:
    """Tests for mode validation."""

    def test_invalid_mode_rejected(self) -> None:
        """Only upsert, insert_only, append are allowed."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorBehavior(mode="replace")  # type: ignore[arg-type]

        error_str = str(exc_info.value).lower()
        assert "mode" in error_str or "replace" in error_str

    def test_mode_is_case_sensitive(self) -> None:
        """Mode must be lowercase."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        with pytest.raises(ValidationError):
            ModelProjectorBehavior(mode="UPSERT")  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelProjectorBehaviorImmutability:
    """Tests for frozen/immutable behavior."""

    def test_behavior_is_frozen(self) -> None:
        """Behavior should be immutable after creation."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError):
            behavior.mode = "append"  # type: ignore[misc]

    def test_behavior_is_hashable(self) -> None:
        """Frozen behavior should be hashable."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        behavior = ModelProjectorBehavior(mode="upsert")

        hash_value = hash(behavior)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelProjectorBehaviorExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorBehavior(
                mode="upsert",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelProjectorBehaviorSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.projectors import (
            ModelIdempotencyConfig,
            ModelProjectorBehavior,
        )

        idempotency = ModelIdempotencyConfig(enabled=True, key="event_id")
        original = ModelProjectorBehavior(
            mode="upsert",
            upsert_key="node_id",
            idempotency=idempotency,
        )
        data = original.model_dump()
        restored = ModelProjectorBehavior.model_validate(data)

        assert restored == original

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        original = ModelProjectorBehavior(mode="insert_only")
        json_str = original.model_dump_json()
        restored = ModelProjectorBehavior.model_validate_json(json_str)

        assert restored == original


@pytest.mark.unit
class TestModelProjectorBehaviorUpsertKeyWarning:
    """Tests for upsert_key validation warnings."""

    def test_upsert_mode_without_key_emits_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When mode='upsert' and upsert_key is None, a warning should be logged."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        with caplog.at_level(logging.WARNING):
            behavior = ModelProjectorBehavior(mode="upsert")

        # Verify model is created successfully
        assert behavior.mode == "upsert"
        assert behavior.upsert_key is None

        # Verify warning was logged
        assert len(caplog.records) >= 1
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any(
            "upsert_key not specified" in msg and "Primary key will be used" in msg
            for msg in warning_messages
        ), f"Expected warning about upsert_key, got: {warning_messages}"

    def test_upsert_mode_with_key_no_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When mode='upsert' and upsert_key is provided, no warning should be logged."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        with caplog.at_level(logging.WARNING):
            behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")

        # Verify model is created successfully
        assert behavior.mode == "upsert"
        assert behavior.upsert_key == "node_id"

        # Verify no warning about upsert_key was logged
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert not any("upsert_key not specified" in msg for msg in warning_messages), (
            f"Unexpected warning about upsert_key: {warning_messages}"
        )

    def test_non_upsert_modes_no_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Non-upsert modes should not emit upsert_key warnings."""
        from omnibase_core.models.projectors import ModelProjectorBehavior

        with caplog.at_level(logging.WARNING):
            ModelProjectorBehavior(mode="insert_only")
            ModelProjectorBehavior(mode="append")

        # Verify no warning about upsert_key was logged
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert not any("upsert_key not specified" in msg for msg in warning_messages), (
            f"Unexpected warning about upsert_key: {warning_messages}"
        )
