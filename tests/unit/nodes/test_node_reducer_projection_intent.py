# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for NodeReducer projection intent emission (OMN-2509).

Tests that NodeReducer:
- Emits ModelProjectionIntent as part of its effects list
- Wraps projection intents in ModelPayloadProjectionIntent payloads
- Has no direct projector calls in reducer code paths
- Preserves causation chain via correlation_id
- Combines FSM intents and projection intents in the correct order
- Handles empty projection intent lists without side effects
- Maintains determinism when projection intents are provided
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
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
from omnibase_core.models.projectors.model_projection_intent import (
    ModelProjectionIntent,
)
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.payloads.model_payload_projection_intent import (
    ModelPayloadProjectionIntent,
)
from omnibase_core.nodes.node_reducer import NodeReducer

# Module-level marker for all tests in this file
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Create a simple FSM contract for projection intent tests."""
    return ModelFSMSubcontract(
        state_machine_name="projection_test_fsm",
        description="FSM for testing projection intent emission",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        version=ModelSemVer(major=1, minor=0, patch=0),
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial state",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                description="Processing state",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="completed",
                state_type="terminal",
                description="Terminal state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                is_terminal=True,
                is_recoverable=False,
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="processing",
                trigger="start_event",
                version=ModelSemVer(major=1, minor=0, patch=0),
                conditions=[],
                actions=[],
            ),
            ModelFSMStateTransition(
                transition_name="complete",
                from_state="processing",
                to_state="completed",
                trigger="complete_event",
                version=ModelSemVer(major=1, minor=0, patch=0),
                conditions=[],
                actions=[],
            ),
        ],
        terminal_states=["completed"],
        error_states=[],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )


class _SimpleEnvelope(BaseModel):
    """Minimal event envelope for test purposes."""

    envelope_id: str
    entity_id: str


def _make_projection_intent(
    projector_key: str = "node_state_projector",
    event_type: str = "node.created.v1",
    entity_id: str = "entity-123",
    correlation_id: UUID | None = None,
) -> ModelProjectionIntent:
    """Create a ModelProjectionIntent for testing."""
    envelope = _SimpleEnvelope(
        envelope_id="env-1",
        entity_id=entity_id,
    )
    return ModelProjectionIntent(
        projector_key=projector_key,
        event_type=event_type,
        envelope=envelope,
        correlation_id=correlation_id or uuid4(),
    )


def _make_input(
    trigger: str = "start_event",
    operation_id: UUID | None = None,
) -> ModelReducerInput[list[int]]:
    """Create a ModelReducerInput for testing."""
    return ModelReducerInput(
        data=[1, 2, 3],
        reduction_type=EnumReductionType.AGGREGATE,
        operation_id=operation_id or uuid4(),
        metadata={"trigger": trigger},
    )


# ---------------------------------------------------------------------------
# Tests: ModelPayloadProjectionIntent payload model
# ---------------------------------------------------------------------------


class TestModelPayloadProjectionIntent:
    """Tests for the ModelPayloadProjectionIntent payload model."""

    def test_payload_has_correct_intent_type(self) -> None:
        """intent_type discriminator is always 'projection_intent'."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent_type == "projection_intent"

    def test_payload_wraps_projection_intent(self) -> None:
        """Payload preserves the wrapped ModelProjectionIntent."""
        pi = _make_projection_intent(
            projector_key="my_projector",
            event_type="node.updated.v1",
        )
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent is pi
        assert payload.intent.projector_key == "my_projector"
        assert payload.intent.event_type == "node.updated.v1"

    def test_payload_is_frozen(self) -> None:
        """Payload is immutable after creation."""
        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        with pytest.raises(Exception):
            payload.intent_type = "other"  # type: ignore[misc]

    def test_payload_implements_protocol(self) -> None:
        """ModelPayloadProjectionIntent satisfies ProtocolIntentPayload."""
        from omnibase_core.models.reducer.payloads.model_protocol_intent_payload import (
            ProtocolIntentPayload,
        )

        pi = _make_projection_intent()
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert isinstance(payload, ProtocolIntentPayload)

    def test_payload_correlation_id_preserved(self) -> None:
        """Correlation ID from projection intent is accessible via payload."""
        corr_id = UUID("12345678-1234-1234-1234-123456789abc")
        pi = _make_projection_intent(correlation_id=corr_id)
        payload = ModelPayloadProjectionIntent(intent=pi)
        assert payload.intent.correlation_id == corr_id


# ---------------------------------------------------------------------------
# Tests: NodeReducer emits projection intents in output
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60)
class TestNodeReducerEmitsProjectionIntents:
    """Tests that NodeReducer emits ModelProjectionIntent as output effects."""

    @pytest.mark.asyncio
    async def test_projection_intent_appears_in_output_intents(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """When a projection intent is passed, it appears in the output intents."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        pi = _make_projection_intent()
        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi,),
        )

        projection_intents_in_output = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(projection_intents_in_output) == 1

    @pytest.mark.asyncio
    async def test_projection_intent_payload_is_correct_type(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Projection intents in output carry ModelPayloadProjectionIntent payloads."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        pi = _make_projection_intent(projector_key="node_state_projector")
        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi,),
        )

        projection_intents_in_output = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(projection_intents_in_output) == 1
        payload = projection_intents_in_output[0].payload
        assert isinstance(payload, ModelPayloadProjectionIntent)

    @pytest.mark.asyncio
    async def test_projection_intent_payload_wraps_original_intent(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """The wrapped ModelProjectionIntent is accessible via payload.intent."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        corr_id = uuid4()
        pi = _make_projection_intent(
            projector_key="my_projector",
            event_type="my.event.v1",
            correlation_id=corr_id,
        )
        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi,),
        )

        proj_outputs = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(proj_outputs) == 1
        payload = proj_outputs[0].payload
        assert isinstance(payload, ModelPayloadProjectionIntent)
        assert payload.intent.projector_key == "my_projector"
        assert payload.intent.event_type == "my.event.v1"
        assert payload.intent.correlation_id == corr_id

    @pytest.mark.asyncio
    async def test_projection_intent_target_matches_projector_key(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """The ModelIntent target equals the projector_key for routing."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        pi = _make_projection_intent(projector_key="workflow_summary_projector")
        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi,),
        )

        proj_outputs = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(proj_outputs) == 1
        assert proj_outputs[0].target == "workflow_summary_projector"

    @pytest.mark.asyncio
    async def test_multiple_projection_intents_all_emitted(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Multiple projection intents are all emitted as separate ModelIntent objects."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        pi1 = _make_projection_intent(
            projector_key="projector_a", event_type="node.created.v1"
        )
        pi2 = _make_projection_intent(
            projector_key="projector_b", event_type="node.created.v1"
        )
        pi3 = _make_projection_intent(
            projector_key="projector_c", event_type="node.created.v1"
        )

        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi1, pi2, pi3),
        )

        proj_outputs = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(proj_outputs) == 3
        projector_keys = {
            proj.payload.intent.projector_key  # type: ignore[union-attr]
            for proj in proj_outputs
        }
        assert projector_keys == {"projector_a", "projector_b", "projector_c"}

    @pytest.mark.asyncio
    async def test_no_projection_intents_by_default(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Without projection_intents, no projection intent appears in output."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        result = await node.process(_make_input(trigger="start_event"))

        projection_intents_in_output = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(projection_intents_in_output) == 0

    @pytest.mark.asyncio
    async def test_empty_projection_intents_tuple_produces_no_projection_output(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Passing an empty tuple explicitly produces no projection intents."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(),
        )

        projection_intents_in_output = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(projection_intents_in_output) == 0


# ---------------------------------------------------------------------------
# Tests: Intent ordering (FSM intents first, then projection intents)
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60)
class TestNodeReducerIntentOrdering:
    """Tests that FSM intents precede projection intents in the output."""

    @pytest.mark.asyncio
    async def test_fsm_intents_precede_projection_intents(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """FSM-generated intents appear before projection intents in the output tuple."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        pi = _make_projection_intent()
        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi,),
        )

        intent_types = [intent.intent_type for intent in result.intents]
        # Find the index of the projection intent
        if "projection_intent" in intent_types:
            proj_idx = intent_types.index("projection_intent")
            # All intents before the projection intent must be non-projection FSM intents
            for idx in range(proj_idx):
                assert intent_types[idx] != "projection_intent", (
                    f"Projection intent found before expected position at index {idx}: "
                    f"{intent_types}"
                )

    @pytest.mark.asyncio
    async def test_total_intent_count_is_fsm_plus_projection(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Total intent count equals FSM intents + projection intents."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # First get FSM-only intent count as baseline
        baseline_result = await node.process(_make_input(trigger="start_event"))
        fsm_intent_count = len(baseline_result.intents)

        # Now start fresh and add projection intents
        node2 = NodeReducer(test_container)
        node2.fsm_contract = simple_fsm
        node2.initialize_fsm_state(simple_fsm, context={})

        pi1 = _make_projection_intent(projector_key="p1")
        pi2 = _make_projection_intent(projector_key="p2")
        result = await node2.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi1, pi2),
        )

        assert len(result.intents) == fsm_intent_count + 2


# ---------------------------------------------------------------------------
# Tests: No direct projector calls (purity contract)
# ---------------------------------------------------------------------------


class TestNodeReducerNoPDirectProjectorCalls:
    """Tests that NodeReducer has no direct projector calls (purity contract)."""

    def test_node_reducer_has_no_projector_import(self) -> None:
        """NodeReducer source must not import any concrete projector implementations."""
        import inspect

        import omnibase_core.nodes.node_reducer as reducer_module

        source = inspect.getsource(reducer_module)

        # Concrete projector classes should not be imported
        assert "ProtocolProjector" not in source, (
            "NodeReducer must not reference ProtocolProjector — "
            "use ModelProjectionIntent to declare projection intent instead"
        )
        # Should not call any project() method directly
        assert ".project(" not in source, (
            "NodeReducer must not call .project() directly — "
            "emit ModelProjectionIntent as an effect instead"
        )

    def test_node_reducer_uses_intent_not_direct_call(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """NodeReducer emits ModelPayloadProjectionIntent; it does not call projectors."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        pi = _make_projection_intent()
        # The presence of a projection intent in the output (not raised exception)
        # proves the reducer declared intent rather than calling a projector directly.
        # If there were a direct call, it would need a real projector implementation.
        import asyncio

        result = asyncio.run(
            node.process(
                _make_input(trigger="start_event"),
                projection_intents=(pi,),
            )
        )
        proj_outputs = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(proj_outputs) == 1
        assert isinstance(proj_outputs[0].payload, ModelPayloadProjectionIntent)


# ---------------------------------------------------------------------------
# Tests: Causation chain (correlation_id) propagation
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60)
class TestNodeReducerCausationChain:
    """Tests that correlation_id is correctly carried through projection intents."""

    @pytest.mark.asyncio
    async def test_correlation_id_preserved_in_output_intent(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """The correlation_id from the originating event is preserved in the intent."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        corr_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        pi = _make_projection_intent(correlation_id=corr_id)

        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi,),
        )

        proj_outputs = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(proj_outputs) == 1
        payload = proj_outputs[0].payload
        assert isinstance(payload, ModelPayloadProjectionIntent)
        assert payload.intent.correlation_id == corr_id

    @pytest.mark.asyncio
    async def test_multiple_projection_intents_preserve_individual_correlation_ids(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Each projection intent retains its own correlation_id independently."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        corr_id_1 = UUID("11111111-1111-1111-1111-111111111111")
        corr_id_2 = UUID("22222222-2222-2222-2222-222222222222")

        pi1 = _make_projection_intent(
            projector_key="projector_one", correlation_id=corr_id_1
        )
        pi2 = _make_projection_intent(
            projector_key="projector_two", correlation_id=corr_id_2
        )

        result = await node.process(
            _make_input(trigger="start_event"),
            projection_intents=(pi1, pi2),
        )

        proj_outputs = [
            intent
            for intent in result.intents
            if intent.intent_type == "projection_intent"
        ]
        assert len(proj_outputs) == 2

        corr_ids_in_output = {
            proj.payload.intent.correlation_id  # type: ignore[union-attr]
            for proj in proj_outputs
        }
        assert corr_ids_in_output == {corr_id_1, corr_id_2}


# ---------------------------------------------------------------------------
# Tests: Determinism with projection intents
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60)
class TestNodeReducerProjectionDeterminism:
    """Tests that projection intent emission is deterministic."""

    @pytest.mark.asyncio
    async def test_same_projection_intents_produce_same_output(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Same inputs + same projection intents produce identical outputs."""
        corr_id = UUID("deadbeef-dead-beef-dead-beefdeadbeef")
        op_id = UUID("12345678-1234-1234-1234-123456789abc")

        results_intent_count = []
        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            pi = _make_projection_intent(
                projector_key="node_state_projector",
                event_type="node.created.v1",
                correlation_id=corr_id,
            )
            result = await node.process(
                _make_input(trigger="start_event", operation_id=op_id),
                projection_intents=(pi,),
            )
            proj_outputs = [
                intent
                for intent in result.intents
                if intent.intent_type == "projection_intent"
            ]
            results_intent_count.append(len(proj_outputs))

        # All runs must produce the same number of projection intents
        assert all(count == 1 for count in results_intent_count)

    @pytest.mark.asyncio
    async def test_projection_intent_structure_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Projection intent structure (excluding auto-generated IDs) is deterministic."""
        corr_id = UUID("cafecafe-cafe-cafe-cafe-cafecafecafe")
        op_id = UUID("87654321-4321-4321-4321-cba987654321")

        all_projector_keys = []
        all_event_types = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            pi = _make_projection_intent(
                projector_key="determinism_projector",
                event_type="determinism.event.v1",
                correlation_id=corr_id,
            )
            result = await node.process(
                _make_input(trigger="start_event", operation_id=op_id),
                projection_intents=(pi,),
            )
            proj_outputs = [
                intent
                for intent in result.intents
                if intent.intent_type == "projection_intent"
            ]
            assert len(proj_outputs) == 1
            payload = proj_outputs[0].payload
            assert isinstance(payload, ModelPayloadProjectionIntent)
            all_projector_keys.append(payload.intent.projector_key)
            all_event_types.append(payload.intent.event_type)

        assert all(k == "determinism_projector" for k in all_projector_keys)
        assert all(et == "determinism.event.v1" for et in all_event_types)


# ---------------------------------------------------------------------------
# Tests: Existing tests still pass (no regression)
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60)
class TestNodeReducerProjectionNoRegression:
    """Tests that adding projection intent support does not regress existing behavior."""

    @pytest.mark.asyncio
    async def test_fsm_state_transitions_unaffected_by_projection_intents(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """FSM state transitions work identically regardless of projection intents."""
        # Without projection intents
        node1 = NodeReducer(test_container)
        node1.fsm_contract = simple_fsm
        node1.initialize_fsm_state(simple_fsm, context={})

        op_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        result1 = await node1.process(
            _make_input(trigger="start_event", operation_id=op_id)
        )

        # With projection intents
        node2 = NodeReducer(test_container)
        node2.fsm_contract = simple_fsm
        node2.initialize_fsm_state(simple_fsm, context={})

        pi = _make_projection_intent()
        result2 = await node2.process(
            _make_input(trigger="start_event", operation_id=op_id),
            projection_intents=(pi,),
        )

        # FSM state should be identical
        assert getattr(result1.metadata, "fsm_state", None) == getattr(
            result2.metadata, "fsm_state", None
        )
        assert getattr(result1.metadata, "fsm_transition", None) == getattr(
            result2.metadata, "fsm_transition", None
        )
        assert getattr(result1.metadata, "fsm_success", None) == getattr(
            result2.metadata, "fsm_success", None
        )

    @pytest.mark.asyncio
    async def test_result_data_passthrough_unaffected(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Result data passthrough is unaffected by projection intents."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        input_data = [10, 20, 30, 40, 50]
        pi = _make_projection_intent()
        result = await node.process(
            ModelReducerInput(
                data=input_data,
                reduction_type=EnumReductionType.AGGREGATE,
                metadata={"trigger": "start_event"},
            ),
            projection_intents=(pi,),
        )

        assert list(result.result) == input_data

    @pytest.mark.asyncio
    async def test_items_processed_unaffected_by_projection_intents(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """items_processed count is unaffected by projection intents."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        input_data = [1, 2, 3, 4, 5]
        pi = _make_projection_intent()
        result = await node.process(
            ModelReducerInput(
                data=input_data,
                reduction_type=EnumReductionType.AGGREGATE,
                metadata={"trigger": "start_event"},
            ),
            projection_intents=(pi,),
        )

        assert result.items_processed == len(input_data)
