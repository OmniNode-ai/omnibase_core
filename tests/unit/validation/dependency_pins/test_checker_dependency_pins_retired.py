# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The pin check refuses a retired repository through every manifest table (OMN-22385).

The layer order and the pin policy are the copies shipped in the package, so the
retired list is the contract's and no test row restates it.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_result import (
    ModelDependencyPinFactsResult,
)
from omnibase_core.models.dependency_pins.model_dependency_pins_input import (
    ModelDependencyPinsInput,
)
from omnibase_core.validation import checker_dependency_pins as checker
from omnibase_core.validation.validator_dependency_pins import (
    ValidatorDependencyPins,
    load_dependency_pin_policy,
    load_layer_order,
)

pytestmark = pytest.mark.unit

_RETIRED_DIST = "omnibase-compat"
_HEAD = '[project]\nname = "omnibase-infra"\n'


def _rules() -> dict[str, ModelValidatorRule]:
    validator = ValidatorDependencyPins(lambda _r: ModelDependencyPinFactsResult())
    return {r.rule_id: r for r in validator.contract.rules}


def _codes(manifest: str) -> list[str]:
    request = ModelDependencyPinsInput(
        manifest_path="pyproject.toml",
        manifest_text=manifest,
        lock_path="uv.lock",
        precommit_path=".pre-commit-config.yaml",
        layer_map=load_layer_order(),
        policy=load_dependency_pin_policy(),
    )
    rules = _rules()
    return sorted(str(i.code) for i in checker.check_dependency_pins(request, rules))


@pytest.mark.parametrize(
    "manifest",
    [
        _HEAD + f'dependencies = ["{_RETIRED_DIST}==0.5.7"]\n',
        _HEAD + f'[project.optional-dependencies]\nx = ["{_RETIRED_DIST}>=0.5"]\n',
        _HEAD + f'[dependency-groups]\ndev = ["{_RETIRED_DIST}"]\n',
        _HEAD + f'[tool.uv]\ndev-dependencies = ["{_RETIRED_DIST}"]\n',
        _HEAD + f'[tool.uv]\noverride-dependencies = ["{_RETIRED_DIST}>=0.5,<0.6"]\n',
        _HEAD + f'[tool.uv.sources]\n{_RETIRED_DIST} = {{ path = "../compat" }}\n',
    ],
    ids=["dependency", "extra", "group", "uv-dev", "override", "uv-source"],
)
def test_a_retired_distribution_is_refused(manifest: str) -> None:
    assert "retired_repository" in _codes(manifest)


def test_the_finding_names_the_retirement() -> None:
    request = ModelDependencyPinsInput(
        manifest_path="pyproject.toml",
        manifest_text=_HEAD + f'dependencies = ["{_RETIRED_DIST}==0.5.7"]\n',
        lock_path="uv.lock",
        precommit_path=".pre-commit-config.yaml",
        layer_map=load_layer_order(),
        policy=load_dependency_pin_policy(),
    )
    issues = [
        i
        for i in checker.check_dependency_pins(request, _rules())
        if str(i.code) == "retired_repository"
    ]
    assert len(issues) == 1
    assert "retired" in issues[0].message.lower()


def test_a_manifest_without_the_retired_distribution_is_not_refused() -> None:
    assert "retired_repository" not in _codes(_HEAD + 'dependencies = ["pydantic"]\n')
