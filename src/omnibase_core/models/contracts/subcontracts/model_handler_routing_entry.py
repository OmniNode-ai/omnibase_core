# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Handler Routing Entry Model — canonical live routing shape (OMN-12547 S-1c).

Replaces the dead routing_key/handler_key shape with the live infra shape
(OMN-7654). Each entry identifies a handler class reference plus optional
discriminators used by the runtime dispatcher:

  - event_model: for payload_type_match routing (class name + module)
  - operation: for operation_match routing (e.g. "tick", "store")
  - event_type: optional dot-path alias for bus-level event_type discrimination;
    also used as the pattern key for topic_pattern routing strategy
  - message_category: per-handler category override (EVENT, COMMAND, INTENT)

The extra="ignore" policy tolerates old YAML fields (routing_key, handler_key,
priority, output_events, callable, lazy_import) during transition. A follow-up
PR will enforce extra="forbid" once all consumers carry the live shape.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dispatch.model_handler_ref import ModelHandlerRef


class ModelHandlerRoutingEntry(BaseModel):
    """Single handler routing entry in the canonical live routing shape (OMN-12547)."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",  # Tolerates old YAML fields during migration
        from_attributes=True,
    )

    handler: ModelHandlerRef = Field(..., description="Handler class reference")
    event_model: ModelHandlerRef | None = Field(
        default=None,
        description="Event model reference (payload_type_match strategy)",
    )
    operation: str | None = Field(
        default=None,
        description="Operation name (operation_match strategy)",
    )
    event_type: str | None = Field(
        default=None,
        description=(
            "Optional contract-declared event_type alias "
            "(e.g. 'omnimarket.pr-lifecycle-orchestrator-start'). When present, "
            "the dispatcher is indexed under this wire-level string in addition to "
            "event_model.name, so publishers that set ModelEventEnvelope.event_type "
            "to the dot-path string resolve to the handler without needing the "
            "Python class name on the wire (OMN-9215). Also used as the pattern key "
            "for topic_pattern routing strategy."
        ),
    )
    message_category: str | None = Field(
        default=None,
        description=(
            "Optional per-handler message category override from contract YAML "
            "(EVENT, COMMAND, or INTENT). Required for mixed-topic contracts so "
            "command handlers do not inherit the category of the contract's first "
            "subscribed topic."
        ),
    )
    # dispatch-surface-test-ok: additive optional field; inert in omnibase_core (no entry.topic consumer here — routing_map_builder that reads it lives in a sibling repo and is covered by that repo's real-dispatch tests when RuntimeDispatch lands). Model round-trip is unit-tested. (OMN-14771)
    topic: str | None = Field(
        default=None,
        description=(
            "Optional per-entry subscribe topic that owns this route (OMN-14771). "
            "When present, RuntimeDispatch route resolution "
            "(routing_map_builder._resolve_owning_entry) uses this to map a single "
            "entry to its owning topic instead of failing closed on topic-agnostic "
            "multiplexed orchestrator entries. Additive and backward-compatible: "
            "existing entries omit it and default to None, leaving the legacy "
            "payload_type_match path (which resolves the topic from the contract's "
            "subscribe_topics list) unaffected."
        ),
    )
