# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Test-only reducer fixture for OMN-8946 state-sink wiring.

Mirrors the real reducer handler convention in
omnimarket/src/omnimarket/nodes/node_loop_state_reducer/handlers/handler_loop_state.py:96-110:
- pure `delta(state, event) -> (new_state, intents[])`
- `handle()` is a RuntimeLocal-protocol shim that wraps the tuple in a dict

This fixture is test-only. Production handlers MUST NOT import from it.
"""

from __future__ import annotations

from pydantic import BaseModel


class ModelProofReducerInput(BaseModel):
    """Test-only input. Not a production type."""

    counter_delta: int = 0


class ModelProofReducerState(BaseModel):
    """Test-only state. Not a production type."""

    counter: int = 0


class HandlerProofReducer:
    """Test-only reducer. Pure delta, dict-shape handle() shim."""

    def delta(
        self,
        state: ModelProofReducerState,
        event: ModelProofReducerInput,
    ) -> tuple[ModelProofReducerState, list[dict]]:
        """Pure: no I/O, no env reads, no bus publishes."""
        new_state = ModelProofReducerState(counter=state.counter + event.counter_delta)
        return new_state, []

    def handle(self, request: ModelProofReducerInput) -> dict:
        """RuntimeLocal-protocol shim. Wraps delta() tuple in dict convention."""
        initial = ModelProofReducerState(counter=0)
        new_state, intents = self.delta(initial, request)
        return {
            "state": new_state.model_dump(mode="json"),
            "intents": intents,
        }
