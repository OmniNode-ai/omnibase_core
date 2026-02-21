# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelPayloadProjectionIntent (OMN-2509).

Tests model construction, validation, immutability, and Protocol conformance.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.projectors.model_projection_intent import (
    ModelProjectionIntent,
)
from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)
from omnibase_core.models.reducer.payloads.model_payload_projection_intent import (
    ModelPayloadProjectionIntent,
)
from omnibase_core.models.reducer.payloads.model_protocol_intent_payload import (
    ProtocolIntentPayload,
)

# Module-level marker for all tests in this file
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MinimalEnvelope(BaseModel):
    """Minimal event envelope for test fixture use."""

    event_id: str


def _make_projection_intent(
    projector_key: str = "test_projector",
    event_type: str = "test.event.v1",
    correlation_id: UUID | None = None,
) -> ModelProjectionIntent:
    """Create a ModelProjectionIntent for testing."""
    return ModelProjectionIntent(
        projector_key=projector_key,
        event_type=event_type,
        envelope=_MinimalEnvelope(event_id="evt-001"),
        correlation_id=correlation_id or uuid4(),
    )


# ---------------------------------------------------------------------------
# Tests: Construction and field values
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntentConstruction:
    """Tests for model construction and default field values."""

    def test_construction_with_required_field(self) -> None:
        """Payload can be constructed with the required intent field."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent is pi

    def test_intent_type_is_projection_intent(self) -> None:
        """intent_type discriminator is always 'projection_intent'."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent_type == "projection_intent"

    def test_intent_type_default_applied(self) -> None:
        """intent_type default is applied even when not explicitly set."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        # Verify it equals the literal value
        assert payload.intent_type == "projection_intent"

    def test_projector_key_accessible_via_nested_intent(self) -> None:
        """projector_key from the nested intent is accessible."""
        pi = _make_projection_intent(projector_key="my_view_projector")
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent.projector_key == "my_view_projector"

    def test_event_type_accessible_via_nested_intent(self) -> None:
        """event_type from the nested intent is accessible."""
        pi = _make_projection_intent(event_type="workflow.completed.v2")
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent.event_type == "workflow.completed.v2"

    def test_correlation_id_accessible_via_nested_intent(self) -> None:
        """correlation_id from the nested intent is accessible."""
        corr_id = UUID("feedface-feed-face-feed-facefeedface")
        pi = _make_projection_intent(correlation_id=corr_id)
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent.correlation_id == corr_id


# ---------------------------------------------------------------------------
# Tests: Immutability
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntentImmutability:
    """Tests that the payload is frozen and immutable after construction."""

    def test_intent_type_cannot_be_reassigned(self) -> None:
        """Attempting to mutate intent_type raises an error."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        with pytest.raises(Exception):
            payload.intent_type = "other"  # type: ignore[misc]

    def test_intent_cannot_be_reassigned(self) -> None:
        """Attempting to mutate the intent field raises an error."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        with pytest.raises(Exception):
            payload.intent = _make_projection_intent()  # type: ignore[misc]

    def test_payload_is_frozen_pydantic_model(self) -> None:
        """Payload model_config has frozen=True."""
        assert ModelPayloadProjectionIntent.model_config.get("frozen") is True


# ---------------------------------------------------------------------------
# Tests: Inheritance and protocol conformance
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntentInheritance:
    """Tests for class hierarchy and protocol conformance."""

    def test_inherits_from_model_intent_payload_base(self) -> None:
        """ModelPayloadProjectionIntent inherits ModelIntentPayloadBase."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert isinstance(payload, ModelIntentPayloadBase)

    def test_satisfies_protocol_intent_payload(self) -> None:
        """Payload satisfies the ProtocolIntentPayload structural protocol."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert isinstance(payload, ProtocolIntentPayload)

    def test_intent_type_attribute_accessible_as_protocol_property(self) -> None:
        """intent_type is accessible as required by ProtocolIntentPayload."""
        pi = _make_projection_intent()
        payload: ProtocolIntentPayload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent_type == "projection_intent"


# ---------------------------------------------------------------------------
# Tests: Validation
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntentValidation:
    """Tests for model validation rules."""

    def test_missing_intent_raises_validation_error(self) -> None:
        """Omitting the required intent field raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelPayloadProjectionIntent()  # type: ignore[call-arg]

    def test_none_intent_raises_validation_error(self) -> None:
        """Passing None for intent raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelPayloadProjectionIntent(intent=None)  # type: ignore[arg-type]

    def test_wrong_type_for_intent_raises_validation_error(self) -> None:
        """Passing a non-ModelProjectionIntent for intent raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            ModelPayloadProjectionIntent(intent="not-a-projection-intent")  # type: ignore[arg-type]

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields are rejected (extra='forbid' inherited from base)."""
        pi = _make_projection_intent()
        with pytest.raises(ValidationError):
            ModelPayloadProjectionIntent(intent=pi, unknown_field="value")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Tests: Serialization
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntentSerialization:
    """Tests for model serialization behavior."""

    def test_model_dump_includes_intent_type(self) -> None:
        """model_dump output includes the intent_type discriminator."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        dumped = payload.model_dump()
        assert "intent_type" in dumped
        assert dumped["intent_type"] == "projection_intent"

    def test_model_dump_includes_intent_fields(self) -> None:
        """model_dump output includes the nested intent fields."""
        pi = _make_projection_intent(projector_key="serialization_projector")
        payload = ModelPayloadProjectionIntent(intent=pi)
        dumped = payload.model_dump()
        assert "intent" in dumped
        assert dumped["intent"]["projector_key"] == "serialization_projector"

    def test_model_fields_set_is_correct(self) -> None:
        """model_fields contains exactly the expected field names."""
        expected_fields = {"intent_type", "intent"}
        actual_fields = set(ModelPayloadProjectionIntent.model_fields.keys())
        assert actual_fields == expected_fields


# ---------------------------------------------------------------------------
# Tests: Public API export
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntentExport:
    """Tests that ModelPayloadProjectionIntent is properly exported."""

    def test_exported_from_payloads_package(self) -> None:
        """ModelPayloadProjectionIntent is importable from payloads package."""
        from omnibase_core.models.reducer.payloads import (
            ModelPayloadProjectionIntent as Imported,
        )

        assert Imported is ModelPayloadProjectionIntent

    def test_in_payloads_all(self) -> None:
        """ModelPayloadProjectionIntent is listed in payloads __all__."""
        import omnibase_core.models.reducer.payloads as payloads_pkg

        assert "ModelPayloadProjectionIntent" in payloads_pkg.__all__
