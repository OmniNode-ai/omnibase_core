# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""K4 ``no_io_outside_effects`` in the generic validator format (OMN-21532).

The checker is pure; the validator reads; every list, pattern and remediation text is a
``parameters`` entry of a rule row of ``no_io_outside_effects.validation.yaml``. These
tests load that contract, so the values that gate the repository are the values under
test.
"""

from __future__ import annotations

import builtins
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.validation.model_no_io_outside_effects_facts import (
    ModelNoIoOutsideEffectsFacts,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    run_validator,
)
from omnibase_core.validation.checker_no_io_outside_effects import (
    check_no_io_outside_effects,
)
from omnibase_core.validation.validator_no_io_outside_effects import (
    ValidatorNoIoOutsideEffects,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT
    / "src/omnibase_core/validation/contracts/no_io_outside_effects.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/no_io_outside_effects"
_GOLDEN = _FIXTURES / "golden_violation_file_read.json"
_MARK = "zzz-marker"
_NEVER = ["zzz-never-matches"]
_COMPUTE = "name: node_x\nnode_type: compute\n"
_EFFECT = "name: node_x\nnode_type: effect\n"
_BROKEN_MODULE = "def broken(:\n"
_BROKEN_CONTRACT = "name: [unclosed\n"
_CLEAN_MODULE = "x = 1\n"
_ENV_MODULE = 'import os\n\nVALUE = os.getenv("X")\n'
_HANDLER = "handlers/handler_x.py"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_rule(
    contract: ModelValidatorSubcontract, rule_id: str, **changes: object
) -> ModelValidatorSubcontract:
    rules = [
        rule.model_copy(update=changes) if rule.rule_id == rule_id else rule
        for rule in contract.rules
    ]
    return contract.model_copy(update={"rules": rules})


def _with_parameter(
    contract: ModelValidatorSubcontract, rule_id: str, key: str, value: object | None
) -> ModelValidatorSubcontract:
    rule = next(r for r in contract.rules if r.rule_id == rule_id)
    parameters = dict(rule.parameters or {})
    if value is None:
        del parameters[key]
    else:
        parameters[key] = cast(RuleParameterValue, value)
    return _with_rule(contract, rule_id, parameters=parameters)


def _facts(
    contract_source: str, module_source: str | None
) -> ModelNoIoOutsideEffectsFacts:
    return ModelNoIoOutsideEffectsFacts(
        contract=ModelSourceFile(
            path="nodes/node_x/contract.yaml", source=contract_source
        ),
        module=None
        if module_source is None
        else ModelSourceFile(path=f"nodes/node_x/{_HANDLER}", source=module_source),
    )


def _check(
    contract: ModelValidatorSubcontract,
    module_source: str | None,
    contract_source: str = _COMPUTE,
) -> list[ModelValidationIssue]:
    rules = {r.rule_id: r for r in contract.rules}
    return list(
        check_no_io_outside_effects(_facts(contract_source, module_source), rules)
    )


def _ids(issues: list[ModelValidationIssue]) -> list[str | None]:
    return [issue.rule_name for issue in issues]


def _unexcluded(contract: ModelValidatorSubcontract) -> ModelValidatorSubcontract:
    """The fixtures are excluded from real runs; the tests judge them anyway."""
    return contract.model_copy(update={"exclude_patterns": []})


def _validate(
    contract: ModelValidatorSubcontract, root: Path
) -> list[ModelValidationIssue]:
    validator = ValidatorNoIoOutsideEffects(contract=_unexcluded(contract))
    return list(validator.validate([root]).issues)


def _tree(tmp_path: Path, rule_id: str, kind: str) -> Path:
    """A writable copy of a fixture tree; the unparseable contract and module and the environment read are planted here.

    Each would trip the repository's own YAML, Python or environment-inventory gate if committed.
    """
    target = tmp_path / f"{kind}_{rule_id}"
    if rule_id == "env_read":
        archetype = _COMPUTE if kind == "violation" else _EFFECT
        (target / "handlers").mkdir(parents=True)
        (target / "contract.yaml").write_text(archetype, encoding="utf-8")
        (target / _HANDLER).write_text(_ENV_MODULE, encoding="utf-8")
        return target
    if kind == "violation" and rule_id == "contract_does_not_parse":
        (target / "handlers").mkdir(parents=True)
        (target / "contract.yaml").write_text(_BROKEN_CONTRACT, encoding="utf-8")
        (target / _HANDLER).write_text(_CLEAN_MODULE, encoding="utf-8")
        return target
    shutil.copytree(_FIXTURES / f"{kind}_{rule_id}", target)
    if kind == "violation" and rule_id == "module_does_not_parse":
        (target / "handlers").mkdir()
        (target / _HANDLER).write_text(_BROKEN_MODULE, encoding="utf-8")
    return target


_RULES = [rule.rule_id for rule in _contract().rules]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    tmp_path: Path, rule_id: str
) -> None:
    issues = _validate(_contract(), _tree(tmp_path, rule_id, "violation"))
    assert [i.rule_name for i in issues] == [rule_id]
    assert [i.code for i in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(tmp_path: Path, rule_id: str) -> None:
    assert _validate(_contract(), _tree(tmp_path, rule_id, "clean")) == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture_and_only_that_rules(
    tmp_path: Path, rule_id: str
) -> None:
    """KC-replay: a disabled row clears its own fixture and no other rule's fixture."""
    contract = _with_rule(_contract(), rule_id, enabled=False)
    assert _validate(contract, _tree(tmp_path, rule_id, "violation")) == []
    for other in _RULES:
        if other != rule_id:
            issues = _validate(contract, _tree(tmp_path, other, "violation"))
            assert [i.rule_name for i in issues] == [other]


def test_ac1_file_read_and_inmemory_bus_in_a_handler_are_refused() -> None:
    read = _check(_contract(), "from pathlib import Path\n\nPath(p).read_text()\n")
    bus = _check(_contract(), "EventBusInmemory()\n")
    assert _ids(read) == ["file_read"]
    assert _ids(bus) == ["direct_bus"]


def test_a_nested_module_is_judged_and_the_nearest_contract_wins(
    tmp_path: Path,
) -> None:
    node = tmp_path / "nodes" / "node_x"
    deep = node / "handlers" / "deeper"
    deep.mkdir(parents=True)
    (node / "contract.yaml").write_text(_COMPUTE, encoding="utf-8")
    (deep / "handler_y.py").write_text("import sqlite3\n", encoding="utf-8")
    inner = node / "handlers" / "effect_inner"
    inner.mkdir()
    (inner / "contract.yaml").write_text(_EFFECT, encoding="utf-8")
    (inner / "handler_z.py").write_text("import sqlite3\n", encoding="utf-8")
    issues = _validate(_contract(), tmp_path)
    assert [(i.rule_name, i.file_path.name) for i in issues if i.file_path] == [
        ("import_database", "handler_y.py")
    ]


# --- KC-config: every parameters key controls a verdict -------------------


@dataclass(frozen=True)
class _Probe:
    """Source judged under a compute contract, the value that neutralises the key, and the verdict after."""

    source: str
    mutated: object = None
    after: tuple[str, ...] = ()


_OPEN_W = 'open(p, "w")\n'
_PROBES: dict[tuple[str, str], _Probe] = {
    ("import_database", "import_roots"): _Probe("import sqlite3\n", _NEVER),
    ("import_network", "import_roots"): _Probe("import httpx\n", _NEVER),
    ("import_network", "import_modules"): _Probe("import urllib.request\n", _NEVER),
    ("git_invocation", "import_roots"): _Probe("import git\n", _NEVER),
    ("git_invocation", "command_executables"): _Probe(
        'os.system("git status")\n', _NEVER, ("subprocess_execution",)
    ),
    ("git_invocation", "command_callee_patterns"): _Probe(
        'os.system("git status")\n', _NEVER, ("subprocess_execution",)
    ),
    ("subprocess_execution", "import_roots"): _Probe("import subprocess\n", _NEVER),
    ("subprocess_execution", "callee_patterns"): _Probe('os.system("ls")\n', _NEVER),
    ("linear_access", "import_roots"): _Probe("import linear\n", _NEVER),
    ("linear_access", "url_substrings"): _Probe('notify("linear.app/t")\n', _NEVER),
    ("filesystem_write", "open_names"): _Probe(_OPEN_W, _NEVER),
    ("filesystem_write", "open_mode_chars"): _Probe(_OPEN_W, "q"),
    ("filesystem_write", "open_when"): _Probe(_OPEN_W, "read"),
    ("filesystem_write", "method_names"): _Probe("Path(p).touch()\n", _NEVER),
    ("filesystem_write", "callee_patterns"): _Probe('os.remove("x")\n', _NEVER),
    ("direct_bus", "bus_class_patterns"): _Probe("EventBusInmemory()\n", _NEVER),
    ("direct_bus", "callee_patterns"): _Probe("confluent_kafka.Producer()\n", _NEVER),
    ("direct_adapter", "adapter_class_patterns"): _Probe("PostgresAdapter()\n", _NEVER),
    ("file_read", "open_names"): _Probe("open(p)\n", _NEVER),
    ("file_read", "open_mode_chars"): _Probe('open(p, "q")\n', "q"),
    ("file_read", "open_when"): _Probe("open(p)\n", "write"),
    ("file_read", "method_names"): _Probe("Path(p).read_text()\n", _NEVER),
    ("clock", "callee_patterns"): _Probe("time.time()\n", _NEVER),
    ("env_read", "callee_patterns"): _Probe('os.getenv("X")\n', _NEVER),
    ("env_read", "subscripts"): _Probe('os.environ["X"]\n', _NEVER),
}


def _parameter_cases() -> list[tuple[str, str]]:
    return [
        (rule.rule_id, key)
        for rule in _contract().rules
        for key in sorted(rule.parameters or {})
    ]


_SCOPE_KEYS = {
    "contract_filename",
    "archetype_fields",
    "known_archetypes",
    "exempt_archetypes",
}


def test_every_parameter_key_has_a_mutation_case() -> None:
    expected = {
        case
        for case in _parameter_cases()
        if case[1] != "remediation" and case[0] != "package_scope"
    }
    assert expected == set(_PROBES)
    assert {k for r, k in _parameter_cases() if r == "package_scope"} == (
        _SCOPE_KEYS | {"remediation"}
    )


@pytest.mark.parametrize(
    ("rule_id", "key"), [case for case in _PROBES if case[1] != "remediation"]
)
def test_mutating_a_matcher_key_changes_the_verdict_it_controls(
    rule_id: str, key: str
) -> None:
    probe = _PROBES[(rule_id, key)]
    baseline = _check(_contract(), probe.source)
    assert _ids(baseline) == [rule_id]
    mutated = _check(
        _with_parameter(_contract(), rule_id, key, probe.mutated), probe.source
    )
    assert tuple(i for i in _ids(mutated) if i) == probe.after


@pytest.mark.parametrize("rule_id", [r for r in _RULES if r != "package_scope"])
def test_mutating_remediation_changes_the_text_it_controls(
    tmp_path: Path, rule_id: str
) -> None:
    mutated = _with_parameter(_contract(), rule_id, "remediation", _MARK)
    issues = _validate(mutated, _tree(tmp_path, rule_id, "violation"))
    assert len(issues) == 1 and issues[0].suggestion == _MARK


def test_package_scope_remediation_changes_the_text_it_controls(tmp_path: Path) -> None:
    mutated = _with_parameter(_contract(), "package_scope", "remediation", _MARK)
    issues = _validate(mutated, _tree(tmp_path, "package_scope", "violation"))
    assert len(issues) == 1 and issues[0].suggestion == _MARK


def test_scope_keys_change_the_verdicts_they_control(tmp_path: Path) -> None:
    contract = _contract()
    # archetype_fields / known_archetypes: a compute contract stops being recognised
    for key in ("archetype_fields", "known_archetypes"):
        assert _check(contract, None) == []
        mutated = _with_parameter(contract, "package_scope", key, _NEVER)
        assert _ids(_check(mutated, None)) == ["package_scope"]
    # exempt_archetypes: an effect package is judged once nothing is exempt
    sql = "import sqlite3\n"
    assert _check(contract, sql, _EFFECT) == []
    mutated = _with_parameter(contract, "package_scope", "exempt_archetypes", _NEVER)
    assert _ids(_check(mutated, sql, _EFFECT)) == ["import_database"]
    # contract_filename: a contract of another name places no package
    tree = _tree(tmp_path, "import_database", "violation")
    assert len(_validate(contract, tree)) == 1
    renamed = _with_parameter(
        contract, "package_scope", "contract_filename", "zzz.yaml"
    )
    assert _validate(renamed, tree) == []


_JUDGED_BY: dict[str, tuple[str | None, str]] = {
    "package_scope": (None, "name: node_x\n"),
    "contract_does_not_parse": (None, _BROKEN_CONTRACT),
    "module_does_not_parse": (_BROKEN_MODULE, _COMPUTE),
}


@pytest.mark.parametrize("rule_id", _RULES)
def test_a_row_missing_remediation_fails_to_load(rule_id: str) -> None:
    module, contract_source = _JUDGED_BY.get(rule_id, ("import sqlite3\n", _COMPUTE))
    mutated = _with_parameter(_contract(), rule_id, "remediation", None)
    with pytest.raises(ModelOnexError):
        _check(mutated, module, contract_source)


@pytest.mark.parametrize("key", sorted(_SCOPE_KEYS - {"contract_filename"}))
def test_a_scope_row_missing_a_required_key_fails_to_load(key: str) -> None:
    mutated = _with_parameter(_contract(), "package_scope", key, None)
    with pytest.raises(ModelOnexError):
        _check(mutated, "import sqlite3\n")


def test_a_matcher_pattern_that_does_not_compile_fails_to_load() -> None:
    mutated = _with_parameter(_contract(), "clock", "callee_patterns", ["("])
    with pytest.raises(ModelOnexError, match="regular expression"):
        _check(mutated, "time.time()\n")


@pytest.mark.parametrize(
    ("rule_id", "key", "value"),
    [
        ("clock", "callee_patterns", "not-a-list"),
        ("import_database", "import_roots", [1]),
        ("clock", "stray_key", ["x"]),
        ("file_read", "open_when", "sideways"),
        ("git_invocation", "command_executables", None),
    ],
)
def test_an_invalid_row_fails_to_load_rather_than_passing(
    rule_id: str, key: str, value: object
) -> None:
    mutated = (
        _with_parameter(_contract(), rule_id, key, value)
        if value
        else _with_rule(
            _contract(),
            rule_id,
            parameters={
                k: v
                for k, v in (
                    next(
                        r for r in _contract().rules if r.rule_id == rule_id
                    ).parameters
                    or {}
                ).items()
                if k != key
            },
        )
    )
    with pytest.raises(ModelOnexError):
        _check(mutated, "x = 1\n")


def test_a_row_with_no_matcher_fails_to_load() -> None:
    mutated = _with_rule(
        _contract(), "clock", parameters={"remediation": "no matcher at all"}
    )
    with pytest.raises(ModelOnexError, match="no matcher"):
        _check(mutated, "x = 1\n")


def test_a_contract_without_a_scope_row_fails_to_load() -> None:
    rules = [r for r in _contract().rules if r.rule_id != "package_scope"]
    contract = _contract().model_copy(update={"rules": rules})
    with pytest.raises(ModelOnexError, match="package_scope"):
        _check(contract, "x = 1\n")


# --- purity and the eight kept kinds ----------------------------------------


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC5: the checker runs with ``open`` and the Path reads patched to raise."""
    rules = {r.rule_id: r for r in _contract().rules}
    facts = _facts(_COMPUTE, "Path(p).read_text()\n")

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open", "exists", "is_file"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    assert _ids(list(check_no_io_outside_effects(facts, rules))) == ["file_read"]


_KEPT = [
    ("import asyncpg\n", "import_database"),
    ("from sqlalchemy import create_engine\n", "import_database"),
    ("import httpx\n", "import_network"),
    ("import urllib.request\n", "import_network"),
    ("import subprocess\n", "subprocess_execution"),
    ("subprocess.run(['ls'])\n", "subprocess_execution"),
    ("os.system('ls')\n", "subprocess_execution"),
    ("import git\n", "git_invocation"),
    ("subprocess.run(['git', 'status'])\n", "git_invocation"),
    ("os.system('git status')\n", "git_invocation"),
    ("import linear_sdk\n", "linear_access"),
    ("notify('https://linear.app/x')\n", "linear_access"),
    ("open(p, 'w')\n", "filesystem_write"),
    ("Path(p).write_text('x')\n", "filesystem_write"),
    ("os.remove(p)\n", "filesystem_write"),
    ("shutil.rmtree(p)\n", "filesystem_write"),
    ("KafkaProducer()\n", "direct_bus"),
    ("bus = x.EventBusKafka()\n", "direct_bus"),
    ("PostgresAdapter()\n", "direct_adapter"),
    ("open(p)\n", "file_read"),
    ("datetime.now()\n", "clock"),
    ("datetime.datetime.utcnow()\n", "clock"),
    ("os.environ.get('X')\n", "env_read"),
    ("x = os.environ['X']\n", "env_read"),
]


@pytest.mark.parametrize(("source", "rule_id"), _KEPT)
def test_each_kind_is_refused_in_a_non_effect_package_and_passes_in_effect(
    source: str, rule_id: str
) -> None:
    assert _ids(_check(_contract(), source)) == [rule_id]
    assert _ids(_check(_contract(), source, "node_type: reducer\n")) == [rule_id]
    assert _check(_contract(), source, _EFFECT) == []


@pytest.mark.parametrize(
    "source",
    [
        "import json\n",
        "import time\n\ntime.sleep(1)\n",
        "container.get_service(ProtocolEventBus)\n",
        "ModelEventBusConfig()\n",
        "'text'.replace('a', 'b')\n",
        "open_things(p)\n",
    ],
)
def test_pure_code_passes(source: str) -> None:
    assert _check(_contract(), source) == []


# --- runtime: the writer and the bus come from the container ------------------


def test_runtime_resolves_the_writer_and_the_bus_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5 container spy: the report writer and the runtime bus are both resolved, never built."""
    resolved: list[type] = []
    real = ModelONEXContainer.get_service

    def spy(
        self: ModelONEXContainer, protocol_type: type, service_name: str | None = None
    ) -> object:
        resolved.append(protocol_type)
        return real(self, protocol_type, service_name)

    monkeypatch.chdir(_ROOT)
    monkeypatch.setattr(ModelONEXContainer, "get_service", spy)
    handler = HandlerValidatorRuntimeOverlay()
    profile = handler.load(handler.default_overlay_path()).profile
    report_path = tmp_path / "report.json"
    result = run_validator(
        build_validator_container(),
        ValidatorNoIoOutsideEffects(contract=_unexcluded(_contract())),
        [_FIXTURES / "violation_file_read"],
        str(report_path),
        profile,
        "example-repository",
    )
    assert not result.is_valid
    assert NodeValidationReportWriteEffect in resolved
    assert ModelValidatorRuntimeBus in resolved
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["report_id"] = "<normalised>"
    report["provenance"]["generated_at"] = "<normalised>"
    assert report == json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert [f["rule_id"] for f in report["findings"]] == ["file_read"]


def test_the_runtime_module_constructs_no_service() -> None:
    """The validator and the checker name no writer and no bus class; the runtime resolves them."""
    for name in ("checker_no_io_outside_effects", "validator_no_io_outside_effects"):
        source = (_ROOT / f"src/omnibase_core/validation/{name}.py").read_text(
            encoding="utf-8"
        )
        assert "NodeValidationReport" not in source
        assert "EventBus" not in source
        assert "asyncio" not in source
