# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts-file validator and CLI acceptance tests."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_delivery_resolved_kind import (
    EnumDeliveryResolvedKind as Resolved,
)
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.handlers.handler_delivery_reference_cli import (
    ValidatorDeliveryReference,
    main,
)
from omnibase_core.models.delivery import ModelDeliveryFacts
from tests.unit.handlers.test_handler_delivery_reference import overlay, path, ref

pytestmark = pytest.mark.unit


def facts_file(tmp_path: Path, *, unknown: bool = False) -> Path:
    facts = ModelDeliveryFacts(
        overlay=overlay(),
        paths=(path(),),
        refs=(ref("unrecognized", Resolved.UNRESOLVED) if unknown else ref(),),
    )
    filename = tmp_path / "fixture.delivery-facts.yaml"
    filename.write_text(yaml.safe_dump(facts.model_dump(mode="json")), encoding="utf-8")
    return filename


def run_cli(filename: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "uv",
            "run",
            "--cache-dir",
            str(filename.parent / "uv-cache"),
            "python",
            "-m",
            "omnibase_core.handlers.handler_delivery_reference_cli",
            str(filename),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_pass_file_exit_zero(tmp_path: Path) -> None:
    filename = facts_file(tmp_path)
    assert ValidatorDeliveryReference().validate_file(filename).is_valid
    assert run_cli(filename).returncode == 0


def test_ac2_unknown_fixture_is_finding_and_nonzero(tmp_path: Path) -> None:
    filename = facts_file(tmp_path, unknown=True)
    result = ValidatorDeliveryReference().validate_file(filename)
    assert not result.is_valid
    assert result.issues[0].rule_name == "delivery_reference_refused"
    assert (
        result.issues[0].context is not None
        and result.issues[0].context["kind"] == "unknown"
    )
    completed = run_cli(filename)
    assert completed.returncode != 0
    assert result.issues[0].message in completed.stdout


@pytest.mark.parametrize("text", ["invalid: [", "{}", "overlay: null", "\xff"])
def test_invalid_facts_fail_closed(tmp_path: Path, text: str) -> None:
    filename = tmp_path / "invalid.delivery-facts.yaml"
    filename.write_bytes(text.encode("latin-1"))
    result = ValidatorDeliveryReference().validate_file(filename)
    assert not result.is_valid
    assert (
        len(result.issues) == 1
        and result.issues[0].rule_name == "delivery_reference_facts_unreadable"
    )
    assert run_cli(filename).returncode != 0


def test_unreadable_facts_fail_closed_even_for_explicit_missing_cli_target(
    tmp_path: Path,
) -> None:
    filename = tmp_path / "missing.delivery-facts.yaml"
    result = ValidatorDeliveryReference().validate_file(filename)
    assert not result.is_valid and len(result.issues) == 1
    assert result.issues[0].rule_name == "delivery_reference_facts_unreadable"
    assert run_cli(filename).returncode != 0


def test_rule_enabled_and_severity_are_honored(tmp_path: Path) -> None:
    filename = facts_file(tmp_path, unknown=True)
    original = ValidatorDeliveryReference().contract
    refused = next(
        rule for rule in original.rules if rule.rule_id == "delivery_reference_refused"
    )
    for enabled, severity in (
        (False, EnumSeverity.ERROR),
        (True, EnumSeverity.WARNING),
    ):
        contract = original.model_copy(
            update={
                "rules": [
                    refused.model_copy(
                        update={"enabled": enabled, "severity": severity}
                    )
                ]
            }
        )
        result = ValidatorDeliveryReference(contract=contract).validate_file(filename)
        assert len(result.issues) == int(enabled)
        if enabled:
            assert result.issues[0].severity == severity


def test_ac6_reconciliation_findings_are_included(tmp_path: Path) -> None:
    filename = facts_file(tmp_path)
    facts = ModelDeliveryFacts(
        overlay=overlay(),
        paths=(path(),),
        refs=(ref(),),
        unreadable_locations=("consumer.yml",),
        discovered=(ref(location="extra.yml"),),
    )
    filename.write_text(yaml.safe_dump(facts.model_dump(mode="json")))
    result = ValidatorDeliveryReference().validate_file(filename)
    assert {i.rule_name for i in result.issues} == {
        "delivery_reference_blocked",
        "delivery_reference_undeclared",
    }


def test_script_hook_and_contract_are_wired() -> None:
    root = Path(__file__).resolve().parents[3]
    scripts = tomllib.loads((root / "pyproject.toml").read_text())["project"]["scripts"]
    assert (
        scripts["check-delivery-reference"]
        == "omnibase_core.handlers.handler_delivery_reference_cli:main"
    )
    hooks = yaml.load(
        (root / ".pre-commit-hooks.yaml").read_text(), Loader=yaml.SafeLoader
    )
    hook = next(h for h in hooks if h["id"] == "check-delivery-reference")
    assert (
        hook["entry"]
        == "python -m omnibase_core.handlers.handler_delivery_reference_cli"
    )
    assert hook["files"] == r"\.delivery-facts\.ya?ml$"
    assert (
        hook["pass_filenames"]
        and hook["require_serial"]
        and hook["stages"] == ["pre-commit"]
    )
    contract = ValidatorDeliveryReference().contract
    assert contract.validator_id == "delivery_reference"
    assert all(
        rule.enabled and rule.severity == EnumSeverity.ERROR for rule in contract.rules
    )


def test_console_entry_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys, "argv", ["check-delivery-reference", str(facts_file(tmp_path))]
    )
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 0
