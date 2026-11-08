# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A contract falsifier that names a test path with no tests is refused (OMN-23185).

The rule row ``falsifier_test_path`` of ``task_criteria.validation.yaml`` is judged against a
checkout on disk by ``ValidatorTaskCriteria``. The offender corpus is omnimarket contract
OMN-22958 as it stood at dev 566d7ead09: its criteria run pytest on a source directory that
holds no test file. The control is a contract whose falsifier names an existing tests path.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_task_criteria import baseline_entry
from omnibase_core.validation.validator_task_criteria import ValidatorTaskCriteria

pytestmark = pytest.mark.unit

RULE = "falsifier_test_path"
FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "validation"
    / "task_criteria"
    / "falsifier_test_path"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "task_criteria.validation.yaml"
)
SOURCE_DIR = "src/omnimarket/nodes/node_dev_deploy_reading_compute"
TESTS_DIR = "tests/nodes/node_dev_deploy_reading_compute"
CONTROL = """\
schema_version: 1.0.0
ticket_id: OMN-99001
requirements:
- id: req-control
  acceptance:
  - id: AC1
    statement: 'AC1: the reading is NOT WORKING -- falsifier: uv run pytest tests/nodes/node_dev_deploy_reading_compute -q -k receipt'
"""


def _contract_with(
    mutate: Callable[[dict[str, Any]], None],
) -> ModelValidatorSubcontract:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: copy.deepcopy(rule) for rule in data["rules"]}
    mutate(rules[RULE])
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def _without_baseline(rule: dict[str, Any]) -> None:
    rule["parameters"]["baseline_offenders"] = []


def _without_rule_row(rule: dict[str, Any]) -> None:
    rule["enabled"] = False


def _checkout(tmp_path: Path, contract_name: str, contract_text: str) -> Path:
    """A checkout named like the repository: the source directory holds no test file."""
    root = tmp_path / "omnimarket"
    (root / "contracts").mkdir(parents=True)
    (root / "contracts" / contract_name).write_text(contract_text, encoding="utf-8")
    (root / SOURCE_DIR).mkdir(parents=True)
    (root / SOURCE_DIR / "node.py").write_text("X = 1\n", encoding="utf-8")
    (root / TESTS_DIR).mkdir(parents=True)
    (root / TESTS_DIR / "test_chain.py").write_text(
        "def test_x() -> None: ...\n", encoding="utf-8"
    )
    return root


def _findings(
    root: Path, contract_name: str, contract: ModelValidatorSubcontract | None = None
) -> list[str]:
    validator = ValidatorTaskCriteria(contract, root=root)
    issues = validator._validate_file(
        root / "contracts" / contract_name, validator.contract
    )
    return [issue.message for issue in issues if issue.code == RULE]


def _offender_case_is_red(tmp_path: Path, contract: ModelValidatorSubcontract) -> None:
    """The offender assertion of AC1: raises AssertionError when the rule admits it."""
    corpus = (FIXTURES / "OMN-22958.yaml").read_text("utf-8")
    root = _checkout(tmp_path, "OMN-22958.yaml", corpus)
    messages = _findings(root, "OMN-22958.yaml", contract)
    assert len(messages) == 1, messages
    assert all(SOURCE_DIR in message for message in messages)
    assert all("holds no test file" in message for message in messages)


def _control_case_is_green(tmp_path: Path, contract: ModelValidatorSubcontract) -> None:
    root = _checkout(tmp_path, "OMN-99001.yaml", CONTROL)
    assert _findings(root, "OMN-99001.yaml", contract) == []


def test_omn22958_as_it_stood_is_refused_when_not_in_the_baseline(
    tmp_path: Path,
) -> None:
    _offender_case_is_red(tmp_path, _contract_with(_without_baseline))


def test_omn22958_is_admitted_while_it_stands_in_the_baseline(tmp_path: Path) -> None:
    corpus = (FIXTURES / "OMN-22958.yaml").read_text("utf-8")
    root = _checkout(tmp_path, "OMN-22958.yaml", corpus)
    assert _findings(root, "OMN-22958.yaml") == []


def test_a_new_contract_with_the_same_offending_path_is_refused(tmp_path: Path) -> None:
    corpus = (FIXTURES / "OMN-22958.yaml").read_text("utf-8")
    root = _checkout(tmp_path, "OMN-99002.yaml", corpus)
    assert len(_findings(root, "OMN-99002.yaml")) == 1


def test_control_naming_an_existing_tests_path_is_admitted(tmp_path: Path) -> None:
    _control_case_is_green(tmp_path, _contract_with(_without_baseline))


def test_the_offender_case_goes_red_when_the_rule_row_is_removed(
    tmp_path: Path,
) -> None:
    removed = _contract_with(_without_rule_row)
    _control_case_is_green(tmp_path / "control", removed)
    with pytest.raises(AssertionError):
        _offender_case_is_red(tmp_path / "offender", removed)


def test_a_missing_path_is_refused_as_absent(tmp_path: Path) -> None:
    text = CONTROL.replace(TESTS_DIR, "tests/nodes/node_missing")
    root = _checkout(tmp_path, "OMN-99003.yaml", text)
    [message] = _findings(root, "OMN-99003.yaml")
    assert "tests/nodes/node_missing" in message
    assert "does not exist" in message


def test_the_validator_reads_the_committed_baseline_as_data() -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    [rule] = [r for r in data["rules"] if r["rule_id"] == RULE]
    entries = rule["parameters"]["baseline_offenders"]
    assert entries == sorted(set(entries))
    assert baseline_entry("contracts/OMN-22958.yaml", SOURCE_DIR) in entries


def test_the_baseline_may_only_shrink() -> None:
    ceiling = json.loads((FIXTURES / "baseline_ceiling.json").read_text("utf-8"))
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    [rule] = [r for r in data["rules"] if r["rule_id"] == RULE]
    grown = set(rule["parameters"]["baseline_offenders"]) - set(ceiling["entries"])
    assert grown == set()
