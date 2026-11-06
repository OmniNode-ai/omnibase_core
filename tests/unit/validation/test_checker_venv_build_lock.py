# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the venv build-lock checker and validator (OMN-22649).

The deadlock: a lock-moving commit (omniclaude#3188, 2026-11-06) moved ``omnibase-spi``
0.23.8 to 0.23.14 and the core git tag. The hook interpreter was a ``.venv`` built from the
checkout. The old rule judged its registry pins against the canonical clone's lock (spi 0.23.8)
and its git sources against the checkout lock, so no venv could pass both halves.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.venv_build_lock.model_venv_build_lock_check_input import (
    ModelVenvBuildLockCheckInput,
)
from omnibase_core.models.venv_build_lock.model_venv_build_lock_surface import (
    ModelVenvBuildLockSurface,
)
from omnibase_core.validation import checker_venv_build_lock, validator_base
from omnibase_core.validation.checker_venv_build_lock import check_venv_build_lock
from omnibase_core.validation.validator_venv_build_lock import ValidatorVenvBuildLock

CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "venv_build_lock.validation.yaml"
)
OLD_CORE = "a" * 40
NEW_CORE = "b" * 40


def _lock(spi: str, core: str) -> str:
    return f"""version = 1

[[package]]
name = "omnibase-spi"
version = "{spi}"
source = {{ registry = "https://pypi.org/simple" }}

[[package]]
name = "omnibase-core"
version = "0.47.0"
source = {{ git = "https://github.com/OmniNode-ai/omnibase_core.git?tag=dev-x#{core}" }}

[[package]]
name = "omniclaude"
version = "0.1.0"
source = {{ editable = "." }}
"""


DEV_LOCK = _lock("0.23.8", OLD_CORE)
CHECKOUT_LOCK = _lock("0.23.14", NEW_CORE)


def _contract(data: dict[str, Any] | None = None) -> ModelValidatorSubcontract:
    loaded = data or yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    return ModelValidatorSubcontract.model_validate(loaded)


def _surface(
    lock: str | None, spi: str, core: str, label: str = "hook interpreter"
) -> ModelVenvBuildLockSurface:
    return ModelVenvBuildLockSurface(
        label=label,
        build_lock_path="/lock/uv.lock",
        build_lock_text=lock,
        installed={"omnibase-spi": spi},
        installed_git={"omnibase-core": core[:12]},
    )


def _check(
    surfaces: tuple[ModelVenvBuildLockSurface, ...],
    checkout: str = CHECKOUT_LOCK,
    contract: ModelValidatorSubcontract | None = None,
) -> Any:
    return check_venv_build_lock(
        ModelVenvBuildLockCheckInput(
            source_name="facts.venv-build-lock-facts.json",
            checkout_lock_text=checkout,
            surfaces=surfaces,
            contract=contract or _contract(),
        )
    )


def _codes(result: Any) -> list[str]:
    return sorted(str(issue.code) for issue in result.issues)


@pytest.mark.unit
class TestLockMovingCommit:
    def test_golden_surface_built_from_the_checkout_lock_passes(self) -> None:
        result = _check((_surface(CHECKOUT_LOCK, "0.23.14", NEW_CORE),))
        assert [i for i in result.issues if i.severity.value == "error"] == []
        assert result.surfaces_judged == 1

    def test_golden_surface_built_from_the_clone_lock_passes_without_the_checkout(
        self,
    ) -> None:
        result = _check((_surface(DEV_LOCK, "0.23.8", OLD_CORE),))
        assert [i for i in result.issues if i.severity.value == "error"] == []
        assert _codes(result) == ["checkout_lock_not_authority"]

    def test_failing_control_judging_against_the_clone_lock_is_red(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Named injected break: every surface judged against the clone lock, as the old gate did."""
        surfaces = (_surface(CHECKOUT_LOCK, "0.23.14", NEW_CORE),)
        monkeypatch.setattr(
            checker_venv_build_lock, "build_lock_for", lambda _s, _c: DEV_LOCK
        )
        result = _check(surfaces)
        assert _codes(result) == [
            "checkout_lock_not_authority",
            "surface_git_pin",
            "surface_registry_pin",
        ]


@pytest.mark.unit
class TestErrorChain:
    def test_in_place_registry_drift_on_the_same_surface_is_refused(self) -> None:
        result = _check((_surface(CHECKOUT_LOCK, "0.23.8", NEW_CORE),))
        assert _codes(result) == ["surface_registry_pin"]
        assert "pins 0.23.14" in result.issues[0].message

    def test_in_place_git_drift_is_refused(self) -> None:
        result = _check((_surface(CHECKOUT_LOCK, "0.23.14", OLD_CORE),))
        assert _codes(result) == ["surface_git_pin"]

    def test_unreadable_build_lock_fails_closed(self) -> None:
        result = _check((_surface(None, "0.23.14", NEW_CORE),))
        assert _codes(result) == ["build_lock_unreadable"]
        assert result.surfaces_judged == 0

    def test_a_missing_rule_is_a_contract_error(self) -> None:
        data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
        data["rules"] = [r for r in data["rules"] if r["rule_id"] != "surface_git_pin"]
        with pytest.raises(ModelOnexError):
            _check(
                (_surface(CHECKOUT_LOCK, "0.23.14", NEW_CORE),),
                contract=_contract(data),
            )

    def test_disabling_a_rule_in_the_contract_silences_it_with_no_code_change(
        self,
    ) -> None:
        data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
        for rule in data["rules"]:
            if rule["rule_id"] == "surface_registry_pin":
                rule["enabled"] = False
        result = _check(
            (_surface(CHECKOUT_LOCK, "0.23.8", NEW_CORE),), contract=_contract(data)
        )
        assert _codes(result) == []


@pytest.mark.unit
class TestValidatorReadsFiles:
    def _write(self, tmp_path: Path, spi: str) -> Path:
        checkout = tmp_path / "checkout.lock"
        checkout.write_text(CHECKOUT_LOCK, encoding="utf-8")
        facts = tmp_path / "run.venv-build-lock-facts.json"
        facts.write_text(
            json.dumps(
                {
                    "checkout_lock_path": str(checkout),
                    "surfaces": [
                        {
                            "label": "hook interpreter",
                            "build_lock_path": str(checkout),
                            "installed": {"omnibase-spi": spi},
                            "installed_git": {"omnibase-core": NEW_CORE[:12]},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return facts

    def test_validator_passes_the_lock_moving_shape(self, tmp_path: Path) -> None:
        facts = self._write(tmp_path, "0.23.14")
        validator = ValidatorVenvBuildLock()
        issues = validator._validate_file(facts, validator._load_contract())
        assert [i for i in issues if i.severity.value == "error"] == []

    def test_validator_refuses_drift(self, tmp_path: Path) -> None:
        facts = self._write(tmp_path, "0.23.8")
        validator = ValidatorVenvBuildLock()
        issues = validator._validate_file(facts, validator._load_contract())
        assert [i.code for i in issues] == ["surface_registry_pin"]

    def test_validator_refuses_an_unreadable_build_lock(self, tmp_path: Path) -> None:
        facts = self._write(tmp_path, "0.23.14")
        data = json.loads(facts.read_text("utf-8"))
        data["surfaces"][0]["build_lock_path"] = str(tmp_path / "absent.lock")
        facts.write_text(json.dumps(data), encoding="utf-8")
        validator = ValidatorVenvBuildLock()
        issues = validator._validate_file(facts, validator._load_contract())
        assert "build_lock_unreadable" in [i.code for i in issues]
