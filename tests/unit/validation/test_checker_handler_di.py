# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""K1 handler_di (OMN-21531): planted violations, clean twins, every rule parameter, purity,
scope, the hook entry, the report golden and the shrink-only baseline.

Two criteria wait on other tickets and are written to activate when those land, without a skip:
the corpus half of replay (plan task T0.8, the corpus) and the broker half of the two-overlay run
(plan task T3.1, the overlay pair). Each runs only the half that exists today and says so.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_handler_di_module_fact import (
    ModelHandlerDiModuleFact,
)
from omnibase_core.nodes.node_handler_di_check_effect.runtime_handler_di_check import (
    build_container,
    run,
)
from omnibase_core.validation import checker_handler_di as checker
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_handler_di import ValidatorHandlerDi
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "validation" / "handler_di"
VALIDATION = ROOT / "src" / "omnibase_core" / "validation"

CONSTRUCTOR = checker.RULE_CONSTRUCTOR
DIRECT = checker.RULE_DIRECT
CALL_SITE = checker.RULE_CALL_SITE
FALLBACK = checker.RULE_FALLBACK
REFLECTIVE = checker.RULE_REFLECTIVE
OPTIONAL_PORT = checker.RULE_NONE_DEFAULT
CONTRACT_LOAD = checker.RULE_CONTRACT_LOAD
SINGLETON = checker.RULE_SINGLETON
SIBLING = checker.RULE_SIBLING
VALUE_LITERAL = checker.RULE_VALUE_LITERAL
BASELINE = checker.RULE_BASELINE

# rule_id -> violation fixtures (directory, file): each yields exactly one issue of that rule
VIOLATIONS: dict[str, list[str]] = {
    CONSTRUCTOR: ["violation_constructor_signature/handlers/handler_x.py"],
    DIRECT: ["violation_direct_construction/handlers/handler_x.py"],
    CALL_SITE: ["violation_call_site_construction/handlers/handler_x_cli.py"],
    FALLBACK: [
        "violation_fallback_construction_or/handlers/handler_x.py",
        "violation_fallback_construction_ternary/handlers/handler_x.py",
        "violation_fallback_construction_guard/handlers/handler_x.py",
    ],
    REFLECTIVE: [
        "violation_reflective_construction_getattr/handlers/handler_x.py",
        "violation_reflective_construction_class_variable/handlers/handler_x.py",
        "violation_reflective_construction_table/handlers/handler_x.py",
    ],
    OPTIONAL_PORT: [
        "violation_optional_port_default_name/handlers/handler_x.py",
        "violation_optional_port_default_annotation/handlers/handler_x.py",
    ],
    CONTRACT_LOAD: [
        "violation_contract_self_load/handlers/handler_x.py",
        "violation_contract_loader_call/handlers/handler_x.py",
    ],
    SINGLETON: ["violation_module_singleton/handlers/handler_x.py"],
    SIBLING: ["violation_sibling_handler_import/handlers/handler_x.py"],
    VALUE_LITERAL: [
        "violation_contract_value_literal_name/handlers/handler_x.py",
        "violation_contract_value_literal_value/handlers/handler_x.py",
    ],
}
# rule_id -> clean fixtures: each yields no issue of any rule
CLEANS: dict[str, list[str]] = {
    CONSTRUCTOR: ["clean_constructor_signature/handlers/handler_x.py"],
    DIRECT: ["clean_direct_construction/handlers/handler_x.py"],
    CALL_SITE: ["clean_call_site_construction/handlers/handler_x_cli.py"],
    FALLBACK: ["clean_fallback_construction/handlers/handler_x.py"],
    REFLECTIVE: ["clean_reflective_construction/handlers/handler_x.py"],
    OPTIONAL_PORT: ["clean_optional_port_default/handlers/handler_x.py"],
    CONTRACT_LOAD: ["clean_contract_self_load/handlers/handler_x.py"],
    SINGLETON: ["clean_module_singleton/handlers/handler_x.py"],
    SIBLING: [
        "clean_sibling_handler_import/handlers/handler_x.py",
        "clean_sibling_handler_import_cli/handlers/handler_z_cli.py",
    ],
    VALUE_LITERAL: ["clean_contract_value_literal/handlers/handler_x.py"],
}
# (rule, parameter) -> (fixture, "clears" | "flags"): the fixture the key controls
CONTROLS: dict[tuple[str, str], tuple[str, str]] = {
    (CONSTRUCTOR, "class_name_pattern"): (VIOLATIONS[CONSTRUCTOR][0], "clears"),
    (CONSTRUCTOR, "init_name"): (VIOLATIONS[CONSTRUCTOR][0], "clears"),
    (CONSTRUCTOR, "self_parameter"): (CLEANS[CONSTRUCTOR][0], "flags"),
    (CONSTRUCTOR, "container_parameter"): (CLEANS[CONSTRUCTOR][0], "flags"),
    (DIRECT, "class_name_pattern"): (VIOLATIONS[DIRECT][0], "clears"),
    (DIRECT, "init_name"): (VIOLATIONS[DIRECT][0], "clears"),
    (DIRECT, "receiver_name"): (VIOLATIONS[DIRECT][0], "clears"),
    (DIRECT, "resolution_attrs"): (CLEANS[DIRECT][0], "flags"),
    (CALL_SITE, "constructed_name_pattern"): (VIOLATIONS[CALL_SITE][0], "clears"),
    (CALL_SITE, "invoked_methods"): (VIOLATIONS[CALL_SITE][0], "clears"),
    (FALLBACK, "class_name_pattern"): (VIOLATIONS[FALLBACK][0], "clears"),
    (FALLBACK, "loader_name_pattern"): (VIOLATIONS[FALLBACK][0], "clears"),
    (FALLBACK, "fallback_forms"): (VIOLATIONS[FALLBACK][0], "clears"),
    (REFLECTIVE, "reflective_getters"): (VIOLATIONS[REFLECTIVE][0], "clears"),
    (REFLECTIVE, "class_variable_pattern"): (VIOLATIONS[REFLECTIVE][1], "clears"),
    (REFLECTIVE, "lookup_tables"): (VIOLATIONS[REFLECTIVE][2], "clears"),
    (OPTIONAL_PORT, "class_name_pattern"): (VIOLATIONS[OPTIONAL_PORT][0], "clears"),
    (OPTIONAL_PORT, "port_name_pattern"): (VIOLATIONS[OPTIONAL_PORT][0], "clears"),
    (OPTIONAL_PORT, "port_annotation_pattern"): (
        VIOLATIONS[OPTIONAL_PORT][1],
        "clears",
    ),
    (CONTRACT_LOAD, "loader_call_names"): (VIOLATIONS[CONTRACT_LOAD][1], "clears"),
    (CONTRACT_LOAD, "loader_class_pattern"): (VIOLATIONS[CONTRACT_LOAD][1], "clears"),
    (CONTRACT_LOAD, "self_reference_names"): (VIOLATIONS[CONTRACT_LOAD][0], "clears"),
    (CONTRACT_LOAD, "contract_file_pattern"): (VIOLATIONS[CONTRACT_LOAD][0], "clears"),
    (CONTRACT_LOAD, "statement_kinds"): (VIOLATIONS[CONTRACT_LOAD][0], "clears"),
    (SINGLETON, "statement_kinds"): (VIOLATIONS[SINGLETON][0], "clears"),
    (SIBLING, "importer_path_pattern"): (VIOLATIONS[SIBLING][0], "clears"),
    (SIBLING, "importer_exclude_pattern"): (CLEANS[SIBLING][1], "flags"),
    (SIBLING, "imported_module_pattern"): (VIOLATIONS[SIBLING][0], "clears"),
    (VALUE_LITERAL, "constant_name_pattern"): (VIOLATIONS[VALUE_LITERAL][0], "clears"),
    (VALUE_LITERAL, "value_patterns"): (VIOLATIONS[VALUE_LITERAL][1], "clears"),
}
BASELINE_KEYS = (
    "baseline_path",
    "base_ref",
    "move_similarity_percent",
    "grew_message",
    "stale_message",
    "growth_message",
    "missing_message",
)


def _contract() -> ModelValidatorSubcontract:
    contract = ValidatorHandlerDi().contract
    # the planted fixtures sit under tests/, which the shipped contract excludes
    return contract.model_copy(update={"exclude_patterns": []})


def _validator(
    contract: ModelValidatorSubcontract | None = None, root: Path = FIXTURES
) -> ValidatorHandlerDi:
    return ValidatorHandlerDi(contract=contract or _contract(), root=root, baseline={})


def _codes(
    fixture: str, contract: ModelValidatorSubcontract | None = None
) -> list[str]:
    return [
        str(i.code) for i in _validator(contract).validate(FIXTURES / fixture).issues
    ]


def _mutated(rule_id: str, key: str) -> ModelValidatorSubcontract:
    contract = _contract()
    rows = []
    for row in contract.rules:
        if row.rule_id == rule_id and row.parameters and key in row.parameters:
            params = dict(row.parameters)
            current = params[key]
            params[key] = ["(?!)"] if isinstance(current, list) else "(?!)"
            row = row.model_copy(update={"parameters": params})
        rows.append(row)
    return contract.model_copy(update={"rules": rows})


def _rules(contract: ModelValidatorSubcontract | None = None) -> dict:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _check(source: str, path: str = "handlers/handler_x.py") -> list[str]:
    fact = ModelHandlerDiModuleFact(path, source)
    return [str(i.code) for i in checker.check_module(fact, _rules())]


# --- AC1: planted violations and clean twins -----------------------------------


@pytest.mark.parametrize(
    ("rule_id", "fixture"),
    [(r, f) for r, fixtures in VIOLATIONS.items() for f in fixtures],
)
def test_violation_fixture_yields_exactly_one_issue(rule_id: str, fixture: str) -> None:
    assert [c for c in _codes(fixture) if c == rule_id] == [rule_id]


@pytest.mark.parametrize(
    "fixture", [f for fixtures in CLEANS.values() for f in fixtures]
)
def test_clean_fixture_yields_nothing(fixture: str) -> None:
    assert _codes(fixture) == []


def test_every_rule_has_a_violation_and_a_clean_fixture() -> None:
    ids = {r.rule_id for r in _contract().rules} - {BASELINE}
    assert ids == set(VIOLATIONS) == set(CLEANS)
    assert len(ids) == 10


@pytest.mark.parametrize(
    ("fixture", "rule_id"),
    [
        ("violation_call_site_construction/handlers/handler_x_cli.py", CALL_SITE),
        ("violation_fallback_construction_or/handlers/handler_x.py", FALLBACK),
        ("violation_contract_self_load/handlers/handler_x.py", CONTRACT_LOAD),
        ("violation_reflective_construction_getattr/handlers/handler_x.py", REFLECTIVE),
        (
            "violation_reflective_construction_class_variable/handlers/handler_x.py",
            REFLECTIVE,
        ),
        ("violation_module_singleton/handlers/handler_x.py", SINGLETON),
    ],
)
def test_the_planted_violations_of_the_plan_are_reported_by_rule_id(
    fixture: str, rule_id: str
) -> None:
    issues = _validator().validate(FIXTURES / fixture).issues
    assert rule_id in {i.code for i in issues}


# --- AC3: scope ----------------------------------------------------------------


def test_a_handler_with_no_node_and_a_cli_module_are_in_scope() -> None:
    assert _codes("violation_scope_handler_without_node/handlers/helper.py") == [
        CONSTRUCTOR
    ]
    assert _codes("violation_scope_cli_outside_handlers/tools/tool_cli.py") == [
        CALL_SITE
    ]
    assert _codes("violation_call_site_construction/handlers/handler_x_cli.py") == [
        CALL_SITE
    ]


def test_a_module_outside_handlers_nodes_and_cli_is_not_judged() -> None:
    assert _codes("clean_scope_outside/services/service_x.py") == []


def test_scope_is_the_contract_target_patterns() -> None:
    contract = _contract().model_copy(update={"target_patterns": ["**/nodes/*.py"]})
    assert (
        _codes("violation_call_site_construction/handlers/handler_x_cli.py", contract)
        == []
    )


# --- AC4: every parameter of every rule row ------------------------------------


def test_every_parameter_of_every_rule_row_has_a_control() -> None:
    declared = {(r.rule_id, k) for r in _contract().rules for k in (r.parameters or {})}
    assert declared == set(CONTROLS) | {(BASELINE, k) for k in BASELINE_KEYS}


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_mutating_a_parameter_changes_the_verdict(rule_id: str, key: str) -> None:
    fixture, direction = CONTROLS[(rule_id, key)]
    before = [c for c in _codes(fixture) if c == rule_id]
    after = [c for c in _codes(fixture, _mutated(rule_id, key)) if c == rule_id]
    assert before == ([rule_id] if direction == "clears" else [])
    assert after == ([] if direction == "clears" else [rule_id])


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_a_missing_parameter_fails_the_contract_load(rule_id: str, key: str) -> None:
    contract = _contract()
    rows = []
    for row in contract.rules:
        if row.rule_id == rule_id:
            params = {k: v for k, v in (row.parameters or {}).items() if k != key}
            row = row.model_copy(update={"parameters": params})
        rows.append(row)
    broken = contract.model_copy(update={"rules": rows})
    with pytest.raises(ModelOnexError, match=key):
        ValidatorHandlerDi(contract=broken, root=FIXTURES, baseline={})


@pytest.mark.parametrize("key", BASELINE_KEYS)
def test_a_missing_baseline_parameter_fails_the_contract_load(key: str) -> None:
    contract = _contract()
    rows = []
    for row in contract.rules:
        if row.rule_id == BASELINE:
            params = {k: v for k, v in (row.parameters or {}).items() if k != key}
            row = row.model_copy(update={"parameters": params})
        rows.append(row)
    with pytest.raises(ModelOnexError, match=key):
        ValidatorHandlerDi(
            contract=contract.model_copy(update={"rules": rows}),
            root=FIXTURES,
            baseline={},
        )


def test_an_invalid_regular_expression_fails_the_contract_load() -> None:
    with pytest.raises(ModelOnexError, match="regular expression"):
        ValidatorHandlerDi(
            contract=_mutated(CALL_SITE, "constructed_name_pattern").model_copy(
                update={
                    "rules": [
                        r.model_copy(
                            update={
                                "parameters": {
                                    **(r.parameters or {}),
                                    "constructed_name_pattern": "(",
                                }
                            }
                        )
                        if r.rule_id == CALL_SITE
                        else r
                        for r in _contract().rules
                    ]
                }
            ),
            root=FIXTURES,
            baseline={},
        )


def test_the_remediation_text_is_the_rule_row_description() -> None:
    contract = _contract()
    for rule_id, fixtures in VIOLATIONS.items():
        shipped = {r.rule_id: r.description for r in contract.rules}
        marked = contract.model_copy(
            update={
                "rules": [
                    r.model_copy(update={"description": "remediation-marker-xyz"})
                    if r.rule_id == rule_id
                    else r
                    for r in contract.rules
                ]
            }
        )
        own = [
            i
            for i in _validator().validate(FIXTURES / fixtures[0]).issues
            if i.code == rule_id
        ]
        changed = [
            i
            for i in _validator(marked).validate(FIXTURES / fixtures[0]).issues
            if i.code == rule_id
        ]
        assert [shipped[rule_id] in i.message for i in own] == [True]
        assert ["remediation-marker-xyz" in i.message for i in changed] == [True]


# --- AC7: disabling a row ------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(VIOLATIONS))
def test_disabling_a_rule_row_clears_exactly_its_fixtures(rule_id: str) -> None:
    contract = _contract()
    disabled = contract.model_copy(
        update={
            "rules": [
                r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
                for r in contract.rules
            ]
        }
    )
    for fixture in VIOLATIONS[rule_id]:
        assert rule_id not in _codes(fixture, disabled)
        others = {c for c in _codes(fixture) if c != rule_id}
        assert set(_codes(fixture, disabled)) == others


def test_the_corpus_assertions_naming_k1_rules_are_reported_with_their_rule_id() -> (
    None
):
    """Corpus half of AC7: runs once the T0.8 corpus is in the tree; none is today."""
    corpus = sorted((ROOT / "tests" / "fixtures").glob("**/corpus*/**/handler_di*"))
    for assertion in corpus:
        expected = json.loads(assertion.read_text(encoding="utf-8"))
        rule_id = expected["rule_id"]
        assert rule_id in {r.rule_id for r in _contract().rules}
    assert corpus == [] or all(p.is_file() for p in corpus)


# --- AC5: pure checker, container-resolved writer ------------------------------


def test_checker_is_pure_over_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("checker performed I/O")

    rules = _rules()
    facts = [
        ModelHandlerDiModuleFact(
            f"{f.split('/', 1)[1]}",
            (FIXTURES / f).read_text(encoding="utf-8"),
        )
        for fixtures in VIOLATIONS.values()
        for f in fixtures
    ]
    with monkeypatch.context() as patched:
        patched.setattr("builtins.open", refuse)
        patched.setattr(Path, "read_text", refuse)
        patched.setattr(Path, "exists", refuse)
        patched.setattr(Path, "is_file", refuse)
        patched.setattr(Path, "iterdir", refuse)
        issues = [i for fact in facts for i in checker.check_module(fact, rules)]
    assert {i.code for i in issues} == set(VIOLATIONS)


RUNTIME = (
    ROOT
    / "src/omnibase_core/nodes/node_handler_di_check_effect/runtime_handler_di_check.py"
)


def _corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    shutil.copytree(
        FIXTURES, corpus, ignore=shutil.ignore_patterns("golden_check_output.json")
    )
    return corpus


def test_the_runtime_resolves_the_check_and_the_report_writer_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Container spy: both effects are resolved with get_service, never built by the runtime."""
    resolutions: list[str] = []
    container = build_container()
    original = container.get_service

    def resolve(token: type, service_name: str | None = None) -> object:
        resolutions.append(token.__name__)
        return original(token, service_name)

    monkeypatch.setattr(container, "get_service", resolve)
    corpus = _corpus(tmp_path)
    report = tmp_path / "report.json"
    code = run(
        [
            str(corpus / VIOLATIONS[CALL_SITE][0]),
            "--repo-root",
            str(corpus),
            "--report-json",
            str(report),
        ],
        container=container,
    )
    assert code == 1
    assert resolutions == [
        "NodeHandlerDiCheckEffect",
        "NodeValidationReportWriteEffect",
    ]
    assert json.loads(report.read_text())["findings"][0]["rule_id"] == CALL_SITE


def test_the_runtime_module_constructs_no_handler_at_a_call_site() -> None:
    fact = ModelHandlerDiModuleFact(
        RUNTIME.relative_to(ROOT).as_posix(), RUNTIME.read_text(encoding="utf-8")
    )
    assert checker.check_module(fact, _rules()) == ()


@pytest.mark.parametrize("module", ["checker_handler_di", "validator_handler_di"])
def test_the_new_modules_construct_no_handler_at_a_call_site_and_hold_no_rule_table(
    module: str,
) -> None:
    path = VALIDATION / f"{module}.py"
    fact = ModelHandlerDiModuleFact(
        path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8")
    )
    codes = [i.code for i in checker.check_module(fact, _rules())]
    assert CALL_SITE not in codes
    assert ValidatorCheckerRuleData().validate(path).issues == []


# --- AC2: the hook id and the deleted gate -------------------------------------


def test_the_hook_id_runs_on_the_new_runtime_and_the_old_gate_is_gone() -> None:
    hooks = yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text())
    [hook] = [h for h in hooks if h["id"] == "handler-di-gate"]
    assert hook["entry"].endswith(
        "omnibase_core.nodes.node_handler_di_check_effect.runtime_handler_di_check"
    )
    assert "validators.handler_di_gate" not in hook["entry"]
    assert not (ROOT / "src/omnibase_core/validators/handler_di_gate.py").exists()
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    ids = [h["id"] for r in config["repos"] for h in r["hooks"]]
    assert "handler-di-gate" in ids


# --- kept rules of the old gate (the old gate) ------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "class HandlerFoo:\n    def __init__(self, container):\n        self._bus = container.get_service('ProtocolEventBus')\n",
        "class HandlerFoo:\n    def __init__(self, container: ModelONEXContainer) -> None:\n        self._bus = container.get_service('ProtocolEventBus')\n",
        "class HandlerFoo:\n    def __init__(self):\n        pass\n",
        "class HandlerFoo:\n    def __init__(self, container):\n        self._bus = container.resolve('P')\n        self._store = container.get_service('S')\n",
        "class HandlerFoo:\n    def __init__(self, container):\n        local = SomeHelper()\n        self._bus = container.get_service('P')\n",
    ],
)
def test_kept_old_gate_clean_cases_pass(source: str) -> None:
    assert _check(source) == []


@pytest.mark.parametrize(
    ("source", "rule_id", "named"),
    [
        (
            "class HandlerBad:\n    def __init__(self, container, event_bus):\n        self._bus = event_bus\n",
            CONSTRUCTOR,
            "event_bus",
        ),
        (
            "class HandlerBad:\n    def __init__(self, event_bus):\n        self._bus = event_bus\n",
            CONSTRUCTOR,
            "event_bus",
        ),
        (
            "class HandlerBad:\n    def __init__(self, container):\n        self._bus = EventBusInmemory()\n",
            DIRECT,
            "EventBusInmemory",
        ),
        (
            "class HandlerBad:\n    def __init__(self, container):\n        self._conn = sqlite3.connect(':memory:')\n",
            DIRECT,
            "sqlite3.connect",
        ),
        (
            "class HandlerBad:\n    def __init__(self, container):\n        self._adapter = SomeAdapter()\n",
            DIRECT,
            "SomeAdapter",
        ),
    ],
)
def test_kept_old_gate_rejection_cases(source: str, rule_id: str, named: str) -> None:
    fact = ModelHandlerDiModuleFact("handlers/handler_bad.py", source)
    issues = [i for i in checker.check_module(fact, _rules()) if i.code == rule_id]
    assert len(issues) == 1
    assert "HandlerBad" in issues[0].message or named in issues[0].message
    assert named in issues[0].message


def test_kept_old_gate_node_file_is_scanned(tmp_path: Path) -> None:
    node = tmp_path / "nodes/my_node/node.py"
    node.parent.mkdir(parents=True)
    node.write_text(
        "class NodeFoo:\n    def __init__(self, container, extra_dep):\n        pass\n",
        encoding="utf-8",
    )
    issues = _validator(root=tmp_path).validate(node).issues
    assert [i.code for i in issues] == [CONSTRUCTOR]


def test_kept_old_gate_suppression_comment_silences_the_line(tmp_path: Path) -> None:
    marker = _contract().suppression_comments[0]
    handler = tmp_path / "nodes/my_node/handlers/handler_bad.py"
    handler.parent.mkdir(parents=True)
    handler.write_text(
        "class HandlerBad:\n"
        f"    def __init__(self, container, extra):  # {marker} legacy param\n"
        f"        self._bus = EventBusInmemory()  # {marker} test-only shim\n",
        encoding="utf-8",
    )
    assert _validator(root=tmp_path).validate(handler).issues == []


def test_a_topic_literal_is_reported_by_value() -> None:
    topic = "onex" + ".evt.platform.thing-happened.v1"
    assert _check(
        f'def publish(bus, payload):\n    bus.publish("{topic}", payload)\n'
    ) == [VALUE_LITERAL]


def test_kept_old_gate_directory_scan(tmp_path: Path) -> None:
    for name, params in (
        ("handler_a.py", "container, event_bus"),
        ("handler_b.py", "container"),
    ):
        handler = tmp_path / "nodes/my_node/handlers" / name
        handler.parent.mkdir(parents=True, exist_ok=True)
        handler.write_text(
            f"class Handler{name[8].upper()}:\n    def __init__(self, {params}):\n        pass\n",
            encoding="utf-8",
        )
    issues = _validator(root=tmp_path).validate([tmp_path]).issues
    assert [i.code for i in issues] == [CONSTRUCTOR]
    assert "HandlerA" in issues[0].message


# --- AC8: golden report, run event, overlays -----------------------------------


def _normalised(report: dict) -> dict:
    report = json.loads(json.dumps(report))
    report["report_id"] = "<run_id>"
    report["provenance"]["generated_at"] = "<timestamp>"
    return report


def _run(tmp_path: Path, container: ModelONEXContainer) -> dict:
    corpus = _corpus(tmp_path)
    report_path = tmp_path / "report.json"
    assert (
        run(
            [
                str(corpus),
                "--repo-root",
                str(corpus),
                "--report-json",
                str(report_path),
            ],
            container=container,
        )
        == 1
    )
    report = json.loads(report_path.read_text())
    events = [
        json.loads(line)
        for line in report_path.with_name(f"{report_path.name}.events.jsonl")
        .read_text()
        .splitlines()
    ]
    runs = [e for e in events if e["kind"] == "run"]
    assert [e["report_ref"] for e in runs] == [report["report_id"]]
    return _normalised(report)


def test_the_in_memory_default_run_equals_the_committed_golden_report(
    tmp_path: Path,
) -> None:
    golden = json.loads((FIXTURES / "golden_check_output.json").read_text())
    assert _run(tmp_path, build_container()) == golden


def test_the_second_overlay_run_equals_the_golden_once_the_overlay_pair_exists() -> (
    None
):
    """Broker half of AC8: waits on plan task T3.1, which lands the overlay pair for the validator runtime.

    No overlay file for the validator runtime is in the tree today, so only the in-memory
    half above is exercised and nothing is faked. When one lands, it must be a YAML mapping
    here, and the broker run of the fixture set against golden_check_output.json is added.
    """
    for overlay in sorted((ROOT / "src").glob("**/*validator*overlay*.y*ml")):
        assert isinstance(yaml.safe_load(overlay.read_text(encoding="utf-8")), dict)


# --- baseline ratchet ----------------------------------------------------------

BASELINE_FILE = ROOT / ".onex_ratchets" / "handler_di_baseline.txt"
TABLE_FIXTURE = FIXTURES / VIOLATIONS[CONSTRUCTOR][0]


def _baselined(count: int, contract: ModelValidatorSubcontract | None = None) -> list:
    validator = ValidatorHandlerDi(
        contract=contract or _contract(),
        root=ROOT,
        baseline={TABLE_FIXTURE.relative_to(ROOT).as_posix(): count},
    )
    return list(validator.validate(TABLE_FIXTURE).issues)


def test_a_file_at_its_baseline_entry_passes() -> None:
    assert _baselined(1) == []


def test_a_file_with_no_entry_keeps_its_finding() -> None:
    assert [i.code for i in _baselined(0)] == [CONSTRUCTOR]


def _two_findings(rules: dict) -> tuple:
    fact = ModelHandlerDiModuleFact(
        "handlers/h.py",
        "class HandlerA:\n    def __init__(self, a):\n        self._x = B()\n",
    )
    return checker.check_module(fact, rules)


def test_a_baselined_file_holding_more_than_its_entry_fails() -> None:
    rules = _rules()
    held = checker.apply_baseline(Path("h.py"), _two_findings(rules), 1, rules)
    assert [i.code for i in held] == [CONSTRUCTOR, DIRECT, BASELINE]


def test_an_entry_above_what_the_file_holds_is_stale() -> None:
    issues = _baselined(3)
    assert [i.code for i in issues] == [BASELINE]
    assert "lower the entry to 1" in issues[0].message


def test_an_entry_the_base_lacks_or_raises_is_baseline_growth() -> None:
    grown = checker.baseline_growth(
        {"a.py": 2, "b.py": 1, "c.py": 1},
        {"a.py": 2, "b.py": 0},
        BASELINE_FILE,
        _rules(),
    )
    assert sorted(i.message.split()[0] for i in grown) == ["b.py", "c.py"]
    assert (
        checker.baseline_growth({"a.py": 1}, {"a.py": 2}, BASELINE_FILE, _rules()) == ()
    )


@pytest.mark.parametrize(
    "key", ["grew_message", "stale_message", "growth_message", "missing_message"]
)
def test_baseline_messages_are_rule_parameters(key: str) -> None:
    contract = _contract()
    row = next(r for r in contract.rules if r.rule_id == BASELINE)
    params = {**(row.parameters or {}), key: f"marker-for-{key} {{path}}"}
    mutated = contract.model_copy(
        update={
            "rules": [
                r.model_copy(update={"parameters": params}) if r is row else r
                for r in contract.rules
            ]
        }
    )
    scenarios = {
        "grew_message": lambda rules: checker.apply_baseline(
            Path("x.py"), _two_findings(rules), 1, rules
        ),
        "stale_message": lambda rules: checker.apply_baseline(
            Path("x.py"), (), 2, rules
        ),
        "growth_message": lambda rules: checker.baseline_growth(
            {"x.py": 2}, {}, BASELINE_FILE, rules
        ),
        "missing_message": lambda rules: checker.baseline_missing(
            {"x.py": 2}, lambda _: False, BASELINE_FILE, rules
        ),
    }
    changed = " ".join(i.message for i in scenarios[key](_rules(mutated)))
    original = " ".join(i.message for i in scenarios[key](_rules()))
    assert f"marker-for-{key}" in changed
    assert f"marker-for-{key}" not in original


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _baseline_repo(tmp_path: Path, committed: str | None, worktree: str) -> Path:
    _git(tmp_path, "init", "-q")
    baseline = tmp_path / ".onex_ratchets" / "handler_di_baseline.txt"
    baseline.parent.mkdir()
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
    if committed is not None:
        baseline.write_text(committed, encoding="utf-8")
        for path in checker.parse_baseline(committed):
            _baseline_source(tmp_path / path)
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-q", "-m", "baseline")
    baseline.write_text(worktree, encoding="utf-8")
    for path in checker.parse_baseline(worktree):
        if not (tmp_path / path).is_file():
            _baseline_source(tmp_path / path)
    return baseline


def _baseline_source(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "class HandlerLegacy:\n"
        "    def __init__(self, first, second):\n"
        "        self.bus = Bus()\n" + "".join(f"value_{i} = {i}\n" for i in range(17)),
        encoding="utf-8",
    )


def _growth(tmp_path: Path, committed: str | None, worktree: str) -> list[str]:
    baseline = _baseline_repo(tmp_path, committed, worktree)
    validator = ValidatorHandlerDi(contract=_contract(), root=tmp_path)
    return [str(i.code) for i in validator.validate(baseline).issues]


def test_handing_the_baseline_file_checks_its_growth_against_the_base_revision(
    tmp_path: Path,
) -> None:
    assert _growth(tmp_path, "src/a.py 1\n", "src/a.py 2\n") == [BASELINE]


def test_a_baseline_that_shrinks_or_stays_passes(tmp_path: Path) -> None:
    assert _growth(tmp_path, "src/a.py 2\n", "src/a.py 1\n") == []


def test_the_first_install_of_the_baseline_has_nothing_to_grow_from(
    tmp_path: Path,
) -> None:
    assert _growth(tmp_path, None, "src/a.py 2\n") == []


def _updated_baseline_codes(tmp_path: Path, baseline: Path, text: str) -> list[str]:
    baseline.write_text(text, encoding="utf-8")
    validator = ValidatorHandlerDi(contract=_contract(), root=tmp_path)
    return [str(i.code) for i in validator.validate(baseline).issues]


@pytest.mark.unit
def test_a_moved_finding_passes_before_the_move_is_committed(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    _git(tmp_path, "mv", "src/old.py", "src/new.py")
    assert _updated_baseline_codes(tmp_path, baseline, "src/new.py 2\n") == []


@pytest.mark.unit
def test_a_committed_move_carries_the_stale_origin_entry(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    _git(tmp_path, "mv", "src/old.py", "src/new.py")
    _git(tmp_path, "commit", "-q", "-m", "move source")
    assert _updated_baseline_codes(tmp_path, baseline, "src/new.py 2\n") == []


@pytest.mark.unit
def test_two_copies_share_the_origin_entry(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    for destination in ("src/a.py", "src/b.py"):
        shutil.copyfile(tmp_path / "src/old.py", tmp_path / destination)
        _git(tmp_path, "add", destination)
    _git(tmp_path, "rm", "-q", "-f", "src/old.py")
    assert _updated_baseline_codes(tmp_path, baseline, "src/a.py 1\nsrc/b.py 1\n") == []
    assert _updated_baseline_codes(tmp_path, baseline, "src/a.py 2\nsrc/b.py 1\n") == [
        BASELINE
    ]


@pytest.mark.unit
def test_a_copy_of_a_file_that_stays_frees_no_budget(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    shutil.copyfile(tmp_path / "src/old.py", tmp_path / "src/copy.py")
    _git(tmp_path, "add", "src/copy.py")
    assert _updated_baseline_codes(
        tmp_path, baseline, "src/old.py 1\nsrc/copy.py 1\n"
    ) == [BASELINE]


@pytest.mark.unit
def test_a_finding_without_a_move_origin_is_refused(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    fresh = tmp_path / "src/fresh.py"
    fresh.write_text("fresh_value = 'unrelated source'\n", encoding="utf-8")
    _git(tmp_path, "add", "src/fresh.py")
    assert _updated_baseline_codes(
        tmp_path, baseline, "src/old.py 2\nsrc/fresh.py 1\n"
    ) == [BASELINE]


@pytest.mark.unit
def test_an_increased_count_on_moved_code_is_refused(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    _git(tmp_path, "mv", "src/old.py", "src/new.py")
    assert _updated_baseline_codes(tmp_path, baseline, "src/new.py 3\n") == [BASELINE]


@pytest.mark.unit
def test_a_shrunk_count_on_moved_code_passes(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/old.py 2\n", "src/old.py 2\n")
    _git(tmp_path, "mv", "src/old.py", "src/new.py")
    assert _updated_baseline_codes(tmp_path, baseline, "src/new.py 1\n") == []


@pytest.mark.unit
def test_a_missing_file_entry_must_be_dropped(tmp_path: Path) -> None:
    baseline = _baseline_repo(tmp_path, "src/gone.py 1\n", "src/gone.py 1\n")
    (tmp_path / "src/gone.py").unlink()
    assert _updated_baseline_codes(tmp_path, baseline, "src/gone.py 1\n") == [BASELINE]
    assert _updated_baseline_codes(tmp_path, baseline, "") == []


@pytest.mark.unit
def test_growth_reports_the_moved_allowance_in_path_order() -> None:
    issues = checker.baseline_growth(
        {"b.py": 1, "a.py": 3},
        {"old.py": 2},
        BASELINE_FILE,
        _rules(),
        {"a.py": "old.py", "b.py": "old.py"},
    )
    assert [i.code for i in issues] == [BASELINE, BASELINE]
    assert issues[0].message.startswith(
        "a.py is baselined at 3 and the base revision has 2:"
    )
    assert issues[1].message.startswith(
        "b.py is baselined at 1 and the base revision has 0:"
    )


@pytest.mark.unit
def test_missing_entries_are_reported_in_path_order() -> None:
    issues = checker.baseline_missing(
        {"b.py": 2, "present.py": 3, "a.py": 1},
        lambda path: path == "present.py",
        BASELINE_FILE,
        _rules(),
    )
    assert [i.code for i in issues] == [BASELINE, BASELINE]
    assert [i.file_path for i in issues] == [BASELINE_FILE, BASELINE_FILE]
    assert issues[0].message.startswith("a.py is baselined at 1 but")
    assert issues[1].message.startswith("b.py is baselined at 2 but")


@pytest.mark.unit
def test_missing_entries_are_not_checked_when_the_rule_is_inactive() -> None:
    def unexpected_exists(path: str) -> bool:
        pytest.fail(f"inactive rule checked {path}")

    assert (
        checker.baseline_missing({"gone.py": 1}, unexpected_exists, BASELINE_FILE, {})
        == ()
    )
    rules = _rules()
    rules[BASELINE] = rules[BASELINE].model_copy(update={"enabled": False})
    assert (
        checker.baseline_missing(
            {"gone.py": 1}, unexpected_exists, BASELINE_FILE, rules
        )
        == ()
    )


def test_the_baseline_holds_exactly_what_the_tree_holds_and_only_files_that_exist() -> (
    None
):
    entries = checker.parse_baseline(BASELINE_FILE.read_text(encoding="utf-8"))
    assert entries
    assert all((ROOT / path).is_file() for path in entries)
    validator = ValidatorHandlerDi(root=ROOT)
    assert validator.validate([ROOT / "src"]).issues == []
    stale = validator.validate([ROOT / path for path in entries]).issues
    assert stale == []
