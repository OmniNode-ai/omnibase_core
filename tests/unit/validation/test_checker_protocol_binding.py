# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the protocol-binding rules in the generic validator format (OMN-21533, K5).

A protocol is bound to its implementation in a binding site, never in the code that
needs it. The checker is pure; the validator reads a source or a contract; every
class list, binding site, pattern, threshold and remediation text is a ``parameters``
entry of a rule row of ``protocol_binding.validation.yaml``. These tests load that
contract, so the values that gate the repository are the values under test.
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import cast

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
    run_validator,
)
from omnibase_core.validation.checker_protocol_binding import (
    check_protocol_binding,
    check_setting_two_homes,
    contract_setting_keys,
    parse_baseline,
)
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    main as hardcoded_model_config_main,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_hook_writes import ValidatorHookWrites
from omnibase_core.validation.validator_protocol_binding import ValidatorProtocolBinding
from omnibase_core.validation.validator_url_authority import ValidatorUrlAuthority
from omnibase_core.validators.contract_config_compliance import validate_paths

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/protocol_binding.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/protocol_binding"
_BASELINE = _ROOT / ".onex_ratchets/protocol_binding_baseline.txt"
_MARK = "zzz-marker"
_NEVER = r"\bnever-matches-zzz\b"
_SOURCE = Path("src/pkg/module.py")
_CONTAINER_FILE = "src/omnibase_core/container/container_auto_config.py"
_BASELINED_FILES = [
    "src/omnibase_core/event_bus/testing/fixture_event_bus_substrate.py",
    "src/omnibase_core/handlers/handler_ci_inheritance_cli.py",
    "src/omnibase_core/nodes/node_source_file_gather_effect/runtime_shared_token_policy.py",
    "src/omnibase_core/runtime/harness/harness_dispatch.py",
    "src/omnibase_core/runtime/runtime_local.py",
    "src/omnibase_core/validation/doc_content_scan/runtime_doc_content_scan.py",
    "src/omnibase_core/validation/localhost_url/runtime_localhost_url.py",
    "src/omnibase_core/validation/no_faked_boundary/runtime_no_faked_boundary.py",
    "src/omnibase_core/validation/pin_hygiene/runtime_pin_hygiene.py",
    "src/omnibase_core/validation/todo_marker/runtime_todo_marker.py",
]


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


def _fixture(kind: str, rule_id: str) -> Path:
    return next(_FIXTURES.glob(f"{kind}_{rule_id}.*"))


def _issues(
    contract: ModelValidatorSubcontract,
    fixture: Path,
    baseline: dict[str, int] | None = None,
) -> list[ModelValidationIssue]:
    """The issues of one fixture: Python text through the source check, a contract bundle in order."""
    if fixture.suffix == ".txt":
        text = fixture.read_text(encoding="utf-8")
        return list(check_protocol_binding(_SOURCE, text, contract.rules, baseline))
    bundle = yaml.safe_load(fixture.read_text(encoding="utf-8"))["contracts"]
    homes: dict[str, list[str]] = {}
    issues: list[ModelValidationIssue] = []
    for name, document in bundle.items():
        keys = contract_setting_keys(document, contract.rules)
        issues.extend(check_setting_two_homes(Path(name), keys, homes, contract.rules))
        for key in keys:
            homes.setdefault(key, []).append(name)
    return issues


_RULES = [rule.rule_id for rule in _contract().rules]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    issues = _issues(_contract(), _fixture("violation", rule_id))
    assert [issue.rule_name for issue in issues] == [rule_id]
    assert [issue.code for issue in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    assert _issues(_contract(), _fixture("clean", rule_id)) == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture(rule_id: str) -> None:
    contract = _with_rule(_contract(), rule_id, enabled=False)
    assert _issues(contract, _fixture("violation", rule_id)) == []


def test_the_three_d2_k5_fixtures_are_refused() -> None:
    contract = _contract()
    sources = {
        'ProtocolEventBus = {"x": 1}\n_LOCAL_BACKENDS = {"ProtocolEventBus": "inmemory"}\n': "code_side_binding_table",
        "def build_local_bus():\n    return EventBusInmemory(name='x')\n": "default_implementation_construction",
        "def f(event_bus):\n    if isinstance(event_bus, EventBusKafka):\n        return 1\n": "implementation_isinstance_branch",
    }
    for source, rule_id in sources.items():
        issues = check_protocol_binding(_SOURCE, source, contract.rules)
        assert rule_id in [i.code for i in issues], source


def _parameter_cases() -> list[tuple[str, str]]:
    return [
        (rule.rule_id, key)
        for rule in _contract().rules
        for key in sorted(rule.parameters or {})
    ]


def _first_class(contract: ModelValidatorSubcontract, rule_id: str) -> str:
    rule = next(r for r in contract.rules if r.rule_id == rule_id)
    return cast(list[str], (rule.parameters or {})["classes"])[0]


@pytest.mark.parametrize(("rule_id", "key"), _parameter_cases())
def test_every_parameter_key_changes_the_verdict_it_controls(
    tmp_path: Path, rule_id: str, key: str
) -> None:
    """Mutate each ``parameters`` key of each rule row in turn; the verdict follows."""
    contract = _contract()
    violation = _fixture("violation", rule_id)
    clean = _fixture("clean", rule_id)
    if key == "remediation":
        issues = _issues(_with_parameter(contract, rule_id, key, _MARK), violation)
        assert len(issues) == 1 and _MARK in issues[0].message
    elif key == "classes":
        assert (
            _issues(_with_parameter(contract, rule_id, key, [_MARK]), violation) == []
        )
        both = _with_parameter(contract, rule_id, key, ["dict", "get_service"])
        assert len(_issues(both, clean)) == 1
    elif key == "binding_sites":
        source = Path(violation).read_text(encoding="utf-8")
        site = _with_parameter(contract, rule_id, key, ["src/pkg/*.py"])
        assert _issues(site, violation) == []
        assert (
            len(check_protocol_binding(Path("src/other/m.py"), source, site.rules)) == 1
        )
    elif key == "key_pattern":
        assert _issues(_with_parameter(contract, rule_id, key, _NEVER), violation) == []
        assert len(_issues(_with_parameter(contract, rule_id, key, "^.*$"), clean)) == 1
    elif key == "reexport_value_pattern":
        assert _issues(_with_parameter(contract, rule_id, key, _NEVER), clean) != []
        assert _issues(_with_parameter(contract, rule_id, key, "^.*$"), violation) == []
    elif key == "sections":
        assert (
            _issues(_with_parameter(contract, rule_id, key, [_MARK]), violation) == []
        )
    elif key == "min_homes":
        assert _issues(_with_parameter(contract, rule_id, key, 3), violation) == []
    elif key == "stale_message":
        mutated = _with_parameter(contract, rule_id, key, _MARK)
        issues = _issues(mutated, clean, {_SOURCE.as_posix(): 1})
        assert len(issues) == 1 and _MARK in issues[0].message
    elif key == "kind":
        with pytest.raises(ModelOnexError, match="unknown kind"):
            _issues(_with_parameter(contract, rule_id, key, "bogus"), violation)
    else:
        pytest.fail(f"no mutation case for parameter {key!r} of {rule_id}")


_OPTIONAL_KEYS = frozenset({"stale_message"})


@pytest.mark.parametrize(
    ("rule_id", "key"),
    [case for case in _parameter_cases() if case[1] not in _OPTIONAL_KEYS],
)
def test_a_rule_row_missing_a_required_key_fails_to_load(
    rule_id: str, key: str
) -> None:
    """An invalid contract raises rather than passing."""
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        _issues(mutated, _fixture("violation", rule_id))


def test_a_pattern_that_does_not_compile_fails_to_load() -> None:
    mutated = _with_parameter(
        _contract(), "code_side_binding_table", "key_pattern", "("
    )
    with pytest.raises(ModelOnexError, match="regular expression"):
        _issues(mutated, _fixture("violation", "code_side_binding_table"))


def test_source_that_does_not_parse_raises() -> None:
    with pytest.raises(ModelOnexError, match="does not parse"):
        check_protocol_binding(_SOURCE, "def (:", _contract().rules)


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """The checker runs with ``open`` and the Path reads patched to raise."""
    rules = _contract().rules
    text = _fixture("violation", "default_implementation_construction").read_text(
        encoding="utf-8"
    )

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    issues = check_protocol_binding(_SOURCE, text, rules)
    assert [i.rule_name for i in issues] == ["default_implementation_construction"]
    homes = {"retry_window": ["node_a/contract.yaml"]}
    two = check_setting_two_homes(
        Path("node_b/contract.yaml"), ("retry_window",), homes, rules
    )
    assert [i.rule_name for i in two] == ["setting_two_homes"]


@pytest.mark.parametrize(
    "source_name", ["checker_protocol_binding.py", "validator_protocol_binding.py"]
)
def test_changed_source_has_no_operational_literals(
    source_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5 scans source contents and refuses absent or empty scan targets."""
    monkeypatch.chdir(_ROOT)
    path = Path("src/omnibase_core/validation") / source_name
    # The scanners may skip absent paths, so require readable source first.
    assert path.read_text(encoding="utf-8").strip(), f"empty scan target: {path}"
    for validator in (
        ValidatorUrlAuthority(repo_root=_ROOT),
        ValidatorHardcodedTopics(),
    ):
        result = validator.validate([path])
        assert result.metadata is not None
        assert result.metadata.files_processed == 1
        assert result.issues == []
    assert validate_paths([path]) == []
    assert hardcoded_model_config_main([str(path)]) == 0


def test_a_binding_site_may_construct_the_default_implementation() -> None:
    text = _fixture("violation", "default_implementation_construction").read_text(
        encoding="utf-8"
    )
    assert check_protocol_binding(Path(_CONTAINER_FILE), text, _contract().rules) == ()


def test_each_construction_is_one_issue_on_its_line() -> None:
    text = "a = EventBusInmemory()\n\nb = EventBusInmemory()\n"
    issues = check_protocol_binding(_SOURCE, text, _contract().rules)
    assert [i.line_number for i in issues] == [1, 3]


def test_a_baselined_file_passes_at_its_entry_fails_above_and_is_stale_below() -> None:
    contract = _contract()
    text = "a = EventBusInmemory()\nb = EventBusInmemory()\n"
    key = _SOURCE.as_posix()
    assert check_protocol_binding(_SOURCE, text, contract.rules, {key: 2}) == ()
    assert len(check_protocol_binding(_SOURCE, text, contract.rules, {key: 1})) == 2
    stale = check_protocol_binding(_SOURCE, text, contract.rules, {key: 3})
    assert [i.code for i in stale] == ["default_implementation_construction"]
    assert "lower the entry" in stale[0].message


def test_baseline_shrinks_to_the_files_the_ticket_names() -> None:
    """The baseline holds the 10 files and not the container's own registration."""
    entries = parse_baseline(_BASELINE.read_text(encoding="utf-8"))
    assert sorted(entries) == sorted(_BASELINED_FILES)
    assert _CONTAINER_FILE not in entries
    rules = _contract().rules
    for name, count in entries.items():
        text = (_ROOT / name).read_text(encoding="utf-8")
        found = [
            i
            for i in check_protocol_binding(Path(name), text, rules)
            if i.code == "default_implementation_construction"
        ]
        assert len(found) == count, name


def test_baseline_shrinks_only_when_the_file_holds_fewer_findings() -> None:
    """An entry above what the file holds is stale; a file above its entry fails."""
    rules = _contract().rules
    name = _BASELINED_FILES[0]
    text = (_ROOT / name).read_text(encoding="utf-8")
    assert check_protocol_binding(Path(name), text, rules, {name: 1}) == ()
    assert check_protocol_binding(Path(name), text, rules, {name: 2}) != ()
    assert len(check_protocol_binding(Path(name), text, rules, {})) == 1


def test_this_repositorys_source_is_clean_against_the_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shipped contract, scan set and baseline leave ``src`` clean."""
    monkeypatch.chdir(_ROOT)
    validator = ValidatorProtocolBinding.with_baseline_file(_BASELINE)
    result = validator.validate([_ROOT / "src"])
    assert [str(i.file_path) for i in result.issues] == []


def test_validator_flags_a_second_contract_holding_the_same_setting(
    tmp_path: Path,
) -> None:
    bundle = yaml.safe_load(
        _fixture("violation", "setting_two_homes").read_text(encoding="utf-8")
    )["contracts"]
    for name, document in bundle.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True)
        target.write_text(yaml.safe_dump(document), encoding="utf-8")
    contract = _contract().model_copy(update={"exclude_patterns": []})
    result = ValidatorProtocolBinding(contract=contract, root=tmp_path).validate(
        [tmp_path]
    )
    assert [i.rule_name for i in result.issues] == ["setting_two_homes"]


def test_runtime_resolves_the_writer_and_the_bus_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A container spy records the resolution of the report writer and the bus."""
    container = build_validator_container()
    resolved: list[type] = []
    inner = container.get_service

    def spy(protocol_type: type, service_name: str | None = None) -> object:
        resolved.append(protocol_type)
        return inner(protocol_type, service_name)

    monkeypatch.setattr(container, "get_service", spy)
    target = tmp_path / "src/pkg/module.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        _fixture("violation", "default_implementation_construction").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    contract = _contract().model_copy(update={"exclude_patterns": []})
    monkeypatch.chdir(tmp_path)

    result = run_validator(
        container,
        ValidatorProtocolBinding(contract=contract, baseline={}, root=tmp_path),
        [target],
        str(tmp_path / "report.json"),
        "default",
        "repository",
    )

    assert not result.is_valid
    assert resolved == [NodeValidationReportWriteEffect, ModelValidatorRuntimeBus]


def test_the_runtime_holds_the_validator_to_the_baseline_it_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _fixture("violation", "default_implementation_construction")
    target = tmp_path / "src/pkg/module.py"
    target.parent.mkdir(parents=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    baseline = tmp_path / "held.txt"
    baseline.write_text("src/pkg/module.py 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    reference = [str(target.relative_to(tmp_path)), "--report-json", "r.json"]

    assert main(ValidatorProtocolBinding, reference, build_validator_container) == 1
    assert (
        main(
            ValidatorProtocolBinding,
            [*reference, "--baseline", str(baseline)],
            build_validator_container,
        )
        == 0
    )


def test_the_runtime_refuses_a_baseline_for_a_validator_that_takes_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "held.txt").write_text("", encoding="utf-8")
    exit_code = main(
        ValidatorHookWrites,
        ["--baseline", "held.txt", "--report-json", "r.json"],
        build_validator_container,
    )
    assert exit_code != 0
    assert "takes no baseline" in capsys.readouterr().err
