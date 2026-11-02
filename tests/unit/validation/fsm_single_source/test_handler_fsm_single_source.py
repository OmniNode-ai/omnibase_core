# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The single-source check as a core checker: the contract is the only source of a state machine (OMN-21513).

The fixtures are the ones the merged omnimarket check (OMN-21477) was proven on, copied here so the
core checker is held to the same verdicts without reading another repository.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import ModuleType

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers import (
    handler_fsm_single_source,
    handler_fsm_single_source_rules,
)
from omnibase_core.handlers.handler_fsm_single_source import HandlerFsmSingleSource
from omnibase_core.handlers.handler_fsm_single_source_cli import (
    ValidatorFsmSingleSource,
)
from omnibase_core.handlers.handler_fsm_single_source_rules import (
    rules_from_subcontract,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_fsm_single_source_request import (
    ModelFsmSingleSourceRequest,
)
from omnibase_core.models.validation.model_fsm_single_source_result import (
    ModelFsmSingleSourceResult,
)
from omnibase_core.models.validation.model_fsm_single_source_rules import (
    ModelFsmSingleSourceRules,
)
from omnibase_core.models.validation.model_fsm_source_text import ModelFsmSourceText

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent / "fixtures"

RULE_STATE_TABLE = "state_table"
RULE_BRANCH_CHAIN = "state_branch_chain"
RULE_EXECUTOR_MISSING = "execute_transition_missing"
RULE_STATE_MACHINE_MISSING = "state_machine_missing"
RULE_CONTRACT_UNREADABLE = "contract_unreadable"
RULE_SOURCE_UNPARSEABLE = "source_unparseable"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text("utf-8")


def _shipped() -> ModelValidatorSubcontract:
    return ValidatorFsmSingleSource().contract


def _with_parameter(
    rule_id: str, parameter: str, drop: str | None = None, value: str | None = None
) -> ModelValidatorSubcontract:
    """The shipped contract with one entry of one rule's parameter removed (or replaced)."""
    shipped = _shipped()
    rules: list[ModelValidatorRule] = []
    for rule in shipped.rules:
        if rule.rule_id == rule_id:
            parameters = dict(rule.parameters or {})
            if value is not None:
                parameters[parameter] = value
            else:
                entries = parameters[parameter]
                assert isinstance(entries, list)
                assert drop in entries
                parameters[parameter] = [e for e in entries if e != drop]
            rule = rule.model_copy(update={"parameters": parameters})
        rules.append(rule)
    return shipped.model_copy(update={"rules": rules})


def check_fsm_single_source(
    contract_source: ModelFsmSourceText,
    sources: tuple[ModelFsmSourceText, ...],
    rules: ModelFsmSingleSourceRules,
) -> ModelFsmSingleSourceResult:
    return HandlerFsmSingleSource().handle(
        ModelFsmSingleSourceRequest(
            contract_source=contract_source, sources=sources, rules=rules
        )
    )


def _check(
    source_name: str,
    contract: str = "contract_machine.yaml",
    subcontract: ModelValidatorSubcontract | None = None,
) -> ModelFsmSingleSourceResult:
    rules = rules_from_subcontract(subcontract or _shipped())
    return check_fsm_single_source(
        ModelFsmSourceText(name="contract", text=_fixture(contract)),
        (ModelFsmSourceText(name=source_name, text=_fixture(source_name)),),
        rules,
    )


def _codes(result: ModelFsmSingleSourceResult) -> set[str | None]:
    return {issue.code for issue in result.issues}


# --- the merged task's fixtures, the same verdicts ------------------------------------------


def test_state_trigger_mapping_fails_and_names_the_line() -> None:
    result = _check("reducer_allowed_transitions.py.fixture")
    assert result.exit_code != 0
    table = [i for i in result.issues if i.code == RULE_STATE_TABLE]
    assert [i.line_number for i in table] == [5]
    assert table[0].file_path == Path("reducer_allowed_transitions.py.fixture")
    assert table[0].message is not None
    assert "line 5" in table[0].message


def test_reducer_routed_through_execute_transition_passes() -> None:
    result = _check("reducer_clean.py.fixture")
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.state_names == ("drafted", "built", "done", "refused")


def test_function_local_mapping_beside_execute_transition_fails() -> None:
    result = _check("handler_local_mapping.py.fixture")
    assert _codes(result) == {RULE_STATE_TABLE}
    assert [i.line_number for i in result.issues] == [7]


@pytest.mark.parametrize(
    ("source", "line"),
    [("state_enum.py.fixture", 8), ("state_tuple.py.fixture", 5)],
)
def test_state_only_enum_or_tuple_fails(source: str, line: int) -> None:
    result = _check(source)
    assert [(i.code, i.line_number) for i in result.issues] == [
        (RULE_STATE_TABLE, line)
    ]


def test_branch_chain_on_state_literals_fails() -> None:
    result = _check("branch_chain.py.fixture")
    assert _codes(result) == {RULE_BRANCH_CHAIN}
    assert [i.line_number for i in result.issues] == [8]


def test_single_state_name_in_a_collection_is_not_a_table() -> None:
    source = 'KEYS = {"drafted": 1, "other": 2}\nexecute_transition(a, b, c, d)\n'
    result = check_fsm_single_source(
        ModelFsmSourceText(name="contract", text=_fixture("contract_machine.yaml")),
        (ModelFsmSourceText(name="one.py", text=source),),
        rules_from_subcontract(_shipped()),
    )
    assert result.issues == ()


def test_handler_that_never_calls_execute_transition_fails() -> None:
    result = _check("no_executor.py.fixture")
    assert _codes(result) == {RULE_EXECUTOR_MISSING}


def test_contract_without_state_machine_fails() -> None:
    result = _check(
        "reducer_clean.py.fixture", contract="contract_without_machine.yaml"
    )
    assert _codes(result) == {RULE_STATE_MACHINE_MISSING}
    assert result.exit_code != 0


def test_unparseable_source_and_contract_are_issues_not_crashes() -> None:
    rules = rules_from_subcontract(_shipped())
    broken = ModelFsmSourceText(name="broken.py", text="def (:\n")
    result = check_fsm_single_source(
        ModelFsmSourceText(name="contract", text="state_machine: [unclosed"),
        (broken,),
        rules,
    )
    assert RULE_CONTRACT_UNREADABLE in _codes(result)
    result = check_fsm_single_source(
        ModelFsmSourceText(name="contract", text=_fixture("contract_machine.yaml")),
        (broken,),
        rules,
    )
    assert RULE_SOURCE_UNPARSEABLE in _codes(result)


def test_issue_is_the_generic_validation_issue_with_rule_severity() -> None:
    result = _check("state_tuple.py.fixture")
    (issue,) = result.issues
    assert isinstance(issue, ModelValidationIssue)
    assert issue.severity == EnumSeverity.ERROR
    assert issue.rule_name == RULE_STATE_TABLE


# --- configuration: each rule table is the .validation.yaml contract ------------------------


@pytest.mark.parametrize(
    ("rule_id", "parameter", "drop", "source", "caught"),
    [
        (
            RULE_STATE_TABLE,
            "collection_nodes",
            "Tuple",
            "state_tuple.py.fixture",
            RULE_STATE_TABLE,
        ),
        (
            RULE_STATE_TABLE,
            "collection_nodes",
            "Dict",
            "reducer_allowed_transitions.py.fixture",
            RULE_STATE_TABLE,
        ),
        (
            RULE_STATE_TABLE,
            "enum_base_suffixes",
            "Enum",
            "state_enum.py.fixture",
            RULE_STATE_TABLE,
        ),
        (
            RULE_BRANCH_CHAIN,
            "compare_operators",
            "Eq",
            "branch_chain.py.fixture",
            RULE_BRANCH_CHAIN,
        ),
        (
            RULE_BRANCH_CHAIN,
            "scope_nodes",
            "AsyncFunctionDef",
            "branch_chain.py.fixture",
            RULE_BRANCH_CHAIN,
        ),
    ],
)
def test_removing_one_contract_entry_changes_the_verdict_it_catches(
    rule_id: str, parameter: str, drop: str, source: str, caught: str
) -> None:
    assert caught in _codes(_check(source))
    edited = _with_parameter(rule_id, parameter, drop=drop)
    after = _check(source, subcontract=edited)
    assert caught not in _codes(after)


def test_renaming_the_executor_in_the_contract_changes_the_verdict() -> None:
    assert _check("reducer_clean.py.fixture").issues == ()
    edited = _with_parameter(
        RULE_EXECUTOR_MISSING, "executor_name", value="run_machine"
    )
    after = _check("reducer_clean.py.fixture", subcontract=edited)
    assert _codes(after) == {RULE_EXECUTOR_MISSING}


def test_disabling_a_rule_in_the_contract_drops_its_issues() -> None:
    shipped = _shipped()
    rules = [
        r.model_copy(update={"enabled": False}) if r.rule_id == RULE_BRANCH_CHAIN else r
        for r in shipped.rules
    ]
    edited = shipped.model_copy(update={"rules": rules})
    assert _check("branch_chain.py.fixture", subcontract=edited).issues == ()


def test_rule_severity_comes_from_the_contract() -> None:
    shipped = _shipped()
    rules = [
        r.model_copy(update={"severity": EnumSeverity.WARNING})
        if r.rule_id == RULE_STATE_TABLE
        else r
        for r in shipped.rules
    ]
    edited = shipped.model_copy(update={"rules": rules})
    (issue,) = _check("state_tuple.py.fixture", subcontract=edited).issues
    assert issue.severity == EnumSeverity.WARNING


def test_an_unknown_ast_node_name_in_the_contract_is_refused() -> None:
    edited = _with_parameter(RULE_STATE_TABLE, "collection_nodes", value="x")
    with pytest.raises(ModelOnexError, match="collection_nodes"):
        rules_from_subcontract(edited)


def test_the_checker_module_holds_no_rule_table() -> None:
    """No module-level tuple, set, list or dict of rule values survives in the checker."""
    tables: list[str] = []
    for module in (handler_fsm_single_source, handler_fsm_single_source_rules):
        tables.extend(_module_tables(module))
    assert tables == []


def _module_tables(module: ModuleType) -> list[str]:
    tree = ast.parse(Path(module.__file__ or "").read_text("utf-8"))
    tables: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if names == ["__all__"]:
                continue
            if any(
                isinstance(child, (ast.Tuple, ast.Set, ast.List, ast.Dict))
                for child in ast.walk(node.value)
            ):
                tables.extend(names)
    return tables


# --- bindings: pure --------------------------------------------------------------------------


def test_checker_imports_no_io_module_and_calls_no_io() -> None:
    tree = ast.parse(Path(handler_fsm_single_source.__file__ or "").read_text("utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {
        "os",
        "subprocess",
        "socket",
        "sys",
        "time",
        "random",
        "requests",
    }
    called = {
        n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
    }
    assert not called & {"open", "read_text", "write_text", "getenv", "now", "utcnow"}


def test_results_are_byte_identical_across_calls_and_through_the_validator(
    tmp_path: Path,
) -> None:
    names = (
        "reducer_allowed_transitions.py.fixture",
        "handler_local_mapping.py.fixture",
        "state_enum.py.fixture",
        "branch_chain.py.fixture",
        "no_executor.py.fixture",
    )
    rules = rules_from_subcontract(_shipped())
    sources = tuple(ModelFsmSourceText(name=n, text=_fixture(n)) for n in names)
    contract = ModelFsmSourceText(
        name="contract", text=_fixture("contract_machine.yaml")
    )
    first = check_fsm_single_source(contract, sources, rules).model_dump_json()
    second = check_fsm_single_source(contract, sources, rules).model_dump_json()
    assert first == second

    node_dir = tmp_path / "node_fixture_reducer"
    (node_dir / "handlers").mkdir(parents=True)
    (node_dir / "contract.yaml").write_text(contract.text, encoding="utf-8")
    for name in names:
        (node_dir / "handlers" / name.removesuffix(".fixture")).write_text(
            _fixture(name), encoding="utf-8"
        )
    via_validator = ValidatorFsmSingleSource().validate(tmp_path)
    direct = check_fsm_single_source(
        contract,
        tuple(
            ModelFsmSourceText(name=s.name.removesuffix(".fixture"), text=s.text)
            for s in sources
        ),
        rules,
    )
    assert sorted((i.code, i.line_number) for i in via_validator.issues) == sorted(
        (i.code, i.line_number) for i in direct.issues
    )


# --- the ValidatorBase entry ------------------------------------------------------------------


def _write_reducer(tmp_path: Path, node_type: str, source: str) -> Path:
    node_dir = tmp_path / "node_x"
    (node_dir / "handlers").mkdir(parents=True)
    (node_dir / "contract.yaml").write_text(
        _fixture("contract_machine.yaml").replace("REDUCER_GENERIC", node_type),
        encoding="utf-8",
    )
    (node_dir / "handlers" / "handler.py").write_text(
        _fixture(source), encoding="utf-8"
    )
    return node_dir


def test_validator_flags_a_reducer_directory_with_a_second_table(
    tmp_path: Path,
) -> None:
    _write_reducer(tmp_path, "REDUCER_GENERIC", "state_tuple.py.fixture")
    result = ValidatorFsmSingleSource().validate(tmp_path)
    assert [(i.code, i.line_number) for i in result.issues] == [(RULE_STATE_TABLE, 5)]


def test_validator_passes_a_clean_reducer_directory(tmp_path: Path) -> None:
    _write_reducer(tmp_path, "REDUCER_GENERIC", "reducer_clean.py.fixture")
    assert ValidatorFsmSingleSource().validate(tmp_path).issues == []


def test_validator_ignores_a_contract_that_is_not_a_reducer(tmp_path: Path) -> None:
    _write_reducer(tmp_path, "COMPUTE_GENERIC", "state_tuple.py.fixture")
    assert ValidatorFsmSingleSource().validate(tmp_path).issues == []
