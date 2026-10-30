# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-driven event-chain tests using the shipped rule data (OMN-21558)."""

from __future__ import annotations

import builtins
from collections import Counter
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
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
from omnibase_core.validation import validator_event_chain_walker
from omnibase_core.validation.checker_event_chain_walker import check_event_chain
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    main as hardcoded_model_config_main,
)
from omnibase_core.validation.validator_contract_walker import load_machines
from omnibase_core.validation.validator_event_chain_walker import (
    ValidatorEventChainWalker,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_url_authority import ValidatorUrlAuthority
from omnibase_core.validators.contract_config_compliance import validate_paths

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/event_chain_walker.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/event_chain_walker"
_MARK = "changed-remediation"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_rule(
    contract: ModelValidatorSubcontract, rule_id: str, **changes: object
) -> ModelValidatorSubcontract:
    return contract.model_copy(
        update={
            "rules": [
                rule.model_copy(update=changes) if rule.rule_id == rule_id else rule
                for rule in contract.rules
            ]
        }
    )


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
    return _FIXTURES / f"{kind}_{rule_id}.contract.yaml"


def _facts(
    paths: list[Path],
) -> tuple[dict[str, dict[str, object]], dict[str, ModelFSMSubcontract]]:
    documents = {}
    fsms = {}
    for path in paths:
        documents[path.as_posix()] = yaml.safe_load(path.read_text(encoding="utf-8"))
        machines, not_armed = load_machines([path])
        assert not_armed == [], not_armed
        for machine in machines:
            fsms[path.as_posix()] = machine.fsm
    return documents, fsms


def _issues(
    contract: ModelValidatorSubcontract, path: Path
) -> list[ModelValidationIssue]:
    return check_event_chain(*_facts([path]), contract.rules)


_RULES = [rule.rule_id for rule in _contract().rules]
_PARAMETERS = [
    (rule.rule_id, key)
    for rule in _contract().rules
    for key in sorted(rule.parameters or {})
]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    path = _fixture("violation", rule_id)
    issues = _issues(_contract(), path)
    assert [issue.code for issue in issues] == [rule_id]
    assert [issue.rule_name for issue in issues] == [rule_id]
    assert issues[0].file_path == path
    rule = next(rule for rule in _contract().rules if rule.rule_id == rule_id)
    assert issues[0].message.endswith(f" -- {(rule.parameters or {})['remediation']}")


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    assert _issues(_contract(), _fixture("clean", rule_id)) == []


def test_planted_set_names_all_four_rules_once_and_repaired_set_is_clean() -> None:
    for kind in ("violation", "clean"):
        paths = [_fixture(kind, rule_id) for rule_id in _RULES]
        issues = check_event_chain(*_facts(paths), _contract().rules)
        assert Counter(i.code for i in issues) == (
            Counter(_RULES) if kind == "violation" else Counter()
        )
        for issue in issues:
            assert issue.file_path == _fixture(kind, str(issue.code))


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture(rule_id: str) -> None:
    contract = _with_rule(_contract(), rule_id, enabled=False)
    assert _issues(contract, _fixture("violation", rule_id)) == []
    paths = [_fixture("violation", name) for name in _RULES]
    issues = check_event_chain(*_facts(paths), contract.rules)
    assert Counter(i.code for i in issues) == Counter(
        name for name in _RULES if name != rule_id
    )


def test_severity_is_error_for_every_rule_and_zero_findings_are_required() -> None:
    contract = _contract()
    assert contract.fail_on_error is True
    assert contract.fail_on_warning is False
    assert contract.max_violations == 0
    assert contract.severity_default == "error"
    assert all(rule.severity == "error" and rule.enabled for rule in contract.rules)
    for rule_id in _RULES:
        assert all(
            i.severity == "error"
            for i in _issues(contract, _fixture("violation", rule_id))
        )


def test_severity_cli_refuses_fixture_directory_and_accepts_clean_files(
    tmp_path: Path,
) -> None:
    assert (
        main(
            ValidatorEventChainWalker,
            [str(_FIXTURES), "--report-json", str(tmp_path / "refused.json")],
            build_validator_container,
        )
        == 1
    )
    assert (
        main(
            ValidatorEventChainWalker,
            [
                *(str(_fixture("clean", name)) for name in _RULES),
                "--report-json",
                str(tmp_path / "clean.json"),
            ],
            build_validator_container,
        )
        == 0
    )


@pytest.mark.parametrize(("rule_id", "key"), _PARAMETERS)
def test_every_parameter_key_changes_the_verdict_it_controls(
    rule_id: str, key: str
) -> None:
    contract = _contract()
    violation = _fixture("violation", rule_id)
    clean = _fixture("clean", rule_id)
    if key == "kind":
        with pytest.raises(ModelOnexError, match="unknown kind"):
            _issues(_with_parameter(contract, rule_id, key, "bogus"), violation)
    elif key == "remediation":
        issues = _issues(_with_parameter(contract, rule_id, key, _MARK), violation)
        assert len(issues) == 1 and issues[0].message.endswith(f" -- {_MARK}")
    elif (rule_id, key) in (
        ("event_without_consumer", "producer_paths"),
        ("consumer_without_producer", "consumer_paths"),
    ):
        assert _issues(_with_parameter(contract, rule_id, key, []), violation) == []
    elif (rule_id, key) in (
        ("event_without_consumer", "consumer_paths"),
        ("event_without_consumer", "external_consumer_paths"),
        ("consumer_without_producer", "producer_paths"),
        ("consumer_without_producer", "external_producer_paths"),
        ("transition_on_undeclared_event", "alphabet_paths"),
    ):
        issues = _issues(_with_parameter(contract, rule_id, key, []), clean)
        assert [issue.code for issue in issues] == [rule_id]
    elif (rule_id, key) == ("state_without_exit", "analysis_fields"):
        mutated = _with_parameter(contract, rule_id, key, ["cycles_without_exit"])
        assert _issues(mutated, violation) == []
        cycle = _fixture("cycle", rule_id)
        assert _issues(contract, cycle) == []
        assert [i.code for i in _issues(mutated, cycle)] == [rule_id]
    else:
        pytest.fail(f"no mutation case for parameter {key!r} of {rule_id}")


@pytest.mark.parametrize(("rule_id", "key"), _PARAMETERS)
def test_a_rule_row_missing_each_required_key_fails_to_load(
    rule_id: str, key: str
) -> None:
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        check_event_chain({}, {}, mutated.rules)


@pytest.mark.parametrize(
    "path",
    ["", ".", "event_bus..topics", "[]", "events[", "events[bad]", "event_bus.*bad"],
)
def test_invalid_path_fails_to_load(path: str) -> None:
    mutated = _with_parameter(
        _contract(), "event_without_consumer", "producer_paths", [path]
    )
    with pytest.raises(ModelOnexError, match="invalid path"):
        check_event_chain({}, {}, mutated.rules)


@pytest.mark.parametrize(
    "field",
    ["unknown", "is_valid", "errors", "dead_transitions", "ambiguous_transitions"],
)
def test_unknown_or_non_state_analysis_fields_fail_to_load(field: str) -> None:
    mutated = _with_parameter(
        _contract(), "state_without_exit", "analysis_fields", [field]
    )
    with pytest.raises(ModelOnexError, match="unknown analysis_fields"):
        check_event_chain({}, {}, mutated.rules)


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts([_fixture("violation", name) for name in _RULES])
    rules = _contract().rules

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    assert [i.code for i in check_event_chain(*facts, rules)] == _RULES


def test_checker_has_no_yaml_loader_and_validator_uses_walkers_load_machines() -> None:
    path = _ROOT / "src/omnibase_core/validation/checker_event_chain_walker.py"
    assert "safe_load" not in path.read_text(encoding="utf-8")
    source = _fixture("violation", "state_without_exit")
    with patch.object(
        validator_event_chain_walker, "load_machines", wraps=load_machines
    ) as loader:
        result = ValidatorEventChainWalker().validate([source])
    assert [i.code for i in result.issues] == ["state_without_exit"]
    loader.assert_called_once_with([source.resolve()])


@pytest.mark.parametrize(
    "source_name", ["checker_event_chain_walker.py", "validator_event_chain_walker.py"]
)
def test_changed_source_has_no_operational_literals(
    source_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    path = Path("src/omnibase_core/validation") / source_name
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


def test_runtime_resolves_the_writer_and_the_bus_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    container = build_validator_container()
    resolved: list[type] = []
    inner = container.get_service

    def spy(protocol_type: type, service_name: str | None = None) -> object:
        resolved.append(protocol_type)
        return inner(protocol_type, service_name)

    monkeypatch.setattr(container, "get_service", spy)
    target = tmp_path / "src/pkg/contract.yaml"
    target.parent.mkdir(parents=True)
    target.write_text(
        _fixture("violation", "event_without_consumer").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = run_validator(
        container,
        ValidatorEventChainWalker(),
        [target],
        str(tmp_path / "report.json"),
        "default",
        "repository",
    )
    assert not result.is_valid
    assert resolved == [NodeValidationReportWriteEffect, ModelValidatorRuntimeBus]


def test_cross_file_producer_and_consumer_are_clean_and_validate_file_is_a_corpus_of_one(
    tmp_path: Path,
) -> None:
    producer = tmp_path / "producer.contract.yaml"
    consumer = tmp_path / "consumer.contract.yaml"
    topic = "onex.evt.orders.cross-file.v1"
    producer.write_text(
        yaml.safe_dump({"event_bus": {"publish_topics": [topic]}}), encoding="utf-8"
    )
    consumer.write_text(
        yaml.safe_dump({"event_bus": {"subscribe_topics": [topic]}}), encoding="utf-8"
    )
    validator = ValidatorEventChainWalker()
    assert validator.validate(tmp_path).issues == []
    assert [i.code for i in validator.validate_file(producer).issues] == [
        "event_without_consumer"
    ]
    assert [i.code for i in validator.validate_file(consumer).issues] == [
        "consumer_without_producer"
    ]


def test_issues_are_ordered_by_rule_then_contract_path_then_name() -> None:
    documents = {
        "z.contract.yaml": {
            "event_bus": {"publish_topics": ["z", "a", "a"], "subscribe_topics": ["b"]}
        },
        "a.contract.yaml": {"event_bus": {"publish_topics": ["c"]}},
    }
    issues = check_event_chain(documents, {}, _contract().rules)
    assert [(i.code, str(i.file_path), i.message.split("'")[1]) for i in issues] == [
        ("event_without_consumer", "a.contract.yaml", "c"),
        ("event_without_consumer", "z.contract.yaml", "a"),
        ("event_without_consumer", "z.contract.yaml", "z"),
        ("consumer_without_producer", "z.contract.yaml", "b"),
    ]


@pytest.mark.parametrize(
    "text", ["name: one\nname: two\n", "not: [valid", "- not-a-mapping\n"]
)
def test_validator_refuses_invalid_contract_yaml(tmp_path: Path, text: str) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ModelOnexError):
        ValidatorEventChainWalker().validate([path])


def test_unarmed_machines_are_not_reloaded_or_judged(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    document = yaml.safe_load(
        _fixture("violation", "state_without_exit").read_text(encoding="utf-8")
    )
    document["state_machine"]["misspelled_key"] = True
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    machines, not_armed = load_machines([path])
    assert machines == [] and len(not_armed) == 1
    assert ValidatorEventChainWalker().validate([path]).issues == []


def _document_at(path: str, value: object) -> dict[str, object]:
    """Build facts at one path, independent of the checker's path interpreter."""
    result: object = value
    for segment in reversed(path.split(".")):
        if segment == "*":
            result = {"declared": result}
        elif segment.endswith("[]"):
            result = {segment[:-2]: [result]}
        else:
            result = {segment: result}
    return cast(dict[str, object], result)


_TOPIC_PATHS = [
    (rule.rule_id, key, path)
    for rule in _contract().rules
    for key, paths in (rule.parameters or {}).items()
    if key.endswith("_paths") and key != "alphabet_paths"
    for path in cast(list[str], paths)
]


@pytest.mark.parametrize(("rule_id", "key", "path"), _TOPIC_PATHS)
@pytest.mark.parametrize("as_list", [False, True])
def test_each_declared_topic_path_resolves_strings_and_string_lists(
    rule_id: str, key: str, path: str, as_list: bool
) -> None:
    topic = "onex.evt.orders.path-probe.v1"
    document = _document_at(path, [topic] if as_list else topic)
    rule = next(r for r in _contract().rules if r.rule_id == rule_id)
    contract = _contract().model_copy(update={"rules": [rule]})
    kind = (rule.parameters or {})["kind"]
    source_key = "producer_paths" if kind == "unconsumed_topic" else "consumer_paths"
    source_path = cast(list[str], (rule.parameters or {})[source_key])[0]
    documents = {"source.contract.yaml": _document_at(source_path, topic)}
    if key == source_key:
        documents = {"source.contract.yaml": document}
        assert [i.code for i in check_event_chain(documents, {}, contract.rules)] == [
            rule_id
        ]
    else:
        assert len(check_event_chain(documents, {}, contract.rules)) == 1
        documents["peer.contract.yaml"] = document
        assert check_event_chain(documents, {}, contract.rules) == []


@pytest.mark.parametrize(
    "path",
    cast(
        list[str],
        next(
            r
            for r in _contract().rules
            if r.rule_id == "transition_on_undeclared_event"
        ).parameters["alphabet_paths"],
    ),
)
def test_each_declared_alphabet_path_supplies_the_transition_trigger(path: str) -> None:
    documents, fsms = _facts([_fixture("violation", "transition_on_undeclared_event")])
    key = next(iter(documents))
    assert len(check_event_chain(documents, fsms, _contract().rules)) == 1
    documents[key] = _document_at(path, "complete")
    assert check_event_chain(documents, fsms, _contract().rules) == []


def test_nested_wildcard_and_mapping_lists_and_non_string_leaves() -> None:
    contract = _with_parameter(
        _contract(),
        "event_without_consumer",
        "producer_paths",
        ["groups.*.events[].topics"],
    )
    documents = {
        "node.contract.yaml": {
            "groups": {
                "one": {
                    "events": [{"topics": ["z", 7, None]}, {"topics": "a"}, "ignored"]
                },
                "two": None,
            }
        }
    }
    issues = check_event_chain(documents, {}, contract.rules)
    assert len(issues) == 2
    assert "'a'" in issues[0].message
    assert "'z'" in issues[1].message


@pytest.mark.parametrize(("rule_id", "key"), _PARAMETERS)
def test_each_mistyped_parameter_raises_even_with_no_documents(
    rule_id: str, key: str
) -> None:
    mutated = _with_parameter(_contract(), rule_id, key, 42)
    with pytest.raises(ModelOnexError):
        check_event_chain({}, {}, mutated.rules)


def test_a_named_external_producer_mapping_satisfies_its_consumer(
    tmp_path: Path,
) -> None:
    topic = "onex.cmd.orders.named-external.v1"
    contract = tmp_path / "consumer.contract.yaml"
    contract.write_text(
        yaml.safe_dump(
            {
                "event_bus": {"subscribe_topics": [topic]},
                "externally_produced_topics": [
                    {"topic": topic, "producer": "the orders CLI, not a node contract"}
                ],
            }
        ),
        encoding="utf-8",
    )
    assert ValidatorEventChainWalker().validate(tmp_path).issues == []


def test_every_shipped_contract_names_the_producer_of_each_external_topic() -> None:
    # Downstream topic graphs (omnimarket contract_topic_graph) read the
    # contracts packaged in omnibase_core and refuse a bare topic string here:
    # an external producer must be named. Shipped contracts use the mapping form.
    bare: list[str] = []
    for path in sorted((_ROOT / "src/omnibase_core").rglob("contract.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            continue
        for entry in document.get("externally_produced_topics") or []:
            if not (
                isinstance(entry, dict)
                and isinstance(entry.get("topic"), str)
                and str(entry.get("producer") or "").strip()
            ):
                bare.append(f"{path.relative_to(_ROOT)}: {entry!r}")
    assert bare == []
