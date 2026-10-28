# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Every operator the FSM condition model accepts must be evaluated by the executor.

``ModelFSMTransitionCondition.VALID_OPERATORS`` is the single list of operators a
contract may use. A guard written with an operator that the executor does not
evaluate would silently never hold, so each operator is driven through
``execute_transition`` with a context that satisfies the guard and one that does
not. The cases are keyed by the model's own operator set, so an operator added to
the model without an evaluator (and a case here) fails the suite.
"""

from pathlib import Path

import pytest
import yaml

from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_fsm_executor import execute_transition
from omnibase_core.utils.util_fsm_expression_parser import SUPPORTED_OPERATORS

pytestmark = pytest.mark.unit

_VERSION = ModelSemVer(major=1, minor=0, patch=0)

# operator -> (value token, context where the guard holds, context where it does not)
OPERATOR_CASES: dict[str, tuple[str, dict[str, object], dict[str, object]]] = {
    "==": ("5", {"field": 5}, {"field": 6}),
    "!=": ("5", {"field": 6}, {"field": 5}),
    "equals": ("ready", {"field": "ready"}, {"field": "busy"}),
    "not_equals": ("ready", {"field": "busy"}, {"field": "ready"}),
    "<": ("5", {"field": 4}, {"field": 5}),
    ">": ("5", {"field": 6}, {"field": 5}),
    "<=": ("5", {"field": 5}, {"field": 6}),
    ">=": ("5", {"field": 5}, {"field": 4}),
    "less_than": ("5", {"field": 4}, {"field": 5}),
    "greater_than": ("5", {"field": 6}, {"field": 5}),
    "less_than_or_equal": ("5", {"field": 5}, {"field": 6}),
    "greater_than_or_equal": ("5", {"field": 5}, {"field": 4}),
    "min_length": ("2", {"field": [1, 2]}, {"field": [1]}),
    "max_length": ("2", {"field": [1, 2]}, {"field": [1, 2, 3]}),
    "exists": ("_", {"field": 0}, {}),
    "not_exists": ("_", {}, {"field": 0}),
    "in": ("a,b", {"field": "a"}, {"field": "c"}),
    "not_in": ("a,b", {"field": "c"}, {"field": "a"}),
    "contains": ("ell", {"field": "hello"}, {"field": "world"}),
    "matches": ("^he", {"field": "hello"}, {"field": "world"}),
}


def _single_guard_fsm(expression: str) -> ModelFSMSubcontract:
    """An FSM whose only transition is guarded by one condition."""
    return ModelFSMSubcontract(
        state_machine_name="operator_fsm",
        state_machine_version=_VERSION,
        description="One guarded transition",
        version=_VERSION,
        states=[
            ModelFSMStateDefinition(
                state_name="before",
                state_type="operational",
                description="State before the guard",
                is_terminal=False,
                version=_VERSION,
            ),
            ModelFSMStateDefinition(
                state_name="after",
                state_type="operational",
                description="State after the guard",
                is_terminal=False,
                version=_VERSION,
            ),
        ],
        initial_state="before",
        terminal_states=[],
        error_states=[],
        transitions=[
            ModelFSMStateTransition(
                transition_name="go",
                from_state="before",
                to_state="after",
                trigger="go",
                conditions=[
                    ModelFSMTransitionCondition(
                        condition_name="guard",
                        condition_type="expression",
                        expression=expression,
                    )
                ],
                version=_VERSION,
            ),
        ],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )


def test_cases_cover_exactly_the_operators_the_model_accepts() -> None:
    """A new operator needs an evaluator and a case; a removed one needs neither."""
    assert set(OPERATOR_CASES) == set(ModelFSMTransitionCondition.VALID_OPERATORS)


def test_parser_and_model_accept_the_same_operators() -> None:
    assert SUPPORTED_OPERATORS == ModelFSMTransitionCondition.VALID_OPERATORS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operator", sorted(ModelFSMTransitionCondition.VALID_OPERATORS)
)
async def test_operator_evaluates_true_and_false(operator: str) -> None:
    value, holds, fails = OPERATOR_CASES[operator]
    fsm = _single_guard_fsm(f"field {operator} {value}")

    taken = await execute_transition(fsm, "before", "go", holds)
    refused = await execute_transition(fsm, "before", "go", fails)

    assert taken.success, f"{operator}: guard should hold for {holds!r}"
    assert taken.new_state == "after"
    assert not refused.success, f"{operator}: guard should not hold for {fails!r}"
    assert refused.new_state == "before"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("symbol", "text"),
    [
        ("<", "less_than"),
        (">", "greater_than"),
        ("<=", "less_than_or_equal"),
        (">=", "greater_than_or_equal"),
    ],
)
@pytest.mark.parametrize("observed", [4, 5, 6])
async def test_textual_comparison_matches_symbolic(
    symbol: str, text: str, observed: int
) -> None:
    context: dict[str, object] = {"field": observed}
    symbolic = await execute_transition(
        _single_guard_fsm(f"field {symbol} 5"), "before", "go", context
    )
    textual = await execute_transition(
        _single_guard_fsm(f"field {text} 5"), "before", "go", context
    )
    assert symbolic.success == textual.success


@pytest.mark.asyncio
@pytest.mark.parametrize("operator", ["min_length", "max_length"])
@pytest.mark.parametrize("field_value", [None, 5, True])
async def test_length_operators_refuse_values_without_a_length(
    operator: str, field_value: object
) -> None:
    result = await execute_transition(
        _single_guard_fsm(f"field {operator} 1"), "before", "go", {"field": field_value}
    )
    assert not result.success


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("expression", "field_value", "expected"),
    [
        ("field min_length 3", "abc", True),
        ("field min_length 3", "ab", False),
        ("field min_length 0", {}, True),
        ("field max_length 0", {}, True),
        ("field max_length 1", {"a": 1, "b": 2}, False),
        ("field min_length 1", {"a": 1}, True),
        ("field min_length 1", (1,), True),
    ],
)
async def test_length_operators_cover_strings_and_mappings(
    expression: str, field_value: object, expected: bool
) -> None:
    result = await execute_transition(
        _single_guard_fsm(expression), "before", "go", {"field": field_value}
    )
    assert result.success is expected


@pytest.mark.asyncio
async def test_length_operator_with_non_integer_bound_does_not_hold() -> None:
    result = await execute_transition(
        _single_guard_fsm("field min_length many"), "before", "go", {"field": [1]}
    )
    assert not result.success


@pytest.mark.asyncio
async def test_exists_follows_nested_paths() -> None:
    fsm = _single_guard_fsm("user.email exists _")
    assert (
        await execute_transition(fsm, "before", "go", {"user": {"email": "a"}})
    ).success
    assert not (await execute_transition(fsm, "before", "go", {"user": {}})).success
    assert not (await execute_transition(fsm, "before", "go", {"user": None})).success


_RUNTIME_CONTRACT = (
    Path(__file__).parent.parent.parent.parent
    / "contracts"
    / "runtime"
    / "node_graph_reducer.yaml"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("registry", "expected"),
    [
        ({"node_a": {}}, True),
        (["node_a"], True),
        ({}, False),
        ([], False),
    ],
)
async def test_node_graph_reducer_registry_loaded_guard(
    registry: object, expected: bool
) -> None:
    """The runtime contract's ``node_registry min_length 1`` guard means what it says."""
    with open(_RUNTIME_CONTRACT, encoding="utf-8") as f:
        fsm = ModelFSMSubcontract.model_validate(yaml.safe_load(f)["state_transitions"])

    result = await execute_transition(
        fsm,
        "initializing",
        "registry_ready",
        {"node_registry": registry, "registry_errors": 0},
    )

    assert result.success is expected
    assert result.new_state == ("wiring" if expected else "initializing")


class _InProcessReducer(MixinFSMExecution):
    """A reducer run in process: it drives the contract through the mixin."""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operator", sorted(ModelFSMTransitionCondition.VALID_OPERATORS)
)
@pytest.mark.parametrize("guard_holds", [True, False])
async def test_reducer_run_matches_direct_call(
    operator: str, guard_holds: bool
) -> None:
    """The same context gives the same transition in a direct call and in a reducer."""
    value, holds, fails = OPERATOR_CASES[operator]
    fsm = _single_guard_fsm(f"field {operator} {value}")
    context = holds if guard_holds else fails

    direct = await execute_transition(fsm, "before", "go", context)
    via_reducer = await _InProcessReducer().execute_fsm_transition(fsm, "go", context)

    assert (via_reducer.success, via_reducer.new_state) == (
        direct.success,
        direct.new_state,
    )
    assert direct.success is guard_holds


def test_condition_keeps_declared_description_and_version() -> None:
    """Contract conditions carry a description and a version; both are typed fields."""
    condition = ModelFSMTransitionCondition.model_validate(
        {
            "condition_name": "registry_loaded",
            "condition_type": "data_validation",
            "expression": "node_registry min_length 1",
            "description": "Registry must hold a node",
            "version": {"major": 1, "minor": 0, "patch": 0},
        }
    )
    assert condition.description == "Registry must hold a node"
    assert condition.version == _VERSION


def test_condition_refuses_an_undeclared_key() -> None:
    with pytest.raises(ValueError, match="unknown_key"):
        ModelFSMTransitionCondition.model_validate(
            {
                "condition_name": "c",
                "condition_type": "expression",
                "expression": "x == 1",
                "unknown_key": True,
            }
        )


def test_valid_operators_is_a_class_constant_not_a_serialized_field() -> None:
    condition = ModelFSMTransitionCondition(
        condition_name="c", condition_type="expression", expression="x == 1"
    )
    assert "VALID_OPERATORS" not in condition.model_dump()
    assert "VALID_OPERATORS" not in ModelFSMTransitionCondition.model_fields
