# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section 4 refusal fixtures for the error-rule table (OMN-19998)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.error_rule_table.model_error_action_contract import (
    ModelErrorActionContract,
)
from omnibase_core.models.error_rule_table.model_error_rule_check_input import (
    ModelErrorRuleCheckInput,
)
from omnibase_core.models.error_rule_table.model_error_rule_measurement import (
    ModelErrorRuleMeasurement,
)
from omnibase_core.validation.checker_error_rule_table import (
    action_contract_digest,
    check_error_rule_table,
)
from omnibase_core.validation.validator_error_rule_table import ValidatorErrorRuleTable

pytestmark = pytest.mark.unit


def row() -> dict[str, Any]:
    return {
        "id": "known-branch-error",
        "class_keys": ["install.branch-required"],
        "key_version": 1,
        "trigger": {"kind": "text"},
        "break_class": "A",
        "sources": ["ticket:OMN-19998"],
        "applies_if": {
            "host_roles": ["lab"],
            "repositories": ["sample"],
            "ticket_states": ["In Progress"],
        },
        "action": {
            "kind": "none",
            "reason": "Observe until the registered installer is available",
        },
        "subject_kind": "ticket",
        "budget": 1,
        "lease_s": 60,
        "lane_kinds": ["ticket"],
        "mode": "shadow",
        "fixtures": {"positive": ["record-hit"], "negative": ["record-miss"]},
        "removal_ticket": "OMN-19998",
    }


def context(**changes: Any) -> ModelErrorRuleCheckInput:
    return ModelErrorRuleCheckInput(
        document={},
        contract=ValidatorErrorRuleTable().contract,
        resolved_sources=frozenset({"ticket:OMN-19998"}),
        registered_state_checks=frozenset({"failure-gone"}),
        **changes,
    )


def validate(tmp_path: Path, rows: list[dict[str, Any]], **changes: Any) -> Any:
    target = tmp_path / "error_rules.yaml"
    target.write_text(yaml.safe_dump({"error_rules": rows}), encoding="utf-8")
    return ValidatorErrorRuleTable(context=context(**changes)).validate(target)


def test_error_rule_table_refuses_release_action(tmp_path: Path) -> None:
    bad = row()
    bad["action"] = {"kind": "release", "contract": "release", "digest": "0" * 64}
    result = validate(tmp_path, [bad])
    assert not result.is_valid, "a row naming a release action was accepted"
    assert "action" in " ".join(issue.message for issue in result.issues)


@pytest.mark.parametrize(
    ("field", "value", "diagnostic"),
    [
        ("sources", [], "sources"),
        ("sources", ["memory:branch-rule"], "sources"),
        ("sources", ["ticket:OMN-0"], "sources"),
        ("fixtures", {"positive": ["hit"], "negative": []}, "fixtures.negative"),
        ("mode", "dispatch", "measured"),
        ("action", {"kind": "none"}, "action.reason"),
        ("read_back", {"state_check": "failure-gone", "timeout_s": 30}, "read_back"),
        (
            "trigger",
            {"kind": "state", "state_check": "unregistered"},
            "trigger.state_check",
        ),
        ("budget", 0, "budget"),
        ("lease_s", True, "lease_s"),
        (
            "action",
            {"kind": "none", "reason": "observed", "command": "ignored"},
            "action.command",
        ),
    ],
)
def test_error_rule_table_refuses_field(
    tmp_path: Path, field: str, value: Any, diagnostic: str
) -> None:
    bad = row()
    bad[field] = value
    result = validate(tmp_path, [bad])
    assert not result.is_valid
    assert diagnostic in " ".join(issue.message for issue in result.issues)


def test_error_rule_table_refuses_duplicate_class_keys_and_ids(tmp_path: Path) -> None:
    first, second = row(), row()
    second["id"] = "different-id"
    result = validate(tmp_path, [first, second])
    assert not result.is_valid
    assert any("class_keys" in issue.message for issue in result.issues)
    result = validate(tmp_path, [first, first])
    assert any(".id:" in issue.message for issue in result.issues)


def contract(node_id: str = "wait", **changes: Any) -> ModelErrorActionContract:
    raw = {
        "id": node_id,
        "node": f"node_{node_id.replace('-', '_')}_effect",
        "capabilities": ["observe"],
        "targets": ["local"],
        "scope_marker": ["dev", "stability"],
        "receivers": ["local-runtime"],
        "idempotent_by": ["class_key", "subject", "revision"],
        "calls": [],
    }
    raw.update(changes)
    return ModelErrorActionContract.model_validate(raw)


def executable(
    contracts: dict[str, ModelErrorActionContract], kind: str = "wait"
) -> dict[str, Any]:
    value = row()
    value["action"] = {
        "kind": kind,
        "contract": kind,
        "digest": action_contract_digest(kind, contracts),
    }
    value["read_back"] = {"state_check": "failure-gone", "timeout_s": 30}
    return value


@pytest.mark.parametrize(
    "kind",
    [
        "install-branch",
        "landing-intent",
        "fill-backlog-item",
        "operator-question",
        "wait",
    ],
)
def test_action_contract_closed_registry_positive(tmp_path: Path, kind: str) -> None:
    contracts = {kind: contract(kind)}
    result = validate(
        tmp_path, [executable(contracts, kind)], action_contracts=contracts
    )
    assert result.is_valid, result.issues


@pytest.mark.parametrize(
    ("changes", "diagnostic"),
    [
        ({"capabilities": ["release"]}, "capabilities"),
        ({"capabilities": ["production-target"]}, "capabilities"),
        ({"capabilities": ["check-widening"]}, "capabilities"),
        ({"capabilities": ["hook-bypass"]}, "capabilities"),
        ({"targets": ["prod"]}, "targets"),
        ({"scope_marker": ["dev"]}, "scope_marker"),
        ({"idempotent_by": [" "]}, "idempotent_by"),
    ],
)
@pytest.mark.parametrize("transitive", [False, True])
def test_action_contract_refuses_direct_and_transitive_stops(
    tmp_path: Path, changes: dict[str, Any], diagnostic: str, transitive: bool
) -> None:
    if transitive:
        contracts = {
            "wait": contract(calls=["second-node"]),
            "second-node": contract("second-node", **changes),
        }
    else:
        contracts = {"wait": contract(**changes)}
    result = validate(tmp_path, [executable(contracts)], action_contracts=contracts)
    assert not result.is_valid
    assert any(diagnostic in issue.message for issue in result.issues)


@pytest.mark.parametrize(
    "field",
    ["targets", "scope_marker", "receivers", "capabilities", "calls", "idempotent_by"],
)
@pytest.mark.parametrize("transitive", [False, True])
def test_action_contract_edited_after_validation_refuses_digest(
    tmp_path: Path, field: str, transitive: bool
) -> None:
    contracts = {
        "wait": contract(calls=["child"]),
        "child": contract("child"),
        "other": contract("other"),
    }
    good = executable(contracts)
    assert validate(tmp_path, [good], action_contracts=contracts).is_valid
    node_id = "child" if transitive else "wait"
    mutated = dict(contracts)
    replacement = {
        "targets": ("dev",),
        "scope_marker": ("stability", "dev"),
        "receivers": ("new-receiver",),
        "capabilities": ("observe", "notify"),
        "calls": ("other",),
        "idempotent_by": ("subject", "revision"),
    }[field]
    mutated[node_id] = contracts[node_id].model_copy(update={field: replacement})
    result = validate(tmp_path, [good], action_contracts=mutated)
    assert not result.is_valid
    assert any("action.digest" in issue.message for issue in result.issues)


def test_action_contract_missing_cycle_and_natural_key(tmp_path: Path) -> None:
    contracts = {"wait": contract(calls=["child"]), "child": contract("child")}
    good = executable(contracts)
    del contracts["child"]
    assert not validate(tmp_path, [good], action_contracts=contracts).is_valid
    contracts["child"] = contract("child", calls=["wait"])
    assert not validate(tmp_path, [good], action_contracts=contracts).is_valid
    raw = contract().model_dump()
    raw["idempotent_by"] = ()
    with pytest.raises(ValueError, match="idempotent_by"):
        ModelErrorActionContract.model_validate(raw)


def test_error_rule_table_refuses_fill_pr(tmp_path: Path) -> None:
    contracts = {"fill-backlog-item": contract("fill-backlog-item")}
    bad = executable(contracts, "fill-backlog-item")
    bad["subject_kind"] = "pr"
    result = validate(tmp_path, [bad], action_contracts=contracts)
    assert not result.is_valid
    assert any("subject_kind" in issue.message for issue in result.issues)


def test_error_rule_table_shadow_needs_source_only(tmp_path: Path) -> None:
    contracts = {"wait": contract()}
    value = executable(contracts)
    value.update(sources=[], source_state="needs-source")
    assert validate(tmp_path, [value], action_contracts=contracts).is_valid
    for mode in ("hint", "dispatch"):
        value["mode"] = mode
        result = validate(tmp_path, [value], action_contracts=contracts)
        assert not result.is_valid
        assert any("source_state" in issue.message for issue in result.issues)
    value["mode"] = "shadow"
    value["action"] = {"kind": "none", "reason": "no action"}
    value.pop("read_back")
    assert not validate(tmp_path, [value], action_contracts=contracts).is_valid


def test_error_rule_table_measurement_requires_trusted_record(tmp_path: Path) -> None:
    contracts = {"wait": contract()}
    value = executable(contracts)
    value["mode"] = "dispatch"
    value["measured"] = {
        "corpus_digest": "a" * 64,
        "hits": 5,
        "false_matches": 0,
        "interval_start": "2026-11-04T00:00:00Z",
        "interval_end": "2026-11-04T01:00:00Z",
        "written_by": "node_error_rule_measurement_compute",
    }
    assert not validate(tmp_path, [value], action_contracts=contracts).is_valid
    measurements = {
        value["id"]: ModelErrorRuleMeasurement.model_validate(value["measured"])
    }
    assert validate(
        tmp_path,
        [value],
        action_contracts=contracts,
        measurements=measurements,
        authorized_modes={value["id"]: "dispatch"},
    ).is_valid
    value["measured"]["hits"] = 6
    assert not validate(
        tmp_path, [value], action_contracts=contracts, measurements=measurements
    ).is_valid


def test_error_rule_table_none_positive_control(tmp_path: Path) -> None:
    result = validate(tmp_path, [row()])
    assert result.is_valid, result.issues


def test_error_rule_table_policy_is_data(tmp_path: Path) -> None:
    contracts = {"wait": contract(targets=["new-environment"])}
    value = executable(contracts)
    assert not validate(tmp_path, [value], action_contracts=contracts).is_valid
    base = context(action_contracts=contracts)
    rules = copy.deepcopy(base.contract)
    rules.rules[0].parameters["allowed_targets"].append("new-environment")
    request = base.model_copy(
        update={"document": {"error_rules": [value]}, "contract": rules}
    )
    assert check_error_rule_table(request) == ()


@pytest.mark.parametrize("defect", [None, "missing-reason", "missing-source"])
def test_error_rule_table_none_terminal_projection(
    tmp_path: Path, defect: str | None
) -> None:
    from omnibase_core.validation.checker_error_rule_table import none_rule_result

    value = row()
    if defect == "missing-reason":
        value["action"].pop("reason")
    if defect == "missing-source":
        value["sources"] = []
    request = context().model_copy(update={"document": {"error_rules": [value]}})
    result = validate(tmp_path, [value])
    if defect:
        assert not result.is_valid
        with pytest.raises(ModelOnexError) as caught:
            none_rule_result(request, value["id"])
        assert "action.reason" in str(caught.value) or "sources" in str(caught.value)
    else:
        assert result.is_valid
        terminal = none_rule_result(request, value["id"])
        assert terminal.message == f"NONE-RULED {value['action']['reason']}"
        assert not terminal.executable
        assert (
            terminal.claims,
            terminal.dispatches,
            terminal.asks,
            terminal.triages,
        ) == ((), (), (), ())
        with pytest.raises(ValueError):
            type(terminal).model_validate(
                {**terminal.model_dump(), "dispatches": ["wait"]}
            )


def test_error_rule_table_refuses_retired_id(tmp_path: Path) -> None:
    value = row()
    result = validate(tmp_path, [value], retired_ids=frozenset({value["id"]}))
    assert not result.is_valid
    assert any(".id:" in issue.message for issue in result.issues)


def test_error_rule_table_primary_source_can_have_memory_pointer(
    tmp_path: Path,
) -> None:
    value = row()
    value["sources"].append("memory:install-branch")
    assert validate(tmp_path, [value]).is_valid


def test_error_rule_table_refuses_self_authorized_modes(tmp_path: Path) -> None:
    value = row()
    value["mode"] = "hint"
    assert not validate(tmp_path, [value]).is_valid
    assert validate(tmp_path, [value], authorized_modes={value["id"]: "hint"}).is_valid


def test_error_rule_table_refuses_empty_or_duplicate_yaml(tmp_path: Path) -> None:
    assert not validate(tmp_path, []).is_valid
    target = tmp_path / "error_rules.yaml"
    target.write_text("error_rules: []\nerror_rules: []\n", encoding="utf-8")
    assert not ValidatorErrorRuleTable(context=context()).validate(target).is_valid


def test_action_contract_json_schema_matches_model() -> None:
    import json

    root = Path(__file__).resolve().parents[3] / "src/omnibase_core/contracts"
    schema = json.loads((root / "error_action_contract.schema.json").read_text())
    schema.pop("$schema")
    assert schema == ModelErrorActionContract.model_json_schema()


@pytest.mark.parametrize("defect", [None, "reason", "contract", "read_back", "source"])
def test_error_rule_table_none_schema_branch(defect: str | None) -> None:
    import json

    import jsonschema

    value = row()
    if defect == "reason":
        value["action"].pop("reason")
    if defect == "contract":
        value["action"]["contract"] = "wait"
    if defect == "read_back":
        value["read_back"] = {"state_check": "failure-gone", "timeout_s": 30}
    if defect == "source":
        value["sources"] = []
    root = Path(__file__).resolve().parents[3] / "src/omnibase_core/contracts"
    schema = json.loads((root / "error_rule_row.schema.json").read_text())
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(value))
    assert bool(errors) == bool(defect)


@pytest.mark.parametrize("bad", [False, True])
def test_error_rule_table_runtime_overlay_verdicts_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: bool
) -> None:
    import json
    import types

    from omnibase_core.nodes.node_validation_report_write_effect import (
        handler_validator_runtime_overlay as bindings,
    )
    from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
        HandlerValidatorRuntimeOverlay,
    )
    from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
        build_validator_container,
        main,
    )

    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        '2026-11-04T17:10:13Z | RULING | ticket=OMN-19998 | "fixture source"\n'
    )
    monkeypatch.setenv("ONEX_LEDGER_PATH", str(ledger))
    monkeypatch.delenv("ONEX_ERROR_RULE_ACTION_REGISTRY", raising=False)
    monkeypatch.delenv("ONEX_ERROR_RULE_MEASUREMENTS", raising=False)
    monkeypatch.delenv("ONEX_ERROR_RULE_AUTHORIZED_MODES", raising=False)
    value = row()
    if bad:
        value["action"] = {"kind": "release", "contract": "release", "digest": "0" * 64}
    target = tmp_path / "error_rules.yaml"
    target.write_text(yaml.safe_dump({"error_rules": [value]}))
    handler = HandlerValidatorRuntimeOverlay()
    overlays = Path(bindings.__file__).parent / "overlays"
    redpanda = handler.load(overlays / "validator_runtime.redpanda.overlay.yaml")
    module_name, _, class_name = redpanda.bus.implementation.partition(":")
    published: list[tuple[str, bytes]] = []

    class RecordingBus:
        @classmethod
        def from_bootstrap(cls, bootstrap: str) -> Any:
            assert bootstrap == "fixture-broker:9092"
            return cls()

        async def start(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def publish(self, topic: str, key: bytes | None, value: bytes) -> None:
            published.append((topic, value))

    real_import = bindings.importlib.import_module
    monkeypatch.setattr(
        bindings.importlib,
        "import_module",
        lambda name: types.SimpleNamespace(**{class_name: RecordingBus})
        if name == module_name
        else real_import(name),
    )
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fixture-broker:9092")
    reports = []
    for overlay in (
        "validator_runtime.inmemory.overlay.yaml",
        "validator_runtime.redpanda.overlay.yaml",
    ):
        report_path = tmp_path / f"{overlay}.json"
        exit_code = main(
            ValidatorErrorRuleTable,
            [
                str(target),
                "--report-json",
                str(report_path),
                "--overlay",
                str(overlays / overlay),
            ],
            build_validator_container,
        )
        assert exit_code == int(bad)
        report = json.loads(report_path.read_text())
        report["report_id"] = "<normalised>"
        report["provenance"]["generated_at"] = "<normalised>"
        reports.append(report)
    assert reports[0] == reports[1]
    assert sum(topic == handler.settings().run_topic for topic, _ in published) == 1


def test_error_rule_table_file_authorities_are_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contracts = {"wait": contract()}
    value = executable(contracts)
    target = tmp_path / "error_rules.yaml"
    target.write_text(yaml.safe_dump({"error_rules": [value]}))
    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        '2026-11-04T17:10:13Z | RULING | ticket=OMN-19998 | "fixture source"\n'
    )
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "contracts": {
                    key: node.model_dump(mode="json") for key, node in contracts.items()
                },
                "state_checks": ["failure-gone"],
            }
        )
    )
    monkeypatch.setenv("ONEX_LEDGER_PATH", str(ledger))
    monkeypatch.setenv("ONEX_ERROR_RULE_ACTION_REGISTRY", str(registry))
    monkeypatch.delenv("ONEX_ERROR_RULE_MEASUREMENTS", raising=False)
    monkeypatch.delenv("ONEX_ERROR_RULE_AUTHORIZED_MODES", raising=False)
    assert ValidatorErrorRuleTable().validate(target).is_valid
    contracts["wait"] = contract(receivers=["changed"])
    registry.write_text(
        yaml.safe_dump(
            {
                "contracts": {
                    key: node.model_dump(mode="json") for key, node in contracts.items()
                },
                "state_checks": ["failure-gone"],
            }
        )
    )
    result = ValidatorErrorRuleTable().validate(target)
    assert not result.is_valid
    assert any("action.digest" in issue.message for issue in result.issues)
    # A row cannot replace the trusted registry with one of its own.
    target.write_text(yaml.safe_dump({"error_rules": [value], "action_contracts": {}}))
    assert not ValidatorErrorRuleTable().validate(target).is_valid


def test_error_rule_table_checker_obeys_generic_ratchets() -> None:
    from omnibase_core.validation.validator_checker_rule_data import (
        ValidatorCheckerRuleData,
    )

    root = Path(__file__).resolve().parents[3]
    files = [
        root / "src/omnibase_core/validation/checker_error_rule_table.py",
        root / "src/omnibase_core/validation/validator_error_rule_table.py",
    ]
    result = ValidatorCheckerRuleData().validate(files)
    assert result.is_valid, result.issues


def test_error_rule_table_skill_overlay_root_is_validated(tmp_path: Path) -> None:
    target = tmp_path / "error_rules/overlay.yaml"
    target.parent.mkdir()
    value = row()
    value["action"] = {"kind": "release"}
    target.write_text(yaml.safe_dump({"error_rules": [value]}))
    result = ValidatorErrorRuleTable(context=context()).validate(tmp_path)
    assert not result.is_valid
    assert result.metadata is not None
    assert result.metadata.files_processed == 1


@pytest.mark.parametrize("change", ["disabled", "warning", "absent", "malformed"])
def test_error_rule_table_refuses_weakened_policy(tmp_path: Path, change: str) -> None:
    from omnibase_core.enums import EnumSeverity
    from omnibase_core.errors.model_onex_error import ModelOnexError

    policy = copy.deepcopy(ValidatorErrorRuleTable().contract)
    if change == "disabled":
        policy.rules[0] = policy.rules[0].model_copy(update={"enabled": False})
    elif change == "warning":
        policy.rules[0] = policy.rules[0].model_copy(
            update={"severity": EnumSeverity.WARNING}
        )
    elif change == "absent":
        policy = policy.model_copy(update={"rules": []})
    else:
        policy.rules[0].parameters.pop("allowed_targets")
    target = tmp_path / "error_rules.yaml"
    target.write_text(yaml.safe_dump({"error_rules": [row()]}))
    with pytest.raises(ModelOnexError, match="contract"):
        ValidatorErrorRuleTable(contract=policy).validate(target)


def test_error_rule_table_refuses_duplicate_key_across_versions(tmp_path: Path) -> None:
    first, second = row(), row()
    second.update(id="new-version", key_version=2)
    result = validate(tmp_path, [first, second])
    assert not result.is_valid
    assert any("class_keys" in issue.message for issue in result.issues)


def test_action_contract_requires_execution_binding() -> None:
    raw = contract().model_dump()
    raw.pop("node", None)
    raw.pop("lane_kind", None)
    with pytest.raises(ValueError, match=r"node|lane_kind"):
        ModelErrorActionContract.model_validate(raw)


@pytest.mark.parametrize("transitive", [False, True])
def test_action_contract_edited_node_binding_changes_digest(
    tmp_path: Path, transitive: bool
) -> None:
    contracts = {"wait": contract(calls=["child"]), "child": contract("child")}
    value = executable(contracts)
    assert validate(tmp_path, [value], action_contracts=contracts).is_valid
    selected = "child" if transitive else "wait"
    contracts[selected] = contracts[selected].model_copy(
        update={"node": "node_different_effect"}
    )
    result = validate(tmp_path, [value], action_contracts=contracts)
    assert not result.is_valid
    assert any("action.digest" in issue.message for issue in result.issues)


def test_action_contract_lane_binding_and_ambiguous_binding() -> None:
    value = contract().model_dump()
    value.update(node=None, lane_kind="ticket")
    assert ModelErrorActionContract.model_validate(value).lane_kind == "ticket"
    value["node"] = "node_wait_effect"
    with pytest.raises(ValueError, match=r"node|lane_kind"):
        ModelErrorActionContract.model_validate(value)
