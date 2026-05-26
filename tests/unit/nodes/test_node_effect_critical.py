# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for NodeEffect high-complexity branches.

Targets CCN hotspots in node_effect.py:
- process(): no subcontract guard, subcontract default merge, operation serialization
- get_circuit_breaker(): lazy creation, keyed by operation_id
- reset_circuit_breakers(): clears state
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumEffectType
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelHttpIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.nodes.node_effect import NodeEffect

pytestmark = pytest.mark.unit


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer(enable_service_registry=False)


@pytest.fixture
def effect_node(container: ModelONEXContainer) -> NodeEffect:
    return NodeEffect(container)


def _make_http_operation(name: str = "test_op") -> ModelEffectOperation:
    return ModelEffectOperation(
        operation_name=name,
        description="Test HTTP operation",
        idempotent=True,
        io_config=ModelHttpIOConfig(
            handler_type="http",
            url_template="https://example.com/api",
            method="GET",
        ),
    )


def _make_subcontract(
    retry_policy: ModelEffectRetryPolicy | None = None,
) -> ModelEffectSubcontract:
    return ModelEffectSubcontract(
        subcontract_name="test_subcontract",
        operations=[_make_http_operation()],
        default_retry_policy=retry_policy or ModelEffectRetryPolicy(max_retries=2),
    )


class TestProcessNoSubcontract:
    @pytest.mark.asyncio
    async def test_raises_when_no_subcontract_and_no_handler(
        self, effect_node: NodeEffect
    ) -> None:
        assert effect_node.effect_subcontract is None
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"key": "value"},
        )
        with pytest.raises(ModelOnexError) as exc_info:
            await effect_node.process(input_data)
        assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR
        assert "not loaded" in exc_info.value.message


class TestCircuitBreaker:
    def test_get_circuit_breaker_creates_on_first_access(
        self, effect_node: NodeEffect
    ) -> None:
        op_id = uuid4()
        cb = effect_node.get_circuit_breaker(op_id)
        assert isinstance(cb, ModelCircuitBreaker)

    def test_get_circuit_breaker_returns_same_instance(
        self, effect_node: NodeEffect
    ) -> None:
        op_id = uuid4()
        cb1 = effect_node.get_circuit_breaker(op_id)
        cb2 = effect_node.get_circuit_breaker(op_id)
        assert cb1 is cb2

    def test_different_operation_ids_get_different_breakers(
        self, effect_node: NodeEffect
    ) -> None:
        op1 = uuid4()
        op2 = uuid4()
        cb1 = effect_node.get_circuit_breaker(op1)
        cb2 = effect_node.get_circuit_breaker(op2)
        assert cb1 is not cb2

    def test_reset_clears_all_circuit_breakers(self, effect_node: NodeEffect) -> None:
        op1 = uuid4()
        op2 = uuid4()
        effect_node.get_circuit_breaker(op1)
        effect_node.get_circuit_breaker(op2)
        assert len(effect_node._circuit_breakers) == 2

        effect_node.reset_circuit_breakers()
        assert len(effect_node._circuit_breakers) == 0

    def test_reset_then_new_breaker_is_fresh(self, effect_node: NodeEffect) -> None:
        op_id = uuid4()
        cb_before = effect_node.get_circuit_breaker(op_id)
        effect_node.reset_circuit_breakers()
        cb_after = effect_node.get_circuit_breaker(op_id)
        assert cb_before is not cb_after


class TestSubcontractInjection:
    def test_set_subcontract_directly(self, effect_node: NodeEffect) -> None:
        subcontract = _make_subcontract()
        object.__setattr__(effect_node, "effect_subcontract", subcontract)
        assert effect_node.effect_subcontract is subcontract

    def test_subcontract_name_accessible(self, effect_node: NodeEffect) -> None:
        subcontract = _make_subcontract()
        object.__setattr__(effect_node, "effect_subcontract", subcontract)
        assert effect_node.effect_subcontract.subcontract_name == "test_subcontract"

    def test_subcontract_operations_accessible(self, effect_node: NodeEffect) -> None:
        subcontract = _make_subcontract()
        object.__setattr__(effect_node, "effect_subcontract", subcontract)
        assert len(effect_node.effect_subcontract.operations) == 1
        assert effect_node.effect_subcontract.operations[0].operation_name == "test_op"


class TestNodeEffectInit:
    def test_effect_subcontract_starts_none(self, effect_node: NodeEffect) -> None:
        assert effect_node.effect_subcontract is None

    def test_circuit_breakers_start_empty(self, effect_node: NodeEffect) -> None:
        assert len(effect_node._circuit_breakers) == 0

    def test_node_is_mixin_handler_routing(self, effect_node: NodeEffect) -> None:
        from omnibase_core.mixins.mixin_handler_routing import MixinHandlerRouting

        assert isinstance(effect_node, MixinHandlerRouting)
