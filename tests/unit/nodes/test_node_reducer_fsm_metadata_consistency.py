# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Round-trip consistency tests for ModelReducerOutput.fsm_metadata ↔ metadata extras.

OMN-597 (BETA-03) — fsm_metadata ↔ metadata dict consistency.

Verifies that the typed ``ModelReducerFsmMetadata`` attached to
``ModelReducerOutput.fsm_metadata`` is logically consistent with the 7 FSM
keys stored as extras in ``ModelReducerOutput.metadata``. Both representations
must encode identical values — no silent divergence is allowed.

Test surface:
    1. After a successful FSM transition, fsm_metadata equals what you'd get by
       round-tripping the extras dict through ModelReducerFsmMetadata.from_dict.
    2. Every key present in fsm_metadata.to_dict() is present in metadata extras
       with the same value.
    3. ModelReducerFsmMetadata round-trip (typed → dict → typed) is lossless.
    4. fsm_metadata is None for manually constructed ModelReducerOutput instances
       that did not go through NodeReducer.process (default=None contract).
    5. Building fsm_metadata from extras always yields the same result as the
       typed field (regression guard against future drift).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
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
from omnibase_core.models.reducer.model_reducer_fsm_metadata import (
    ModelReducerFsmMetadata,
)
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.nodes.node_reducer import NodeReducer

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def semver() -> ModelSemVer:
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def two_state_fsm(semver: ModelSemVer) -> ModelFSMSubcontract:
    """Two-state FSM: idle -> processing via 'start_event'."""
    return ModelFSMSubcontract(
        state_machine_name="consistency_test_fsm",
        description="FSM metadata consistency test machine",
        state_machine_version=semver,
        version=semver,
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial idle state",
                version=semver,
                entry_actions=[],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                description="Active processing state",
                version=semver,
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
                version=semver,
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


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


def _make_input(trigger: str) -> ModelReducerInput[int]:
    return ModelReducerInput(
        data=[1, 2, 3],
        reduction_type=EnumReductionType.AGGREGATE,
        operation_id=uuid4(),
        metadata=ModelReducerMetadata(trigger=trigger),
    )


# ---------------------------------------------------------------------------
# ModelReducerFsmMetadata standalone round-trip
# ---------------------------------------------------------------------------


class TestModelReducerFsmMetadataRoundTrip:
    """Typed model ↔ dict round-trip is lossless."""

    def test_roundtrip_success_payload(self) -> None:
        original = ModelReducerFsmMetadata(
            fsm_state="processing",
            fsm_previous_state="idle",
            fsm_transition_success=True,
            fsm_transition_name="start",
            failure_reason=None,
            failed_conditions=None,
            error=None,
        )
        restored = ModelReducerFsmMetadata.from_dict(original.to_dict())
        assert restored == original

    def test_roundtrip_failure_payload(self) -> None:
        original = ModelReducerFsmMetadata(
            fsm_state="idle",
            fsm_previous_state="idle",
            fsm_transition_success=False,
            fsm_transition_name="start",
            failure_reason="Guard rejected",
            failed_conditions=("has_data", "queue_ready"),
            error=None,
        )
        restored = ModelReducerFsmMetadata.from_dict(original.to_dict())
        assert restored == original

    def test_roundtrip_exception_payload(self) -> None:
        original = ModelReducerFsmMetadata(
            fsm_state="idle",
            fsm_previous_state=None,
            fsm_transition_success=False,
            fsm_transition_name=None,
            failure_reason=None,
            failed_conditions=None,
            error="RuntimeError: unexpected condition",
        )
        restored = ModelReducerFsmMetadata.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_preserves_none_values(self) -> None:
        """None optional fields are preserved in dict output (not elided)."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="idle",
            fsm_transition_success=True,
        )
        d = metadata.to_dict()
        assert "fsm_previous_state" in d
        assert d["fsm_previous_state"] is None
        assert "failure_reason" in d
        assert d["failure_reason"] is None

    def test_to_dict_has_exactly_seven_keys(self) -> None:
        metadata = ModelReducerFsmMetadata(
            fsm_state="idle",
            fsm_transition_success=True,
        )
        assert set(metadata.to_dict().keys()) == {
            "fsm_state",
            "fsm_previous_state",
            "fsm_transition_success",
            "fsm_transition_name",
            "failure_reason",
            "failed_conditions",
            "error",
        }


# ---------------------------------------------------------------------------
# Consistency between fsm_metadata typed field and metadata extras
# ---------------------------------------------------------------------------


class TestFsmMetadataExtrasConsistency:
    """fsm_metadata typed field and metadata extras carry identical values."""

    @pytest.mark.asyncio
    async def test_fsm_metadata_field_populated_on_process(
        self,
        container: ModelONEXContainer,
        two_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """NodeReducer.process populates fsm_metadata on every successful call."""
        node: NodeReducer[int, list[int]] = NodeReducer(container)
        node.fsm_contract = two_state_fsm
        node.initialize_fsm_state(two_state_fsm, context={})

        result = await node.process(_make_input(trigger="start_event"))

        assert result.fsm_metadata is not None

    @pytest.mark.asyncio
    async def test_fsm_metadata_matches_extras_on_success(
        self,
        container: ModelONEXContainer,
        two_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """After a successful transition, fsm_metadata equals extras round-tripped."""
        node: NodeReducer[int, list[int]] = NodeReducer(container)
        node.fsm_contract = two_state_fsm
        node.initialize_fsm_state(two_state_fsm, context={})

        result = await node.process(_make_input(trigger="start_event"))

        assert result.fsm_metadata is not None
        extras = result.metadata.model_extra or {}

        # Build typed model from extras and compare to the attached typed field.
        from_extras = ModelReducerFsmMetadata.from_dict(
            {
                "fsm_state": extras["fsm_state"],
                "fsm_previous_state": extras["fsm_previous_state"],
                "fsm_transition_success": extras["fsm_transition_success"],
                "fsm_transition_name": extras["fsm_transition_name"],
                "failure_reason": extras["failure_reason"],
                "failed_conditions": extras["failed_conditions"],
                "error": extras["error"],
            }
        )
        assert from_extras == result.fsm_metadata

    @pytest.mark.asyncio
    async def test_fsm_metadata_to_dict_equals_extras(
        self,
        container: ModelONEXContainer,
        two_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """fsm_metadata.to_dict() must be a subset of metadata extras with equal values."""
        node: NodeReducer[int, list[int]] = NodeReducer(container)
        node.fsm_contract = two_state_fsm
        node.initialize_fsm_state(two_state_fsm, context={})

        result = await node.process(_make_input(trigger="start_event"))

        assert result.fsm_metadata is not None
        extras = result.metadata.model_extra or {}
        typed_dict = result.fsm_metadata.to_dict()

        for key, value in typed_dict.items():
            assert key in extras, (
                f"Key '{key}' in fsm_metadata.to_dict() missing from extras"
            )
            assert extras[key] == value, (
                f"Mismatch for key '{key}': "
                f"fsm_metadata={value!r}, extras={extras[key]!r}"
            )

    @pytest.mark.asyncio
    async def test_fsm_metadata_values_correct_on_successful_transition(
        self,
        container: ModelONEXContainer,
        two_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """Typed field carries correct values for a known idle→processing transition."""
        node: NodeReducer[int, list[int]] = NodeReducer(container)
        node.fsm_contract = two_state_fsm
        node.initialize_fsm_state(two_state_fsm, context={})

        result = await node.process(_make_input(trigger="start_event"))

        assert result.fsm_metadata is not None
        m = result.fsm_metadata
        assert m.fsm_state == "processing"
        assert m.fsm_previous_state == "idle"
        assert m.fsm_transition_success is True
        assert m.fsm_transition_name == "start"
        assert m.failure_reason is None
        assert m.failed_conditions is None
        assert m.error is None

    @pytest.mark.asyncio
    async def test_fsm_metadata_roundtrip_from_output(
        self,
        container: ModelONEXContainer,
        two_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """Typed field survives a to_dict/from_dict round-trip unchanged."""
        node: NodeReducer[int, list[int]] = NodeReducer(container)
        node.fsm_contract = two_state_fsm
        node.initialize_fsm_state(two_state_fsm, context={})

        result = await node.process(_make_input(trigger="start_event"))

        assert result.fsm_metadata is not None
        restored = ModelReducerFsmMetadata.from_dict(result.fsm_metadata.to_dict())
        assert restored == result.fsm_metadata


# ---------------------------------------------------------------------------
# Default-None contract for manually constructed outputs
# ---------------------------------------------------------------------------


class TestFsmMetadataDefaultNone:
    """ModelReducerOutput.fsm_metadata defaults to None for non-FSM outputs."""

    def test_fsm_metadata_defaults_to_none(self) -> None:
        """A manually constructed output without fsm_metadata has None."""
        output: ModelReducerOutput[int] = ModelReducerOutput(
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=1.0,
            items_processed=1,
        )
        assert output.fsm_metadata is None

    def test_fsm_metadata_can_be_set_explicitly(self) -> None:
        """Explicit fsm_metadata construction is supported."""
        fsm_meta = ModelReducerFsmMetadata(
            fsm_state="done",
            fsm_transition_success=True,
        )
        output: ModelReducerOutput[int] = ModelReducerOutput(
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=1.0,
            items_processed=1,
            fsm_metadata=fsm_meta,
        )
        assert output.fsm_metadata == fsm_meta
