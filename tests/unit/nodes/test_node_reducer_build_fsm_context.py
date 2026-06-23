# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeReducer._build_fsm_context (OMN-592, BETA).

Verifies the extracted context-construction method:

* builds the FSM execution context from a ``ModelReducerInput``
* merges ``metadata`` + ``input_data`` + ``operation_id`` into the context
* drops reserved ``_fsm_*``-prefixed keys (never overwrites system context)
  and emits a single WARNING ``log_event`` intent naming them

Spec reference: CONTRACT_DRIVEN_NODEREDUCER_V1_0.md — Context Construction.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.payloads.model_payload_log_event import (
    ModelPayloadLogEvent,
)
from omnibase_core.nodes.node_reducer import (
    _FSM_RESERVED_CONTEXT_PREFIX,
    NodeReducer,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def node() -> NodeReducer[int, list[int]]:
    """A bare NodeReducer — _build_fsm_context reads only the input arg."""
    return NodeReducer(ModelONEXContainer())


def _make_input(
    *, metadata: ModelReducerMetadata, data: list[int] | None = None
) -> ModelReducerInput[int]:
    return ModelReducerInput(
        data=data if data is not None else [1, 2, 3],
        reduction_type=EnumReductionType.AGGREGATE,
        operation_id=uuid4(),
        metadata=metadata,
    )


def test_build_context_includes_system_keys(node: NodeReducer[int, list[int]]) -> None:
    """Context always carries input_data, reduction_type, and operation_id."""
    input_data = _make_input(metadata=ModelReducerMetadata(trigger="start"))

    context, warnings = node._build_fsm_context(input_data)

    assert warnings == ()
    assert context["input_data"] == [1, 2, 3]
    assert context["reduction_type"] == EnumReductionType.AGGREGATE.value
    assert context["operation_id"] == str(input_data.operation_id)


def test_build_context_merges_user_metadata(
    node: NodeReducer[int, list[int]],
) -> None:
    """Non-reserved metadata fields (declared + extra) merge into the context."""
    metadata = ModelReducerMetadata(trigger="start", user_id="abc", attempt=2)
    input_data = _make_input(metadata=metadata)

    context, warnings = node._build_fsm_context(input_data)

    assert warnings == ()
    # Declared metadata field present.
    assert context["trigger"] == "start"
    # Extra (extra="allow") metadata fields merged.
    assert context["user_id"] == "abc"
    assert context["attempt"] == 2


def test_build_context_excludes_none_metadata(
    node: NodeReducer[int, list[int]],
) -> None:
    """None-valued metadata fields are excluded from the context."""
    input_data = _make_input(metadata=ModelReducerMetadata(trigger=None))

    context, _ = node._build_fsm_context(input_data)

    assert "trigger" not in context


def test_reserved_key_is_dropped_and_warns(
    node: NodeReducer[int, list[int]],
) -> None:
    """A user-supplied _fsm_* key is NOT merged and produces one WARNING intent."""
    reserved_key = f"{_FSM_RESERVED_CONTEXT_PREFIX}state"
    metadata = ModelReducerMetadata.model_validate(
        {"trigger": "start", reserved_key: "TAMPERED"}
    )
    input_data = _make_input(metadata=metadata)

    context, warnings = node._build_fsm_context(input_data)

    # Reserved key must not leak into the system context.
    assert reserved_key not in context
    # Non-reserved key still merged.
    assert context["trigger"] == "start"

    # Exactly one WARNING log_event intent naming the rejected key.
    assert len(warnings) == 1
    intent = warnings[0]
    assert intent.intent_type == "log_event"
    payload = intent.payload
    assert isinstance(payload, ModelPayloadLogEvent)
    assert payload.level == "WARNING"
    assert reserved_key in payload.context["reserved_keys"]
    assert payload.context["reserved_prefix"] == _FSM_RESERVED_CONTEXT_PREFIX


def test_multiple_reserved_keys_reported_sorted_in_single_intent(
    node: NodeReducer[int, list[int]],
) -> None:
    """All reserved keys surface, sorted, in a single warning intent."""
    metadata = ModelReducerMetadata.model_validate(
        {
            "trigger": "start",
            f"{_FSM_RESERVED_CONTEXT_PREFIX}zeta": 1,
            f"{_FSM_RESERVED_CONTEXT_PREFIX}alpha": 2,
        }
    )
    input_data = _make_input(metadata=metadata)

    context, warnings = node._build_fsm_context(input_data)

    assert f"{_FSM_RESERVED_CONTEXT_PREFIX}zeta" not in context
    assert f"{_FSM_RESERVED_CONTEXT_PREFIX}alpha" not in context

    assert len(warnings) == 1
    payload = warnings[0].payload
    assert isinstance(payload, ModelPayloadLogEvent)
    assert payload.context["reserved_keys"] == [
        f"{_FSM_RESERVED_CONTEXT_PREFIX}alpha",
        f"{_FSM_RESERVED_CONTEXT_PREFIX}zeta",
    ]


@pytest.mark.asyncio
async def test_process_emits_reserved_key_warning_intent(
    node: NodeReducer[int, list[int]],
) -> None:
    """End-to-end: process() surfaces the reserved-key warning in output intents."""
    from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
        ModelFSMStateDefinition,
    )
    from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
        ModelFSMStateTransition,
    )
    from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
        ModelFSMSubcontract,
    )
    from omnibase_core.models.primitives.model_semver import ModelSemVer

    v = ModelSemVer(major=1, minor=0, patch=0)
    node.fsm_contract = ModelFSMSubcontract(
        state_machine_name="build_ctx_fsm",
        description="Context-construction e2e FSM",
        state_machine_version=v,
        version=v,
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial state",
                version=v,
                entry_actions=[],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                description="Processing state",
                version=v,
                entry_actions=[],
                exit_actions=[],
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="processing",
                trigger="start_event",
                version=v,
                conditions=[],
                actions=[],
            ),
        ],
        terminal_states=[],
        error_states=[],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )

    metadata = ModelReducerMetadata.model_validate(
        {"trigger": "start_event", f"{_FSM_RESERVED_CONTEXT_PREFIX}state": "BAD"}
    )
    result = await node.process(_make_input(metadata=metadata))

    log_intents = [i for i in result.intents if i.intent_type == "log_event"]
    reserved_warnings = [
        i
        for i in log_intents
        if isinstance(i.payload, ModelPayloadLogEvent)
        and i.payload.level == "WARNING"
        and "reserved" in i.payload.message.lower()
    ]
    assert len(reserved_warnings) == 1
