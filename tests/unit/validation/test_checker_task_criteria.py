# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pure task-criteria checker and generic validator (OMN-21535, task T0.7).

Every rule has a planted violation fixture (exactly one issue with its rule id) and a clean
fixture (no issue). All rule data lives in ``validation/contracts/task_criteria.validation.yaml``;
the table-driven mutation test changes every ``parameters`` key of every rule row in turn
and asserts the verdict changes.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.task_criteria.model_task_criteria_check_input import (
    ModelTaskCriteriaCheckInput,
)
from omnibase_core.models.task_criteria.model_task_criteria_check_result import (
    ModelTaskCriteriaCheckResult,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validation_report_publish import (
    NodeValidationReportPublishEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    run_validator,
)
from omnibase_core.validation import checker_task_criteria as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_task_criteria import check_task_criteria
from omnibase_core.validation.hardcoded_model_config import handler as model_config
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_task_criteria import ValidatorTaskCriteria
from omnibase_core.validation.validator_url_authority import scan_source
from omnibase_core.validators import contract_config_compliance

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "task_criteria"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "task_criteria.validation.yaml"
)
LIFECYCLE = {"frozen_tooling": "no-code", "fixing_tooling": "fix-only"}

RULE_IDS = {
    "missing_configuration_criterion",
    "missing_bindings_criterion",
    "criterion_without_falsifier",
    "missing_two_overlay_falsifier",
    "replay_only_bindings_falsifier",
    "missing_zero_literal_falsifier",
    "missing_container_resolution_criterion",
    "brief_missing_rule_block",
    "rule_block_incomplete",
    "task_in_frozen_repository",
}


def _source(rule_id: str, name: str = "x") -> str:
    """The document name each family of rules selects on."""
    if rule_id == "brief_missing_rule_block":
        return f"lanes/{name}/job.json"
    if rule_id == "rule_block_incomplete":
        return f"lanes/{name}/rules.md"
    return f"beta/plans/{name}.md"


def _fixture(kind: str, rule_id: str) -> str:
    suffix = "json" if rule_id == "brief_missing_rule_block" else "txt"
    return (FIXTURES / f"{kind}_{rule_id}.{suffix}").read_text("utf-8")


def _contract() -> ModelValidatorSubcontract:
    return ValidatorTaskCriteria().contract


def _check(
    rule_id: str, text: str, contract: ModelValidatorSubcontract | None = None
) -> ModelTaskCriteriaCheckResult:
    return check_task_criteria(
        ModelTaskCriteriaCheckInput(
            source_name=_source(rule_id),
            text=text,
            repository_lifecycle=LIFECYCLE,
            contract=contract or _contract(),
        )
    )


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> ModelValidatorSubcontract:
    """The committed contract with `mutate` applied to its rules, by rule id."""
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: copy.deepcopy(rule) for rule in data["rules"]}
    mutate(rules)
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def _all_verdicts(
    contract: ModelValidatorSubcontract,
) -> list[tuple[str, tuple[str, ...]]]:
    """Messages of every fixture, planted, clean and mutation, under a contract."""
    verdicts: list[tuple[str, tuple[str, ...]]] = []
    for rule_id in sorted(RULE_IDS):
        for kind in ("violation", "clean"):
            result = _check(rule_id, _fixture(kind, rule_id), contract)
            verdicts.append(
                (f"{kind}_{rule_id}", tuple(i.message for i in result.issues))
            )
    extra = (FIXTURES / "mutation_fix_only_permitted.txt").read_text("utf-8")
    result = _check("task_in_frozen_repository", extra, contract)
    verdicts.append(("mutation_fix_only", tuple(i.message for i in result.issues)))
    return verdicts


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
def test_each_violation_fixture_has_exactly_its_one_issue(rule_id: str) -> None:
    result = _check(rule_id, _fixture("violation", rule_id))
    assert [issue.code for issue in result.issues] == [rule_id]
    assert result.exit_code == 1


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
def test_each_clean_fixture_yields_no_issue(rule_id: str) -> None:
    result = _check(rule_id, _fixture("clean", rule_id))
    assert result.issues == ()
    assert result.exit_code == 0


def test_fix_only_repository_admits_a_check_wiring_task() -> None:
    text = (FIXTURES / "mutation_fix_only_permitted.txt").read_text("utf-8")
    assert _check("task_in_frozen_repository", text).issues == ()


def test_the_bindings_falsifier_of_the_ticket_is_a_replay_only_finding() -> None:
    result = _check(
        "replay_only_bindings_falsifier",
        _fixture("violation", "replay_only_bindings_falsifier"),
    )
    assert "recorded transcript" in result.issues[0].message


def test_one_issue_per_task_in_a_plan_with_several_tasks() -> None:
    bad = _fixture("violation", "missing_configuration_criterion")
    clean = _fixture("clean", "missing_configuration_criterion")
    two = (
        bad.replace("T9.1", "T9.2") + "\n" + bad + "\n" + clean.replace("T9.1", "T9.3")
    )
    result = _check("missing_configuration_criterion", two)
    assert result.task_count == 3
    assert [i.context["subject"] for i in result.issues if i.context] == [
        "T9.2",
        "T9.1",
    ]


def test_a_disabled_rule_row_fails_its_fixture() -> None:
    for rule_id in sorted(RULE_IDS):

        def disable(rules: dict[str, dict[str, Any]], rule_id: str = rule_id) -> None:
            rules[rule_id]["enabled"] = False

        result = _check(
            rule_id, _fixture("violation", rule_id), _contract_with(disable)
        )
        assert result.issues == (), rule_id


def test_committed_contract_holds_every_rule() -> None:
    contract = _contract()
    assert contract.validator_id == "task_criteria"
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS


def _mutations(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [[], [*value, "(?!)"]]
    return ["(?!)", "(?s).+"]


def test_every_parameter_of_every_rule_row_changes_a_verdict() -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    baseline = _all_verdicts(_contract())
    unmoved: list[str] = []
    for rule in data["rules"]:
        for key in rule["parameters"]:
            changed = False
            for replacement in _mutations(rule["parameters"][key]):

                def mutate(
                    rules: dict[str, dict[str, Any]],
                    rule_id: str = rule["rule_id"],
                    key: str = key,
                    replacement: Any = replacement,
                ) -> None:
                    rules[rule_id]["parameters"][key] = replacement

                if _all_verdicts(_contract_with(mutate)) != baseline:
                    changed = True
                    break
            if not changed:
                unmoved.append(f"{rule['rule_id']}.{key}")
    assert unmoved == []


def test_invalid_contracts_fail_to_load_rather_than_pass() -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    clean = _fixture("clean", "missing_configuration_criterion")
    for rule in data["rules"]:
        for key in rule["parameters"]:

            def drop(
                rules: dict[str, dict[str, Any]],
                rule_id: str = rule["rule_id"],
                key: str = key,
            ) -> None:
                del rules[rule_id]["parameters"][key]

            with pytest.raises(ModelOnexError, match=rule["rule_id"]):
                _check(rule["rule_id"], clean, _contract_with(drop))

    def drop_rule(rules: dict[str, dict[str, Any]]) -> None:
        del rules["rule_block_incomplete"]

    with pytest.raises(ModelOnexError, match="rule_block_incomplete"):
        _check("rule_block_incomplete", clean, _contract_with(drop_rule))

    def bad_regex(rules: dict[str, dict[str, Any]]) -> None:
        rules["missing_bindings_criterion"]["parameters"]["bindings_pattern"] = "("

    with pytest.raises(ModelOnexError, match="bindings_pattern"):
        _check("missing_bindings_criterion", clean, _contract_with(bad_regex))


def test_checker_reads_no_file_while_open_and_path_reads_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract()
    cases = [(rule_id, _fixture("violation", rule_id)) for rule_id in sorted(RULE_IDS)]

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open", "exists", "is_file", "iterdir"):
        monkeypatch.setattr(Path, name, refuse)
    for rule_id, text in cases:
        assert [i.code for i in _check(rule_id, text, contract).issues] == [rule_id]


def test_checker_module_is_pure_and_holds_no_rule_table() -> None:
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported & {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "time",
        "datetime",
        "random",
        "urllib",
        "logging",
        "yaml",
    }
    assigned = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign | ast.AnnAssign)
        and not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
    ]
    assert assigned == []


@pytest.mark.parametrize(
    "relative_path",
    [
        "validation/checker_task_criteria.py",
        "validation/validator_task_criteria.py",
        "models/task_criteria/__init__.py",
        "models/task_criteria/model_task_criteria_check_input.py",
        "models/task_criteria/model_task_criteria_check_result.py",
        "models/task_criteria/model_task_criteria_rule_row.py",
        "models/task_criteria/model_task_criteria_rules.py",
    ],
)
def test_production_source_has_no_runtime_literals(relative_path: str) -> None:
    """Scan the actual source; absent source must not count as a clean scan."""
    package_root = Path(validator_base.__file__).parent.parent
    path = package_root / relative_path
    source = path.read_text(encoding="utf-8")
    repo_path = f"src/omnibase_core/{relative_path}"
    policy_path = Path(model_config.__file__).with_name("policy.yaml")
    policy = ModelHardcodedModelConfigPolicy.model_validate(
        yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    )

    assert scan_source("omnibase_core", repo_path, source) == []
    assert model_config.scan(repo_path, source, policy) == []
    assert not ValidatorHardcodedTopics().validate_file(path).issues
    assert not ValidatorCheckerRuleData().validate_file(path).issues
    assert contract_config_compliance.validate_file(path) == []


class _SpyContainer:
    """Records every type resolved through ``get_service`` and delegates to a container."""

    def __init__(self, inner: ModelONEXContainer) -> None:
        self._inner = inner
        self.resolved: list[type] = []

    def get_service(
        self, protocol_type: type, service_name: str | None = None
    ) -> object:
        self.resolved.append(protocol_type)
        return self._inner.get_service(protocol_type, service_name)


def test_runtime_resolves_the_writer_and_the_bus_from_the_container(
    tmp_path: Path,
) -> None:
    plans = tmp_path / "beta" / "plans"
    plans.mkdir(parents=True)
    plan = plans / "planted.md"
    plan.write_text(_fixture("violation", "missing_configuration_criterion"), "utf-8")

    composed = build_validator_container()
    bus = composed.get_service(ModelValidatorRuntimeBus)
    bus_container = ModelONEXContainer(enable_service_registry=True)
    writer_container = ModelONEXContainer(enable_service_registry=True)
    handler = HandlerValidatorRuntimeOverlay()
    bus_spy = _SpyContainer(bus_container)

    async def _compose() -> None:
        await bus_container.service_registry.register_instance(
            ModelValidatorRuntimeBus, bus
        )
        await writer_container.service_registry.register_instance(
            interface=NodeValidationReportWriteEffect,
            instance=NodeValidationReportPublishEffect(
                cast(ModelONEXContainer, bus_spy), handler.settings().run_topic
            ),
        )

    asyncio.run(_compose())
    writer_spy = _SpyContainer(writer_container)
    profile = handler.load(handler.default_overlay_path()).profile

    result = run_validator(
        cast(ModelONEXContainer, writer_spy),
        ValidatorTaskCriteria(),
        [plan],
        str(tmp_path / "report.json"),
        profile,
        "example-repository",
    )

    assert not result.is_valid
    assert {issue.code for issue in result.issues} >= {
        "missing_configuration_criterion"
    }
    assert writer_spy.resolved == [NodeValidationReportWriteEffect]
    assert bus_spy.resolved == [ModelValidatorRuntimeBus]


def test_file_validator_reports_issues_at_the_file(tmp_path: Path) -> None:
    plans = tmp_path / "beta" / "plans"
    plans.mkdir(parents=True)
    good = plans / "good.md"
    good.write_text(_fixture("clean", "missing_configuration_criterion"), "utf-8")
    bad = plans / "bad.md"
    bad.write_text(_fixture("violation", "missing_configuration_criterion"), "utf-8")
    validator = ValidatorTaskCriteria()
    assert validator.validate_file(good).is_valid
    result = validator.validate_file(bad)
    assert {issue.file_path for issue in result.issues} == {bad}
    assert {issue.code for issue in result.issues} == {
        "missing_configuration_criterion"
    }


def test_section_c_tasks_of_the_validators_plan_are_listed_by_rule_id() -> None:
    """The plan's own Phase 0 tasks (a verbatim excerpt) carry no D.5 criteria yet."""
    text = (FIXTURES / "plan_section_c_excerpt.txt").read_text("utf-8")
    result = check_task_criteria(
        ModelTaskCriteriaCheckInput(
            source_name="beta/plans/validators-to-core.md",
            text=text,
            contract=_contract(),
        )
    )
    reported = {(i.context or {})["subject"]: set() for i in result.issues}
    for issue in result.issues:
        reported[(issue.context or {})["subject"]].add(issue.code)
    assert set(reported) == {"T0.1", "T0.2"}
    for codes in reported.values():
        assert {
            "missing_configuration_criterion",
            "missing_bindings_criterion",
        } <= codes
