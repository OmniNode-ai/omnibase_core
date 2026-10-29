# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The binding conformance rule tables are the validator contract, not module constants (OMN-21514).

Covers the configuration criterion (a fixture contract that drops one entry changes the verdict on
the fixture that entry catches), the bindings criterion (pure: byte-identical results called
directly, through the validator entry and through a JSON round trip) and the file-mode entry.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_binding_rule import EnumBindingRule
from omnibase_core.enums.enum_binding_source_kind import EnumBindingSourceKind
from omnibase_core.models.binding_conformance.model_binding_conformance_request import (
    ModelBindingConformanceRequest,
)
from omnibase_core.models.binding_conformance.model_binding_conformance_result import (
    ModelBindingConformanceResult,
)
from omnibase_core.models.binding_conformance.model_binding_protocol_table import (
    ModelBindingProtocolTable,
)
from omnibase_core.models.binding_conformance.model_binding_source import (
    ModelBindingSource,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import checker_binding_conformance
from omnibase_core.validation.checker_binding_conformance import (
    binding_rules_from_contract,
    check_binding_conformance,
)
from omnibase_core.validation.validator_binding_conformance import (
    ValidatorBindingConformance,
)

pytestmark = pytest.mark.unit

TABLE = ModelBindingProtocolTable.model_validate(
    {
        "protocols": [
            {"code": "CLK", "protocol": "fixture_core.protocols:ProtocolClock"}
        ],
        "rows": [{"node": "node_fixture_effect", "protocols": ["CLK"]}],
    }
)
CONTRACT_TEXT = textwrap.dedent(
    """\
    name: node_fixture
    protocol_dependencies:
      - {name: ProtocolClock, protocol: "fixture_core.protocols:ProtocolClock", required: true}
    """
)
CLEAN = "from fixture_core.protocols import ProtocolClock\n"


def _request(handler_tail: str) -> ModelBindingConformanceRequest:
    return ModelBindingConformanceRequest(
        checked_nodes=("node_fixture_effect",),
        protocol_table=TABLE,
        sources=(
            ModelBindingSource(
                node="node_fixture_effect",
                path="contract.yaml",
                kind=EnumBindingSourceKind.CONTRACT,
                text=CONTRACT_TEXT,
            ),
            ModelBindingSource(
                node="node_fixture_effect",
                path="handlers/handler.py",
                kind=EnumBindingSourceKind.HANDLER,
                text=CLEAN + handler_tail,
            ),
        ),
    )


def _verdict(
    request: ModelBindingConformanceRequest, contract: ModelValidatorSubcontract
) -> ModelBindingConformanceResult:
    return check_binding_conformance(request, binding_rules_from_contract(contract))


def _shipped() -> ModelValidatorSubcontract:
    return ValidatorBindingConformance().contract


def _with_rule(
    contract: ModelValidatorSubcontract,
    rule_id: str,
    *,
    parameters: dict[str, str | list[str]] | None = None,
    enabled: bool | None = None,
) -> ModelValidatorSubcontract:
    rules: list[ModelValidatorRule] = []
    for rule in contract.rules:
        if rule.rule_id == rule_id:
            rule = rule.model_copy(
                update={
                    "parameters": parameters
                    if parameters is not None
                    else rule.parameters,
                    "enabled": rule.enabled if enabled is None else enabled,
                }
            )
        rules.append(rule)
    return contract.model_copy(update={"rules": rules})


def _env_names(contract: ModelValidatorSubcontract) -> list[str]:
    rule = next(r for r in contract.rules if r.rule_id == "env_read")
    assert rule.parameters is not None
    names = rule.parameters["environment_names"]
    assert isinstance(names, list)
    return names


def test_the_shipped_contract_carries_every_rule_and_every_rule_table() -> None:
    contract = _shipped()
    assert contract.validator_id == "binding_conformance"
    assert {r.rule_id for r in contract.rules} == {r.value for r in EnumBindingRule}
    assert sorted(_env_names(contract)) == ["environ", "getenv", "getenvb", "putenv"]
    tables = binding_rules_from_contract(contract)
    assert tables.url_pattern
    assert tables.absolute_path_pattern


@pytest.mark.parametrize(
    ("entry", "snippet"),
    [
        ("getenv", "import os\nv = os.getenv('X')\n"),
        ("environ", "import os\nv = os.environ['X']\n"),
        ("putenv", "import os\nos.putenv('X', 'y')\n"),
        ("getenvb", "import os\nv = os.getenvb(b'X')\n"),
    ],
)
def test_removing_an_environment_name_from_the_contract_changes_that_verdict(
    entry: str, snippet: str
) -> None:
    request = _request("\n" + snippet)
    shipped = _shipped()
    assert EnumBindingRule.ENV_READ in {
        i.rule for i in _verdict(request, shipped).issues
    }
    narrowed = _with_rule(
        shipped,
        "env_read",
        parameters={
            "environment_names": [n for n in _env_names(shipped) if n != entry]
        },
    )
    result = _verdict(request, narrowed)
    assert EnumBindingRule.ENV_READ not in {i.rule for i in result.issues}
    assert result.conforming is True


def test_an_environment_name_added_to_the_contract_is_caught() -> None:
    request = _request("\nimport os\nv = os.unsetenv('X')\n")
    shipped = _shipped()
    assert _verdict(request, shipped).conforming is True
    widened = _with_rule(
        shipped,
        "env_read",
        parameters={"environment_names": [*_env_names(shipped), "unsetenv"]},
    )
    assert _verdict(request, widened).conforming is False


def test_the_url_and_path_patterns_are_the_contracts_and_changing_them_changes_the_verdict() -> (
    None
):
    request = _request('\nA = "https://svc.fixture.invalid/v1"\nB = "/srv/fixture/x"\n')
    shipped = _shipped()
    assert {i.rule for i in _verdict(request, shipped).issues} == {
        EnumBindingRule.URL_LITERAL,
        EnumBindingRule.PATH_LITERAL,
    }
    no_url = _with_rule(
        shipped, "url_literal", parameters={"pattern": "^never-matches$"}
    )
    assert {i.rule for i in _verdict(request, no_url).issues} == {
        EnumBindingRule.PATH_LITERAL
    }
    no_path = _with_rule(
        shipped, "path_literal", parameters={"pattern": "^never-matches$"}
    )
    assert {i.rule for i in _verdict(request, no_path).issues} == {
        EnumBindingRule.URL_LITERAL
    }


def test_a_rule_the_contract_disables_is_not_reported() -> None:
    request = _request('\nA = "https://svc.fixture.invalid/v1"\n')
    shipped = _shipped()
    assert _verdict(request, shipped).conforming is False
    disabled = _with_rule(shipped, "url_literal", enabled=False)
    assert _verdict(request, disabled).conforming is True


def test_an_enabled_rule_without_its_table_is_refused_rather_than_passing_empty() -> (
    None
):
    shipped = _shipped()
    bare = _with_rule(shipped, "env_read", parameters={})
    with pytest.raises(ValueError, match="environment_names"):
        binding_rules_from_contract(bare)


def test_the_checker_module_holds_no_rule_table() -> None:
    source = inspect.getsource(checker_binding_conformance)
    tree = ast.parse(source)
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not {"environ", "getenv", "getenvb", "putenv"} & strings
    assert not any("://" in s for s in strings)
    module_level = [
        statement
        for statement in tree.body
        if isinstance(statement, (ast.Assign, ast.AnnAssign))
    ]
    for statement in module_level:
        value = statement.value
        assert not isinstance(value, ast.Call) or "compile" not in ast.unparse(value)


def test_direct_entry_and_json_round_trip_give_byte_identical_results() -> None:
    entry = ValidatorBindingConformance()
    tables = binding_rules_from_contract(entry.contract)
    for tail in ("\n", "\nimport os\nv = os.environ['X']\nU = 'https://h.invalid/x'\n"):
        request = _request(tail)
        direct = check_binding_conformance(request, tables)
        through_entry = entry.check(request)
        round_trip = check_binding_conformance(
            ModelBindingConformanceRequest.model_validate_json(
                request.model_dump_json()
            ),
            tables,
        )
        assert direct.model_dump_json() == through_entry.model_dump_json()
        assert direct.model_dump_json() == round_trip.model_dump_json()
        assert (
            direct.model_dump_json()
            == check_binding_conformance(request, tables).model_dump_json()
        )


def test_file_mode_flags_a_handler_file_through_the_validator_entry(
    tmp_path: Path,
) -> None:
    handler = tmp_path / "handlers" / "handler_fixture.py"
    handler.parent.mkdir()
    handler.write_text("import os\nvalue = os.environ['X']\n", encoding="utf-8")
    result = ValidatorBindingConformance().validate_file(handler)
    assert result.is_valid is False
    assert [i.code for i in result.issues] == ["env_read"]
    assert [i.line_number for i in result.issues] == [2]
    clean = tmp_path / "handlers" / "handler_clean.py"
    clean.write_text("value = 1\n", encoding="utf-8")
    assert ValidatorBindingConformance().validate_file(clean).is_valid is True


def test_the_checker_imports_nothing_that_reads_state_outside_its_arguments() -> None:
    tree = ast.parse(inspect.getsource(checker_binding_conformance))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported & {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "time",
        "datetime",
        "random",
        "uuid",
    }
