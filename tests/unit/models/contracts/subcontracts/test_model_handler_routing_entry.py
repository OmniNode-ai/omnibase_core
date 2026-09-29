# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelHandlerRoutingEntry (OMN-14771 S8 PR2).

Covers the additive ``topic`` field that RuntimeDispatch route resolution
(routing_map_builder._resolve_owning_entry) reads as ``entry.topic``:

- an entry declaring ``topic`` round-trips through model_dump/model_validate,
- an entry omitting ``topic`` defaults to None (backward compatibility),
- the field name/type match the PR2<->PR3 seam exactly ("topic": str | None).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_result_transport import EnumResultTransport
from omnibase_core.models.contracts.subcontracts.model_handler_routing_entry import (
    ModelHandlerRoutingEntry,
)
from omnibase_core.models.dispatch.model_handler_ref import ModelHandlerRef

pytestmark = pytest.mark.unit


def _handler_ref() -> ModelHandlerRef:
    return ModelHandlerRef(
        name="HandlerDelegationRequest",
        module="omnimarket.nodes.node_delegation_orchestrator.handlers",
    )


def _event_model_ref() -> ModelHandlerRef:
    return ModelHandlerRef(
        name="ModelDelegationRequest",
        module="omnimarket.models",
    )


class TestHandlerRoutingEntryTopic:
    """The additive ``topic`` field (OMN-14771 PR2 half of the PR2<->PR3 seam)."""

    def test_topic_defaults_to_none_when_omitted(self) -> None:
        """Existing entries that omit ``topic`` default to None (backward-compatible)."""
        entry = ModelHandlerRoutingEntry(
            handler=_handler_ref(),
            event_model=_event_model_ref(),
        )
        assert entry.topic is None

    def test_topic_round_trips_through_dump_and_validate(self) -> None:
        """An entry declaring ``topic`` round-trips losslessly."""
        topic = "omnimarket.delegation-orchestrator.routing-decision"
        entry = ModelHandlerRoutingEntry(
            handler=_handler_ref(),
            event_model=_event_model_ref(),
            topic=topic,
        )
        assert entry.topic == topic

        dumped = entry.model_dump()
        assert dumped["topic"] == topic

        rehydrated = ModelHandlerRoutingEntry.model_validate(dumped)
        assert rehydrated.topic == topic
        assert rehydrated == entry

    def test_topic_field_is_optional_str(self) -> None:
        """Field name/type match the PR2<->PR3 seam: name 'topic', type str | None."""
        field = ModelHandlerRoutingEntry.model_fields["topic"]
        # Optional (has default None).
        assert field.default is None
        # str | None annotation.
        assert field.annotation == (str | None)


class TestHandlerRoutingEntryResultTransport:
    """Operation result transport is explicit and fail-closed (OMN-17859)."""

    def test_result_transport_defaults_to_response_when_omitted(self) -> None:
        entry = ModelHandlerRoutingEntry(
            handler=_handler_ref(), event_model=_event_model_ref()
        )

        assert entry.result_transport is EnumResultTransport.RESPONSE

    def test_event_fanout_round_trips_without_adding_a_topic_field(self) -> None:
        entry = ModelHandlerRoutingEntry(
            handler=_handler_ref(),
            event_model=_event_model_ref(),
            result_transport=EnumResultTransport.EVENT_FANOUT,
        )

        assert (
            entry.model_dump()["result_transport"] is EnumResultTransport.EVENT_FANOUT
        )
        assert (
            ModelHandlerRoutingEntry.model_validate(entry.model_dump()).result_transport
            is EnumResultTransport.EVENT_FANOUT
        )

    def test_unknown_result_transport_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="result_transport"):
            ModelHandlerRoutingEntry(
                handler=_handler_ref(),
                event_model=_event_model_ref(),
                result_transport="publish_everywhere",  # type: ignore[arg-type]
            )
