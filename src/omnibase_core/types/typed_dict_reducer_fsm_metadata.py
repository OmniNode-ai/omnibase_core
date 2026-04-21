# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict shape of the 7-key reducer FSM metadata contract.

Used at serialization boundaries (Kafka payloads, JSON columns) where a
``ModelReducerFsmMetadata`` instance must be carried as a plain mapping.
All seven contract keys are present; optional fields surface as ``None``
rather than being elided so consumers can rely on a fixed shape.

Follows ONEX one-model-per-file and TypedDict naming conventions
(see omnibase_core.models.reducer.model_reducer_fsm_metadata for the
validated Pydantic counterpart).
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictReducerFsmMetadata(TypedDict):
    """Typed dict shape of the 7-key FSM metadata contract.

    Mirrors ``ModelReducerFsmMetadata`` field-for-field. Required at
    serialization boundaries (Kafka payloads, JSON columns) where the
    model must be carried as a plain mapping. All seven contract keys
    appear; optional fields surface as ``None`` rather than being elided
    so downstream consumers can rely on a fixed shape.
    """

    fsm_state: str
    fsm_previous_state: str | None
    fsm_transition_success: bool
    fsm_transition_name: str | None
    failure_reason: str | None
    failed_conditions: list[str] | None
    error: str | None


__all__ = ["TypedDictReducerFsmMetadata"]
