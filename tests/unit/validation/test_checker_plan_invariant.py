# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pure plan-invariant checker and generic validator (OMN-21559, task T0.7).

Every rule has a planted violation fixture (exactly one issue with its rule id) and a clean
fixture (no issue). All rule data lives in ``validation/contracts/plan_invariant.validation.yaml``;
the table-driven mutation test changes every ``parameters`` key of every rule row in turn
and asserts the verdict changes.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import copy
import json
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
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_settings import (
    ModelValidatorRuntimeSettings,
)
from omnibase_core.models.plan_invariant.model_plan_invariant_check_input import (
    ModelPlanInvariantCheckInput,
)
from omnibase_core.models.plan_invariant.model_plan_invariant_check_result import (
    ModelPlanInvariantCheckResult,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validation_report_publish import (
    _EMITTER_TOKEN,
    _RUN_EVENTS_TOKEN,
    _WRITER_TOKEN,
    NodeValidationReportPublishEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
    run_validator,
)
from omnibase_core.validation import checker_plan_invariant as checker_module
from omnibase_core.validation import checker_task_criteria, validator_base
from omnibase_core.validation.checker_plan_invariant import check_plan_invariant
from omnibase_core.validation.hardcoded_model_config import handler as model_config
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_plan_invariant import ValidatorPlanInvariant
from omnibase_core.validation.validator_task_criteria import ValidatorTaskCriteria
from omnibase_core.validation.validator_url_authority import scan_source
from omnibase_core.validators import contract_config_compliance

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "plan_invariant"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "plan_invariant.validation.yaml"
)
TASK_CRITERIA_CONTRACT = ValidatorTaskCriteria().contract

RULE_IDS = {
    "task_without_falsifiable_criterion",
    "task_names_literal_value",
    "invariant_without_enforcing_task",
}


def _source(rule_id: str, name: str = "x") -> str:
    return f"beta/plans/{name}.md"


def _fixture(kind: str, rule_id: str) -> str:
    suffix = "txt"
    return (FIXTURES / f"{kind}_{rule_id}.{suffix}").read_text("utf-8")


def _contract() -> ModelValidatorSubcontract:
    return ValidatorPlanInvariant().contract


def _check(
    rule_id: str, text: str, contract: ModelValidatorSubcontract | None = None
) -> ModelPlanInvariantCheckResult:
    return check_plan_invariant(
        ModelPlanInvariantCheckInput(
            source_name=_source(rule_id),
            text=text,
            task_criteria_contract=TASK_CRITERIA_CONTRACT,
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


def test_other_kind_violation_fixture_has_exactly_one_issue() -> None:
    result = _check(
        "task_names_literal_value",
        _fixture("violation", "task_names_literal_value_other"),
    )
    assert [issue.code for issue in result.issues] == ["task_names_literal_value"]
    assert result.issues[0].context["kind"] == "topic"


def test_planted_plan_is_refused_by_rule_id_and_clean_plan_passes() -> None:
    result = _check("plan", (FIXTURES / "planted_plan.txt").read_text("utf-8"))
    assert [issue.code for issue in result.issues] == [
        "task_without_falsifiable_criterion",
        "task_names_literal_value",
        "task_names_literal_value",
        "invariant_without_enforcing_task",
    ]
    assert [
        issue.context["kind"]
        for issue in result.issues
        if issue.code == "task_names_literal_value"
    ] == ["host", "topic"]
    assert result.task_count == 2
    assert result.invariant_count == 1
    assert result.exit_code == 1
    clean = _check("plan", (FIXTURES / "clean_plan.txt").read_text("utf-8"))
    assert clean.issues == ()
    assert clean.exit_code == 0
    assert clean.task_count == 1
    assert clean.invariant_count == 2


@pytest.mark.parametrize(
    "fixture",
    [
        "planted_plan",
        *[f"violation_{rule}" for rule in sorted(RULE_IDS)],
        "violation_task_names_literal_value_other",
        "clean_plan",
    ],
)
def test_severity_is_error_and_cli_refuses_planted_fixtures(
    fixture: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = _contract()
    assert all(
        rule.enabled and rule.severity.value == "error" for rule in contract.rules
    )
    assert contract.fail_on_error
    assert not contract.fail_on_warning
    assert contract.max_violations == 0
    plans = tmp_path / "beta" / "plans"
    plans.mkdir(parents=True)
    plan = plans / "example.md"
    plan.write_text((FIXTURES / f"{fixture}.txt").read_text("utf-8"), "utf-8")
    monkeypatch.chdir(tmp_path)
    report = tmp_path / "report.json"
    assert main(
        ValidatorPlanInvariant,
        [str(tmp_path), "--report-json", str(report)],
        build_validator_container,
    ) == (0 if fixture == "clean_plan" else 1)
    written = json.loads(report.read_text("utf-8"))
    assert written["overall_status"] == ("PASS" if fixture == "clean_plan" else "FAIL")


@pytest.mark.parametrize(
    ("entry", "literal"),
    [
        (r"queue::\bqueue-[a-z0-9]+\b", "queue-primary"),
        (r"region::\bregion-[a-z]+\b", "region-east"),
    ],
)
def test_literal_kinds_accept_an_eighth_kind_without_code_changes(
    entry: str, literal: str
) -> None:
    text = _fixture("clean", "task_names_literal_value").replace(
        "Example checker", f"Use {literal}"
    )
    before = Path(checker_module.__file__).read_text("utf-8")
    assert _check("task_names_literal_value", text).issues == ()

    def append(rules: dict[str, dict[str, Any]]) -> None:
        rules["task_names_literal_value"]["parameters"]["literal_kinds"].append(entry)

    result = _check("task_names_literal_value", text, _contract_with(append))
    assert [issue.code for issue in result.issues] == ["task_names_literal_value"]
    assert result.issues[0].context["kind"] == entry.partition("::")[0]
    assert Path(checker_module.__file__).read_text("utf-8") == before


@pytest.mark.parametrize(
    ("literal", "kinds"),
    [
        (literal, set(kinds.split(",")))
        for line in (FIXTURES / "literal_kinds_cases.txt")
        .read_text("utf-8")
        .splitlines()
        for literal, kinds in [line.split("\t")]
    ],
)
def test_literal_kinds_are_detected_once_per_task(
    literal: str, kinds: set[str]
) -> None:
    text = _fixture("clean", "task_names_literal_value").replace(
        "Example checker", f"Use {literal} and {literal}"
    )
    result = _check("task_names_literal_value", text)
    assert {issue.context["kind"] for issue in result.issues} == kinds
    assert len(result.issues) == len(kinds)


def test_task_with_no_criterion_bullets_is_refused() -> None:
    result = _check(
        "task_without_falsifiable_criterion",
        "**T1 Empty task.**\n- Notes: implement it.\n",
    )
    assert [issue.code for issue in result.issues] == [
        "task_without_falsifiable_criterion"
    ]


def test_one_falsifiable_criterion_is_enough_and_relative_commands_are_clean() -> None:
    text = "**T1 Check tests/unit/x.py.**\n- Acceptance: finished\n- AC1: falsifier: `uv run pytest tests/unit/x.py` passes\n"
    assert _check("plan", text).issues == ()


def test_invariants_are_removed_before_task_splitting_and_enforcement_uses_ids() -> (
    None
):
    task = _fixture("clean", "task_names_literal_value")
    text = (
        task
        + "## Invariants\n- INV-012: "
        + _fixture("violation", "task_names_literal_value")
        + "- Enforces: INV-012\n"
    )
    result = _check("plan", text)
    assert [(issue.code, issue.context["subject"]) for issue in result.issues] == [
        ("invariant_without_enforcing_task", "INV-012")
    ]
    assert result.task_count == 1
    assert result.invariant_count == 1
    text = (
        "### Invariants\n- INV-012: Proof.\n- INV-013: Configuration.\n#### Details\n- INV-014: Bindings.\n## Tasks\n"
        + task
        + "- Enforces: INV-012, INV-013, INV-014\n"
    )
    assert _check("plan", text).issues == ()
    assert _check("plan", text).invariant_count == 3
    assert _check("plan", text.replace("- Enforces:", "- Notes:")).invariant_count == 3
    assert len(_check("plan", text.replace("- Enforces:", "- Notes:")).issues) == 3
    result = _check("plan", text.replace("INV-014\n", "INV-0140\n"))
    assert [issue.context["subject"] for issue in result.issues] == ["INV-014"]


def test_calls_the_k12_predicate(monkeypatch: pytest.MonkeyPatch) -> None:
    text = _fixture("violation", "task_without_falsifiable_criterion")
    assert _check("plan", text).exit_code == 1
    monkeypatch.setattr(checker_module, "criterion_has_falsifier", lambda *_: True)
    assert _check("plan", text).issues == ()


def test_calls_the_k12_predicate_without_copying_its_pattern_strings() -> None:
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    patterns = {
        value
        for rule in TASK_CRITERIA_CONTRACT.rules
        for key, value in (rule.parameters or {}).items()
        if key
        in {
            "task_heading_pattern",
            "criterion_pattern",
            "falsifier_pattern",
            "action_pattern",
            "observable_pattern",
        }
    }
    assert not strings & patterns


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
    assert contract.validator_id == "plan_invariant"
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS


def _mutations(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [[], [*value, r"queue::\bqueue-[a-z0-9]+\b"]]
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
    clean = _fixture("clean", "task_without_falsifiable_criterion")
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
        del rules["invariant_without_enforcing_task"]

    with pytest.raises(ModelOnexError, match="invariant_without_enforcing_task"):
        _check("invariant_without_enforcing_task", clean, _contract_with(drop_rule))

    def bad_regex(rules: dict[str, dict[str, Any]]) -> None:
        rules["invariant_without_enforcing_task"]["parameters"]["id_pattern"] = "("

    with pytest.raises(ModelOnexError, match="id_pattern"):
        _check("invariant_without_enforcing_task", clean, _contract_with(bad_regex))


@pytest.mark.parametrize(
    "value", [["host"], ["host::("], ["::valid"], ["host::"], [42], "not-a-list"]
)
def test_invalid_contracts_reject_literal_kinds(value: Any) -> None:
    # Exercise the rules view's own validation even when facts bypass Pydantic parsing.
    contract = _contract()
    rows = [
        row.model_copy(
            update={"parameters": {**(row.parameters or {}), "literal_kinds": value}}
        )
        if row.rule_id == "task_names_literal_value"
        else row
        for row in contract.rules
    ]
    with pytest.raises(
        ModelOnexError, match=r"task_names_literal_value.*literal_kinds"
    ):
        _check(
            "plan",
            _fixture("clean", "task_names_literal_value"),
            contract.model_copy(update={"rules": rows}),
        )


def test_invalid_contracts_validate_disabled_rows_too() -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        rules["task_names_literal_value"]["enabled"] = False
        del rules["task_names_literal_value"]["parameters"]["literal_kinds"]

    with pytest.raises(
        ModelOnexError, match=r"task_names_literal_value.*literal_kinds"
    ):
        _check(
            "plan",
            _fixture("clean", "task_names_literal_value"),
            _contract_with(mutate),
        )


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


@pytest.mark.parametrize("module", [checker_module, checker_task_criteria])
def test_checker_module_is_pure_and_holds_no_rule_table(module: Any) -> None:
    tree = ast.parse(Path(module.__file__).read_text("utf-8"))
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
        "validation/checker_plan_invariant.py",
        "validation/validator_plan_invariant.py",
        "models/plan_invariant/__init__.py",
        "models/plan_invariant/model_plan_invariant_check_input.py",
        "models/plan_invariant/model_plan_invariant_check_result.py",
        "models/plan_invariant/model_plan_invariant_rules.py",
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
    plan.write_text(
        _fixture("violation", "task_without_falsifiable_criterion"), "utf-8"
    )

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
        for token in (
            _WRITER_TOKEN,
            _RUN_EVENTS_TOKEN,
            _EMITTER_TOKEN,
            ModelValidatorRuntimeSettings,
        ):
            await bus_container.service_registry.register_instance(
                token, composed.get_service(token)
            )
        await writer_container.service_registry.register_instance(
            interface=NodeValidationReportWriteEffect,
            instance=NodeValidationReportPublishEffect(
                cast(ModelONEXContainer, bus_spy)
            ),
        )

    asyncio.run(_compose())
    writer_spy = _SpyContainer(writer_container)
    profile = handler.load(handler.default_overlay_path()).profile

    result = run_validator(
        cast(ModelONEXContainer, writer_spy),
        ValidatorPlanInvariant(),
        [plan],
        str(tmp_path / "report.json"),
        profile,
        "example-repository",
    )

    assert not result.is_valid
    assert {issue.code for issue in result.issues} >= {
        "task_without_falsifiable_criterion"
    }
    assert writer_spy.resolved == [NodeValidationReportWriteEffect]
    assert bus_spy.resolved == [
        _WRITER_TOKEN,
        _RUN_EVENTS_TOKEN,
        _EMITTER_TOKEN,
        ModelValidatorRuntimeSettings,
        ModelValidatorRuntimeBus,
    ]


def test_file_validator_reports_issues_at_the_file(tmp_path: Path) -> None:
    plans = tmp_path / "beta" / "plans"
    plans.mkdir(parents=True)
    good = plans / "good.md"
    good.write_text(_fixture("clean", "task_without_falsifiable_criterion"), "utf-8")
    bad = plans / "bad.md"
    bad.write_text(_fixture("violation", "task_without_falsifiable_criterion"), "utf-8")
    validator = ValidatorPlanInvariant()
    assert validator.validate_file(good).is_valid
    result = validator.validate_file(bad)
    assert {issue.file_path for issue in result.issues} == {bad}
    assert {issue.code for issue in result.issues} == {
        "task_without_falsifiable_criterion"
    }
