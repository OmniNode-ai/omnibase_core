# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed FSM metadata model for reducer operations.

ModelReducerFsmMetadata provides a typed, validated alternative to the
untyped metadata dicts that reducer FSM transitions historically emitted.
It encodes the 7-key contract defined in
``CONTRACT_DRIVEN_NODEREDUCER_V1_0.md`` / ``V1_0_4_DELTA.md``.

Design Rationale:
    Dict-based metadata is unsafe — key typos go undetected, values drift in
    type, and downstream consumers (dashboards, replay, verification) have no
    schema to validate against. A typed Pydantic model closes all three gaps
    while remaining cheap to convert to/from a plain dict at serialization
    boundaries (Kafka payloads, JSON columns, Claude Code hook envelopes).

Thread Safety:
    ModelReducerFsmMetadata is immutable (frozen=True) after creation, making
    it safe for concurrent read access.

See Also:
    - omnibase_core.models.reducer.model_reducer_output: Reducer output model
    - omnibase_core.models.reducer.model_reducer_context: Handler context
    - docs/architecture/CONTRACT_SYSTEM.md: Contract metadata requirements
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.typed_dict_reducer_fsm_metadata import (
    TypedDictReducerFsmMetadata,
)

__all__ = ["ModelReducerFsmMetadata"]


class ModelReducerFsmMetadata(BaseModel):
    """Typed FSM metadata for reducer transitions (7-key contract).

    Encodes the transition-level observability payload that reducer FSM
    handlers attach to their outputs. All seven keys come from the
    v1.0.4 metadata contract; no extra fields are allowed.

    Attributes:
        fsm_state: Current FSM state after the transition attempt. Always
            populated, including on failed transitions (where it equals the
            state the FSM remained in).
        fsm_previous_state: FSM state prior to the transition attempt.
            ``None`` when the reducer has just been initialized and there
            is no prior state (first event after construction).
        fsm_transition_success: Whether the transition was accepted and
            applied. ``False`` for guard failures, invalid events, or
            conflicting conditions.
        fsm_transition_name: Name of the attempted transition as declared
            in the FSM definition. ``None`` when no transition was dispatched
            (e.g. the event did not match any declared trigger).
        failure_reason: Human-readable reason the transition failed.
            ``None`` on successful transitions. Intended for operator
            dashboards and replay audits, not for branching logic.
        failed_conditions: Names of declarative conditions/guards that
            evaluated falsy and caused the transition to be rejected.
            ``None`` on successful transitions or when no conditions were
            evaluated (e.g. bad event type).
        error: Error message string if the transition raised an unexpected
            exception. Distinct from ``failure_reason``: ``failure_reason``
            describes an expected rejection, ``error`` describes an
            unexpected crash in guard or effect code.

    Thread Safety:
        Frozen and immutable after creation. Safe for concurrent read access.

    Example:
        >>> from omnibase_core.models.reducer import ModelReducerFsmMetadata
        >>>
        >>> # Successful transition
        >>> success = ModelReducerFsmMetadata(
        ...     fsm_state="PROCESSING",
        ...     fsm_previous_state="PENDING",
        ...     fsm_transition_success=True,
        ...     fsm_transition_name="start_processing",
        ... )
        >>>
        >>> # Failed transition due to guard
        >>> failed = ModelReducerFsmMetadata(
        ...     fsm_state="PENDING",
        ...     fsm_previous_state="PENDING",
        ...     fsm_transition_success=False,
        ...     fsm_transition_name="start_processing",
        ...     failure_reason="Guard not satisfied",
        ...     failed_conditions=["has_input_data"],
        ... )
        >>>
        >>> # Round-trip via dict
        >>> d = success.to_dict()
        >>> restored = ModelReducerFsmMetadata.from_dict(d)
        >>> assert restored == success
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    fsm_state: str = Field(
        description="Current FSM state after the transition attempt.",
    )
    fsm_previous_state: str | None = Field(
        default=None,
        description=(
            "FSM state prior to the transition attempt. None on the first "
            "event after reducer initialization."
        ),
    )
    fsm_transition_success: bool = Field(
        description="Whether the attempted transition was accepted and applied.",
    )
    fsm_transition_name: str | None = Field(
        default=None,
        description=(
            "Name of the attempted transition as declared in the FSM "
            "definition. None when no transition was dispatched."
        ),
    )
    failure_reason: str | None = Field(
        default=None,
        description=("Human-readable reason the transition failed. None on success."),
    )
    failed_conditions: list[str] | None = Field(
        default=None,
        description=(
            "Names of conditions/guards that evaluated falsy. None on "
            "success or when no conditions were evaluated."
        ),
    )
    error: str | None = Field(
        default=None,
        description=(
            "Error message if the transition raised an unexpected "
            "exception. Distinct from failure_reason, which describes an "
            "expected rejection."
        ),
    )

    def to_dict(self) -> TypedDictReducerFsmMetadata:
        """Serialize to a plain dict suitable for JSON / Kafka payloads.

        Returns:
            Dict containing all 7 contract keys. Optional fields are
            preserved as ``None`` (not elided) so downstream consumers
            can rely on a fixed shape.
        """
        payload = self.model_dump(mode="json")
        return TypedDictReducerFsmMetadata(
            fsm_state=payload["fsm_state"],
            fsm_previous_state=payload["fsm_previous_state"],
            fsm_transition_success=payload["fsm_transition_success"],
            fsm_transition_name=payload["fsm_transition_name"],
            failure_reason=payload["failure_reason"],
            failed_conditions=payload["failed_conditions"],
            error=payload["error"],
        )

    @classmethod
    def from_dict(cls, data: TypedDictReducerFsmMetadata) -> ModelReducerFsmMetadata:
        """Construct from a plain dict, validating the 7-key contract.

        Args:
            data: Dict containing the 7 contract keys. Extra keys raise
                ``ValidationError`` (enforced by ``extra='forbid'``).

        Returns:
            Validated ``ModelReducerFsmMetadata`` instance.

        Raises:
            pydantic.ValidationError: If required keys are missing, types
                are wrong, or extra keys are present.
        """
        return cls.model_validate(data)
