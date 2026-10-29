# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""AST host list and per-kind baseline coverage (OMN-21503)."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums import EnumSeverity
from omnibase_core.handlers import handler_hardcoded_value_kinds_cli as kinds
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics

pytestmark = pytest.mark.unit
RULE = "hardcoded_host_list"


def validator(**parameters: object) -> ValidatorHardcodedTopics:
    default = ValidatorHardcodedTopics().contract
    data = default.model_dump()
    data["exclude_patterns"] = []
    data["rules"] = [
        {
            "rule_id": RULE,
            "description": "fixture",
            "parameters": {
                "element_pattern": r"(?:[a-z0-9-]+\.)+[a-z]+|broker-[0-9]+:[0-9]+",
                "min_elements": 2,
                "baseline_path": "",
                **parameters,
            },
        }
    ]
    return ValidatorHardcodedTopics(contract=type(default).model_validate(data))


@pytest.mark.parametrize(
    "literal",
    [
        '["host.example.internal", "broker-1:9092"]',
        '("host.example.internal", "broker-1:9092")',
        '{"host.example.internal", "broker-1:9092"}',
        'frozenset(["host.example.internal", "broker-1:9092"])',
    ],
)
def test_literal_kinds(tmp_path: Path, literal: str) -> None:
    path = tmp_path / "source.py"
    path.write_text(f"HOSTS = {literal}\n")
    issues = validator().validate_file(path).issues
    assert len(issues) == 1
    assert issues[0].code == RULE
    assert issues[0].line_number == 1


@pytest.mark.parametrize(
    "text",
    [
        'HOSTS = ["host.example.internal"]',
        'HOSTS = ["host.example.internal", "ordinary"]',
        '# ["host.example.internal", "broker-1:9092"]',
        'HOSTS = ["host.example.internal", "broker-1:9092"] # onex-topic-allow: fixture',
        "HOSTS = [host for host in values]",
    ],
)
def test_nonmatches_and_suppression(tmp_path: Path, text: str) -> None:
    path = tmp_path / "source.py"
    path.write_text(text)
    assert validator().validate_file(path).is_valid


def test_parameters_enabled_and_severity(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_text('HOSTS = ["custom", "custom"]\n')
    v = validator(element_pattern="custom", min_elements=2)
    assert len(v.validate_file(path).issues) == 1
    data = v.contract.model_dump()
    data["rules"][0]["severity"] = "warning"
    warning = ValidatorHardcodedTopics(contract=type(v.contract).model_validate(data))
    assert warning.validate_file(path).issues[0].severity == EnumSeverity.WARNING
    data["rules"][0]["enabled"] = False
    assert (
        ValidatorHardcodedTopics(contract=type(v.contract).model_validate(data))
        .validate_file(path)
        .is_valid
    )
    assert (
        validator(element_pattern="custom", min_elements=3).validate_file(path).is_valid
    )
    yaml_path = tmp_path / "source.yaml"
    yaml_path.write_text(path.read_text())
    assert v.validate_file(yaml_path).is_valid


def test_cli_baseline_multiset_and_growth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract = Path("contract.yaml")
    contract.write_text(
        yaml.safe_dump({"validation": validator().contract.model_dump(mode="json")})
    )

    def run(arguments: list[str]) -> int:
        return kinds.main(
            ["--kind", "host_list", "--contract", str(contract), *arguments]
        )

    path = Path("source.py")
    line = 'HOSTS = ["host.example.internal", "broker-1:9092"]'
    path.write_text(line + "\n")
    fingerprint = f"{RULE}|source.py|{hashlib.sha1(line.encode()).hexdigest()}"
    baseline = Path("baseline.json")
    baseline.write_text(json.dumps({"entries": [fingerprint]}))
    previous = Path("previous.json")
    previous.write_text('{"entries": []}')
    assert run([str(path)]) == 1
    assert run([str(path), "--baseline", str(baseline)]) == 0
    assert (
        run(
            [
                str(path),
                "--baseline",
                str(baseline),
                "--previous-baseline",
                str(previous),
            ]
        )
        == 1
    )
    path.write_text((line + "\n") * 2)
    assert run([str(path), "--baseline", str(baseline)]) == 1


def test_contract_default_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = Path("source.py")
    line = 'HOSTS = ["host.example.internal", "broker-1:9092"]'
    path.write_text(line + "\n")
    baseline = Path("base.json")
    baseline.write_text(
        json.dumps(
            {"entries": [f"{RULE}|source.py|{hashlib.sha1(line.encode()).hexdigest()}"]}
        )
    )
    contract = Path("contract.yaml")
    contract.write_text(
        yaml.safe_dump(
            {
                "validation": validator(
                    baseline_path=str(baseline)
                ).contract.model_dump(mode="json")
            }
        )
    )
    assert (
        kinds.main(["--kind", "host_list", str(path), "--contract", str(contract)]) == 0
    )


def test_multiline_frozenset_reports_outer_literal_once(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_text(
        'HOSTS = frozenset(\n    ["host.example.internal", "broker-1:9092"]\n)\n'
    )
    issues = validator().validate_file(path).issues
    assert [i.line_number for i in issues] == [1]


def test_topic_registry_is_not_a_host_list_exemption(tmp_path: Path) -> None:
    path = tmp_path / "constants.py"
    path.write_text('HOSTS = ["host.example.internal", "broker-1:9092"]\n')
    assert not validator().validate_file(path).is_valid


@pytest.mark.parametrize("document", ['{"entries": [12]}', "{}", "not json"])
def test_invalid_baseline_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, document: str
) -> None:
    monkeypatch.chdir(tmp_path)
    baseline = Path("baseline.json")
    baseline.write_text(document)
    assert kinds.main(["--kind", "host_list", "--baseline", str(baseline)]) == 1
