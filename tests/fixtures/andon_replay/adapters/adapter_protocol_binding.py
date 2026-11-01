# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K5 ``protocol_binding``: one source or contract into the checker.

A Python source goes through ``check_protocol_binding``; a node contract goes through
``contract_setting_keys`` and ``check_setting_two_homes`` with the contract the assertion's
``comparison_file`` fact names read first, so the audited contract is the later home, as the
validator reads a list of contracts in order. No baseline is passed: the replay judges the
audited revision as it stood, with no admitted count.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_protocol_binding import (
    check_protocol_binding,
    check_setting_two_homes,
    contract_setting_keys,
)
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope

_CONTRACT_ROLE = "node_contract"
_COMPARISON_ROLE = "comparison_file"
_PYTHON_SUFFIX = ".py"


def _keys(text: str, name: str, rules: Sequence[ModelValidatorRule]) -> tuple[str, ...]:
    document = load_yaml_mapping_no_duplicates(text, source=name)
    return contract_setting_keys({str(k): v for k, v in document.items()}, rules)


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    contract = run.contract
    if contract is None or not in_scope(contract, source.path):
        return ()
    rules = contract.subcontract.rules
    text = source.text(source.path)
    if text is None:
        text = source.fact_text(_CONTRACT_ROLE)
    if text is None:
        return ()
    path = Path(source.path)
    if path.suffix == _PYTHON_SUFFIX:
        return check_protocol_binding(path, text, rules)
    homes: dict[str, list[str]] = {}
    comparison = source.fact_text(_COMPARISON_ROLE)
    if comparison is not None:
        for key in _keys(comparison, _COMPARISON_ROLE, rules):
            homes.setdefault(key, []).append(_COMPARISON_ROLE)
    return check_setting_two_homes(path, _keys(text, source.path, rules), homes, rules)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: Python text (``.txt`` holding a module) or a bundle of contracts."""
    rules = contract.subcontract.rules
    text = fixture.read_text(encoding="utf-8")
    if fixture.suffix == ".txt":
        return check_protocol_binding(Path(fixture.stem), text, rules)
    bundle = yaml.safe_load(text)["contracts"]
    homes: dict[str, list[str]] = {}
    issues: list[ModelValidationIssue] = []
    for name, document in bundle.items():
        keys = contract_setting_keys(document, rules)
        issues.extend(check_setting_two_homes(Path(name), keys, homes, rules))
        for key in keys:
            homes.setdefault(key, []).append(name)
    return issues
