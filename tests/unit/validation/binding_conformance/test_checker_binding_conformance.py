# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""check_binding_conformance: nothing a node ships assumes one deployment's setup (OMN-21514).

The merged omnimarket check (OMN-21473) moved into the generic validator format: the rule
tables are the contract ``binding_conformance.validation.yaml`` and the predicate is
``checker_binding_conformance``. These are the merged task's fixtures, run against the checker.
Fixtures use invented names only.
"""

from __future__ import annotations

import builtins
import os
import pathlib
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_binding_rule import EnumBindingRule
from omnibase_core.enums.enum_binding_source_kind import EnumBindingSourceKind
from omnibase_core.enums.enum_private_name_kind import EnumPrivateNameKind
from omnibase_core.models.binding_conformance.model_binding_conformance_request import (
    ModelBindingConformanceRequest,
)
from omnibase_core.models.binding_conformance.model_binding_conformance_result import (
    ModelBindingConformanceResult,
)
from omnibase_core.models.binding_conformance.model_binding_protocol_table import (
    ModelBindingProtocolTable,
)
from omnibase_core.models.binding_conformance.model_binding_rule_tables import (
    ModelBindingRuleTables,
)
from omnibase_core.models.binding_conformance.model_binding_source import (
    ModelBindingSource,
)
from omnibase_core.models.binding_conformance.model_concrete_binding import (
    ModelConcreteBinding,
)
from omnibase_core.models.binding_conformance.model_private_name import (
    ModelPrivateName,
)
from omnibase_core.validation.checker_binding_conformance import (
    binding_rules_from_contract,
    check_binding_conformance,
)
from omnibase_core.validation.validator_binding_conformance import (
    ValidatorBindingConformance,
)

pytestmark = pytest.mark.unit

RULES = binding_rules_from_contract(ValidatorBindingConformance().contract)

BUS_REF = "fixture_core.protocols:ProtocolBus"
CLK_REF = "fixture_core.protocols:ProtocolClock"
LED_REF = "fixture_core.protocols:ProtocolLedger"
# Invented names standing in for a deployment's overlay values.
INVENTED_REPO = "acme-widgets"
INVENTED_HOST = "box-17.fixture.invalid"
INVENTED_ORG = "acme-fixture-org"
PRIVATE_NAMES = (
    ModelPrivateName(kind=EnumPrivateNameKind.REPOSITORY, value=INVENTED_REPO),
    ModelPrivateName(kind=EnumPrivateNameKind.HOST, value=INVENTED_HOST),
    ModelPrivateName(kind=EnumPrivateNameKind.ORGANIZATION, value=INVENTED_ORG),
)

TABLE = ModelBindingProtocolTable.model_validate(
    {
        "protocols": [
            {"code": "BUS", "protocol": BUS_REF},
            {"code": "CLK", "protocol": CLK_REF},
            {"code": "LED", "protocol": LED_REF},
        ],
        "rows": [
            {"node": "node_fixture_effect", "protocols": ["BUS", "CLK"]},
            {"node": "node_fixture_pure_compute", "protocols": []},
        ],
    }
)
CONCRETE = (
    ModelConcreteBinding(
        code="BUS",
        modules=("fixture_kafka",),
        classes=("FixtureKafkaBus",),
        allowed_path_prefixes=("adapters/",),
    ),
)
PURE_BANNED = ("fixture_pkg.overlay_reader", "fixture_contract_loader")


def _contract(*refs: str) -> str:
    entries = [
        {"name": ref.split(":")[1], "protocol": ref, "required": True} for ref in refs
    ]
    return yaml.safe_dump(
        {
            "name": "node_fixture",
            "node_type": "effect",
            "protocol_dependencies": entries,
        }
    )


def _src(
    node: str, kind: EnumBindingSourceKind, text: str, path: str | None = None
) -> ModelBindingSource:
    default = {
        EnumBindingSourceKind.CONTRACT: "contract.yaml",
        EnumBindingSourceKind.HANDLER: "handlers/handler.py",
        EnumBindingSourceKind.MODEL: "models/model.py",
    }[kind]
    return ModelBindingSource(
        node=node, path=path or default, kind=kind, text=textwrap.dedent(text)
    )


CLEAN_EFFECT = textwrap.dedent(
    """\
    from fixture_core.protocols import ProtocolBus, ProtocolClock


    class Handler:
        def __init__(self, bus: ProtocolBus, clock: ProtocolClock) -> None:
            self._bus = bus
            self._clock = clock
    """
)
CLEAN_PURE = textwrap.dedent(
    """\
    class Handler:
        def handle(self, request: object) -> object:
            return request
    """
)


def _effect_sources(handler: str = CLEAN_EFFECT) -> tuple[ModelBindingSource, ...]:
    return (
        _src(
            "node_fixture_effect",
            EnumBindingSourceKind.CONTRACT,
            _contract(BUS_REF, CLK_REF),
        ),
        _src("node_fixture_effect", EnumBindingSourceKind.HANDLER, handler),
    )


def _pure_sources(
    handler: str = CLEAN_PURE, model: str = "class M:\n    pass\n"
) -> tuple[ModelBindingSource, ...]:
    return (
        _src("node_fixture_pure_compute", EnumBindingSourceKind.CONTRACT, _contract()),
        _src("node_fixture_pure_compute", EnumBindingSourceKind.HANDLER, handler),
        _src("node_fixture_pure_compute", EnumBindingSourceKind.MODEL, model),
    )


def _check(
    nodes: tuple[str, ...],
    sources: tuple[ModelBindingSource, ...],
    *,
    table: ModelBindingProtocolTable = TABLE,
    names: tuple[ModelPrivateName, ...] = PRIVATE_NAMES,
    rules: ModelBindingRuleTables = RULES,
) -> ModelBindingConformanceResult:
    return check_binding_conformance(
        ModelBindingConformanceRequest(
            checked_nodes=nodes,
            protocol_table=table,
            concrete_bindings=CONCRETE,
            pure_forbidden_modules=PURE_BANNED,
            private_names=names,
            sources=sources,
        ),
        rules,
    )


def _rules(result: ModelBindingConformanceResult) -> set[EnumBindingRule]:
    return {i.rule for i in result.issues}


def _lines(result: ModelBindingConformanceResult, rule: EnumBindingRule) -> list[int]:
    return sorted(i.line for i in result.issues if i.rule is rule)


# --- positive controls ---------------------------------------------------------------------


def test_a_conforming_effect_and_a_conforming_pure_node_pass() -> None:
    result = _check(
        ("node_fixture_effect", "node_fixture_pure_compute"),
        _effect_sources() + _pure_sources(),
    )
    assert result.issues == ()
    assert result.conforming is True
    assert result.checked_nodes == ("node_fixture_effect", "node_fixture_pure_compute")


# --- AC1: a concrete bus adapter ------------------------------------------------------------


def test_effect_that_constructs_a_concrete_bus_adapter_fails_naming_the_line() -> None:
    handler = """\
        from fixture_core.protocols import ProtocolBus, ProtocolClock
        from fixture_kafka import FixtureKafkaBus


        class Handler:
            def __init__(self, clock: ProtocolClock) -> None:
                self._clock = clock
                self._bus: ProtocolBus = FixtureKafkaBus()
        """
    result = _check(("node_fixture_effect",), _effect_sources(handler))
    assert result.conforming is False
    assert _lines(result, EnumBindingRule.CONCRETE_BINDING) == [2, 8]
    construct = next(i for i in result.issues if i.line == 8)
    assert construct.node == "node_fixture_effect"
    assert construct.path == "handlers/handler.py"
    assert "FixtureKafkaBus" in construct.detail
    assert "BUS" in construct.detail


def test_a_concrete_binding_is_allowed_in_its_own_adapter_path() -> None:
    adapter = _src(
        "node_fixture_effect",
        EnumBindingSourceKind.HANDLER,
        "from fixture_kafka import FixtureKafkaBus\nbus = FixtureKafkaBus()\n",
        path="adapters/bus.py",
    )
    result = _check(("node_fixture_effect",), (*_effect_sources(), adapter))
    assert result.issues == ()


# --- AC2: a protocol the row requires, and one it does not give -----------------------------


def test_contract_missing_a_protocol_its_row_requires_fails_naming_the_protocol() -> (
    None
):
    sources = (
        _src("node_fixture_effect", EnumBindingSourceKind.CONTRACT, _contract(BUS_REF)),
        _src("node_fixture_effect", EnumBindingSourceKind.HANDLER, CLEAN_EFFECT),
    )
    result = _check(("node_fixture_effect",), sources)
    assert result.conforming is False
    (issue,) = result.issues
    assert issue.rule is EnumBindingRule.CONTRACT_MISSING_PROTOCOL
    assert "CLK" in issue.detail
    assert CLK_REF in issue.detail


def test_contract_declaring_a_protocol_its_row_does_not_give_fails() -> None:
    sources = (
        _src(
            "node_fixture_effect",
            EnumBindingSourceKind.CONTRACT,
            _contract(BUS_REF, CLK_REF, LED_REF),
        ),
        _src("node_fixture_effect", EnumBindingSourceKind.HANDLER, CLEAN_EFFECT),
    )
    result = _check(("node_fixture_effect",), sources)
    (issue,) = result.issues
    assert issue.rule is EnumBindingRule.CONTRACT_EXTRA_PROTOCOL
    assert "LED" in issue.detail


def test_contract_declaring_a_protocol_the_table_does_not_know_fails() -> None:
    sources = (
        _src(
            "node_fixture_effect",
            EnumBindingSourceKind.CONTRACT,
            _contract(BUS_REF, CLK_REF, "elsewhere:ProtocolOther"),
        ),
        _src("node_fixture_effect", EnumBindingSourceKind.HANDLER, CLEAN_EFFECT),
    )
    result = _check(("node_fixture_effect",), sources)
    (issue,) = result.issues
    assert issue.rule is EnumBindingRule.CONTRACT_UNKNOWN_PROTOCOL
    assert "elsewhere:ProtocolOther" in issue.detail


def test_a_pure_node_that_declares_a_protocol_fails() -> None:
    sources = (
        _src(
            "node_fixture_pure_compute",
            EnumBindingSourceKind.CONTRACT,
            _contract(BUS_REF),
        ),
        _src("node_fixture_pure_compute", EnumBindingSourceKind.HANDLER, CLEAN_PURE),
    )
    result = _check(("node_fixture_pure_compute",), sources)
    assert _rules(result) == {EnumBindingRule.CONTRACT_EXTRA_PROTOCOL}


@pytest.mark.parametrize(
    ("node", "sources", "rule"),
    [
        ("node_without_a_row", _effect_sources(), EnumBindingRule.NO_TABLE_ROW),
        ("node_fixture_effect", _effect_sources()[1:], EnumBindingRule.NO_CONTRACT),
        ("node_fixture_effect", _effect_sources()[:1], EnumBindingRule.NO_SOURCE),
    ],
)
def test_a_checked_node_with_no_row_contract_or_source_fails_rather_than_passing_empty(
    node: str, sources: tuple[ModelBindingSource, ...], rule: EnumBindingRule
) -> None:
    result = _check((node,), sources)
    assert result.conforming is False
    assert rule in _rules(result)


def test_an_unreadable_contract_fails() -> None:
    sources = (
        _src(
            "node_fixture_effect",
            EnumBindingSourceKind.CONTRACT,
            "protocol_dependencies: [1",
        ),
        _src("node_fixture_effect", EnumBindingSourceKind.HANDLER, CLEAN_EFFECT),
    )
    result = _check(("node_fixture_effect",), sources)
    assert _rules(result) == {EnumBindingRule.CONTRACT_UNREADABLE}


def test_the_table_refuses_a_row_naming_a_protocol_it_does_not_define() -> None:
    with pytest.raises(ValidationError):
        ModelBindingProtocolTable.model_validate(
            {
                "protocols": [{"code": "BUS", "protocol": BUS_REF}],
                "rows": [{"node": "n", "protocols": ["NOPE"]}],
            }
        )


# --- AC3: an invented repository name, host name, or an os.environ read --------------------


def test_handler_with_an_invented_repository_name_fails() -> None:
    handler = CLEAN_EFFECT + f'\n\nTARGET = "{INVENTED_REPO}"\n'
    result = _check(("node_fixture_effect",), _effect_sources(handler))
    assert _rules(result) == {EnumBindingRule.PRIVATE_NAME}
    (issue,) = result.issues
    assert issue.line == 10
    assert "repository" in issue.detail
    assert INVENTED_REPO not in issue.detail


def test_handler_with_an_invented_host_name_fails() -> None:
    handler = CLEAN_EFFECT + f"\n\n# runs on {INVENTED_HOST}\n"
    result = _check(("node_fixture_effect",), _effect_sources(handler))
    assert _rules(result) == {EnumBindingRule.PRIVATE_NAME}
    assert "host" in result.issues[0].detail
    assert INVENTED_HOST not in result.issues[0].detail


def test_handler_that_reads_os_environ_fails_naming_the_line() -> None:
    handler = CLEAN_EFFECT + '\n\nimport os\n\nvalue = os.environ["SOME_SETTING"]\n'
    result = _check(("node_fixture_effect",), _effect_sources(handler))
    assert _rules(result) == {EnumBindingRule.ENV_READ}
    assert _lines(result, EnumBindingRule.ENV_READ) == [12]


@pytest.mark.parametrize(
    "snippet",
    [
        "import os\nv = os.getenv('X')\n",
        "import os as o\nv = o.environ.get('X')\n",
        "from os import environ\nv = environ['X']\n",
        "from os import getenv\nv = getenv('X')\n",
    ],
)
def test_every_spelling_of_an_environment_read_fails(snippet: str) -> None:
    result = _check(
        ("node_fixture_effect",), _effect_sources(CLEAN_EFFECT + "\n" + snippet)
    )
    assert EnumBindingRule.ENV_READ in _rules(result)


def test_private_names_apply_to_the_contract_and_the_models_too() -> None:
    sources = (
        _src(
            "node_fixture_pure_compute",
            EnumBindingSourceKind.CONTRACT,
            _contract() + f"description: for {INVENTED_ORG}\n",
        ),
        _src("node_fixture_pure_compute", EnumBindingSourceKind.HANDLER, CLEAN_PURE),
        _src(
            "node_fixture_pure_compute",
            EnumBindingSourceKind.MODEL,
            f'DEFAULT = "{INVENTED_REPO}"\n',
        ),
    )
    result = _check(("node_fixture_pure_compute",), sources)
    assert {i.path for i in result.issues} == {"contract.yaml", "models/model.py"}
    assert _rules(result) == {EnumBindingRule.PRIVATE_NAME}


def test_a_private_name_is_matched_whole_not_inside_a_longer_word() -> None:
    handler = CLEAN_EFFECT + f"\n\nOTHER = 'x{INVENTED_REPO}y'\n"
    assert _check(("node_fixture_effect",), _effect_sources(handler)).issues == ()


def test_private_names_come_from_the_request_not_from_the_node() -> None:
    handler = CLEAN_EFFECT + f'\n\nTARGET = "{INVENTED_REPO}"\n'
    sources = _effect_sources(handler)
    assert _check(("node_fixture_effect",), sources, names=()).conforming is True
    other = (ModelPrivateName(kind=EnumPrivateNameKind.REPOSITORY, value="other-repo"),)
    assert _check(("node_fixture_effect",), sources, names=other).conforming is True
    assert _check(("node_fixture_effect",), sources).conforming is False


@pytest.mark.parametrize(
    ("literal", "rule"),
    [
        ("https://svc.fixture.invalid/v1", EnumBindingRule.URL_LITERAL),
        ("tcp://127.0.0.1:9000", EnumBindingRule.URL_LITERAL),
        ("/srv/fixture/ledger.md", EnumBindingRule.PATH_LITERAL),
        ("~/fixture/state", EnumBindingRule.PATH_LITERAL),
    ],
)
def test_handler_with_a_url_or_path_literal_fails(
    literal: str, rule: EnumBindingRule
) -> None:
    handler = CLEAN_EFFECT + f'\n\nLOCATION = "{literal}"\n'
    result = _check(("node_fixture_effect",), _effect_sources(handler))
    assert _rules(result) == {rule}
    assert _lines(result, rule) == [10]


def test_an_fstring_is_read_whole_not_by_its_fragments() -> None:
    quiet = CLEAN_EFFECT + "\n\nrate = 1.5\nlabel = f'{rate:.3f}/h'\n"
    assert _check(("node_fixture_effect",), _effect_sources(quiet)).issues == ()
    url = CLEAN_EFFECT + "\n\nhost = 'h'\nendpoint = f'https://{host}/v1'\n"
    result = _check(("node_fixture_effect",), _effect_sources(url))
    assert _rules(result) == {EnumBindingRule.URL_LITERAL}
    path = CLEAN_EFFECT + "\n\nname = 'n'\nlocation = f'/srv/{name}'\n"
    result = _check(("node_fixture_effect",), _effect_sources(path))
    assert _rules(result) == {EnumBindingRule.PATH_LITERAL}


def test_a_docstring_that_shows_a_url_is_not_a_literal_in_use() -> None:
    handler = '"""Talks to https://svc.fixture.invalid in the docs."""\n' + CLEAN_EFFECT
    assert _check(("node_fixture_effect",), _effect_sources(handler)).issues == ()


def test_a_handler_that_does_not_parse_fails() -> None:
    result = _check(("node_fixture_effect",), _effect_sources("def broken(:\n"))
    assert EnumBindingRule.SOURCE_UNPARSEABLE in _rules(result)


# --- AC4: purity ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "imports",
    [
        "from fixture_pkg.overlay_reader import load_structured_overlay\n",
        "import fixture_contract_loader\n",
        "from fixture_contract_loader.loader import load_contract\n",
        "from fixture_pkg import overlay_reader\n",
    ],
)
def test_a_pure_handler_or_model_that_imports_the_overlay_reader_or_loader_fails(
    imports: str,
) -> None:
    for sources in (
        _pure_sources(handler=imports + CLEAN_PURE),
        _pure_sources(model=imports),
    ):
        result = _check(("node_fixture_pure_compute",), sources)
        assert _rules(result) == {EnumBindingRule.PURE_LOADS_CONFIGURATION}
        assert result.issues[0].line == 1


def test_an_effect_may_import_what_a_pure_node_may_not() -> None:
    handler = (
        "from fixture_pkg.overlay_reader import load_structured_overlay\n"
        + CLEAN_EFFECT
    )
    assert _check(("node_fixture_effect",), _effect_sources(handler)).issues == ()


LOADS_ITS_OWN_OVERLAY = textwrap.dedent(
    """\
    from fixture_pkg.overlay_reader import load_structured_overlay


    class Handler:
        def handle(self, request: object) -> object:
            return load_structured_overlay("limits", dict)
    """
)


def test_a_fixture_handler_that_loads_its_own_overlay_fails() -> None:
    result = _check(
        ("node_fixture_pure_compute",), _pure_sources(handler=LOADS_ITS_OWN_OVERLAY)
    )
    assert result.conforming is False
    assert EnumBindingRule.PURE_LOADS_CONFIGURATION in _rules(result)


@contextmanager
def _guard_on_filesystem_reads() -> Iterator[None]:
    """Raise on any open, stat or listing until the block ends."""

    def refuse(*_a: object, **_k: object) -> Any:
        raise AssertionError("filesystem read under the guard")

    patched: list[tuple[Any, str, Any]] = [
        (builtins, "open", refuse),
        (os, "stat", refuse),
        (os, "listdir", refuse),
        (os, "scandir", refuse),
        (pathlib.Path, "open", refuse),
        (pathlib.Path, "read_text", refuse),
        (pathlib.Path, "read_bytes", refuse),
        (pathlib.Path, "exists", refuse),
        (pathlib.Path, "stat", refuse),
        (pathlib.Path, "iterdir", refuse),
    ]
    saved = [(owner, name, getattr(owner, name)) for owner, name, _ in patched]
    for owner, name, replacement in patched:
        setattr(owner, name, replacement)
    try:
        yield
    finally:
        for owner, name, original in saved:
            setattr(owner, name, original)


def test_the_guard_does_stop_a_handler_that_reads_its_own_overlay() -> None:
    """Positive control: a read under the guard raises, so a pass below means no read happened."""
    with _guard_on_filesystem_reads():
        with pytest.raises(AssertionError):
            Path("anything.yaml").read_text()


def test_the_check_runs_under_the_guard_with_injected_configuration() -> None:
    request = ModelBindingConformanceRequest(
        checked_nodes=("node_fixture_effect", "node_fixture_pure_compute"),
        protocol_table=TABLE,
        concrete_bindings=CONCRETE,
        pure_forbidden_modules=PURE_BANNED,
        private_names=PRIVATE_NAMES,
        sources=_effect_sources() + _pure_sources(),
    )
    with _guard_on_filesystem_reads():
        guarded = check_binding_conformance(request, RULES)
    assert guarded.conforming is True
    assert (
        guarded.model_dump_json()
        == check_binding_conformance(request, RULES).model_dump_json()
    )


# --- AC6: configuration --------------------------------------------------------------------


def test_a_fixture_table_that_adds_a_protocol_to_a_node_makes_the_same_contract_fail() -> (
    None
):
    sources = _effect_sources()
    assert _check(("node_fixture_effect",), sources).conforming is True
    wider = ModelBindingProtocolTable.model_validate(
        {
            "protocols": [p.model_dump() for p in TABLE.protocols],
            "rows": [
                {"node": "node_fixture_effect", "protocols": ["BUS", "CLK", "LED"]},
                {"node": "node_fixture_pure_compute", "protocols": []},
            ],
        }
    )
    result = _check(("node_fixture_effect",), sources, table=wider)
    assert result.conforming is False
    assert _rules(result) == {EnumBindingRule.CONTRACT_MISSING_PROTOCOL}
    assert "LED" in result.issues[0].detail


def test_a_fixture_concrete_binding_list_decides_what_counts_as_concrete() -> None:
    handler = (
        CLEAN_EFFECT + "\nfrom other_adapter import OtherAdapter\nOtherAdapter()\n"
    )
    sources = _effect_sources(handler)
    assert _check(("node_fixture_effect",), sources).conforming is True
    request = ModelBindingConformanceRequest(
        checked_nodes=("node_fixture_effect",),
        protocol_table=TABLE,
        concrete_bindings=(
            ModelConcreteBinding(code="BUS", modules=("other_adapter",)),
        ),
        sources=sources,
    )
    assert check_binding_conformance(request, RULES).conforming is False
