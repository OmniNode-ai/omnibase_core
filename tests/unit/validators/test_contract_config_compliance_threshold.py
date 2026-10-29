# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-driven numeric threshold coverage (OMN-21503)."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers import handler_hardcoded_value_kinds_cli as kinds
from omnibase_core.handlers.handler_hardcoded_threshold import (
    load_contract_text,
    load_packaged_contract,
)
from omnibase_core.validators import contract_config_compliance as checker

pytestmark = pytest.mark.unit
RULE = "hardcoded_threshold"
RULES = frozenset({RULE})


@pytest.mark.parametrize(
    "assignment",
    [
        "REQUEST_TIMEOUT = 30",
        "REQUEST_TIMEOUT: float = 2.5",
        "REQUEST_TIMEOUT = -30",
        "REQUEST_TIMEOUT = +30",
        "OTHER = REQUEST_TIMEOUT = 30",
        "class Config:\n    REQUEST_TIMEOUT = 30",
        "if True:\n    REQUEST_TIMEOUT = 30",
    ],
)
def test_numeric_threshold_assignments(tmp_path: Path, assignment: str) -> None:
    path = tmp_path / "source.py"
    path.write_text(assignment + "\n")
    findings = checker.validate_file(path, RULES)
    assert len(findings) == 1
    assert findings[0].rule == RULE


@pytest.mark.parametrize(
    "assignment",
    [
        "REQUEST_TIMEOUT = True",
        "REQUEST_TIMEOUT = 0",
        "REQUEST_TIMEOUT = 1.0",
        "REQUEST_TIMEOUT = -0",
        "ordinary = 30",
        "request_timeout = 30",
        "REQUEST_TIMEOUT = compute()",
        f"REQUEST_TIMEOUT = 30 # {checker.SUPPRESSION_MARKER} fixture",
        "def run():\n    REQUEST_TIMEOUT = 30",
        "class C:\n    def run(self):\n        REQUEST_TIMEOUT = 30",
    ],
)
def test_non_thresholds(tmp_path: Path, assignment: str) -> None:
    path = tmp_path / "source.py"
    path.write_text(assignment + "\n")
    assert checker.validate_file(path, RULES) == []


def _contract_file(tmp_path: Path, **changes: object) -> Path:
    data = load_packaged_contract("contract_config_compliance").model_dump(mode="json")
    data["rules"][0]["parameters"].update(
        {k: v for k, v in changes.items() if k != "enabled"}
    )
    data["rules"][0]["enabled"] = changes.get("enabled", True)
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump({"validation": data}))
    assert load_contract_text(path.read_text())
    return path


def test_fixture_contract_changes_pattern(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.py"
    source.write_text("CUSTOM = 12\nREQUEST_TIMEOUT = 30\n")
    custom = _contract_file(tmp_path, name_pattern="CUSTOM")
    args = ["--kind", "threshold", "--contract", str(custom), str(source)]
    assert kinds.main(args) == 1
    err = capsys.readouterr().err
    assert "source.py:1" in err and "source.py:2" not in err
    disabled = _contract_file(tmp_path, enabled=False)
    assert (
        kinds.main(["--kind", "threshold", "--contract", str(disabled), str(source)])
        == 0
    )


def test_cli_baseline_multiset_growth_and_kind_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = Path("source.py")
    line = "REQUEST_TIMEOUT = 30"
    path.write_text(line + "\n")
    fp = f"{RULE}|source.py|{hashlib.sha1(line.encode()).hexdigest()}"
    baseline = Path("base.json")
    previous = Path("previous.json")
    previous.write_text('{"entries": []}')
    baseline.write_text(json.dumps({"entries": [fp]}))
    run = ["--kind", "threshold"]
    assert kinds.main([*run, str(path)]) == 1
    assert kinds.main([*run, str(path), "--baseline", str(baseline)]) == 0
    both = [
        str(path),
        "--baseline",
        str(baseline),
        "--previous-baseline",
        str(previous),
    ]
    assert kinds.main([*run, *both]) == 1
    path.write_text((line + "\n") * 2)
    assert kinds.main([*run, str(path), "--baseline", str(baseline)]) == 1
    baseline.write_text(
        json.dumps({"entries": [fp.replace(RULE, "hardcoded_host_list")]})
    )
    assert kinds.main([*run, str(path), "--baseline", str(baseline)]) == 1


def test_contract_default_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = Path("source.py")
    line = "REQUEST_TIMEOUT = 30"
    path.write_text(line + "\n")
    baseline = Path("base.json")
    fingerprint = f"{RULE}|source.py|{hashlib.sha1(line.encode()).hexdigest()}"
    baseline.write_text(json.dumps({"entries": [fingerprint]}))
    contract = _contract_file(tmp_path, baseline_path=str(baseline))
    assert (
        kinds.main(["--kind", "threshold", "--contract", str(contract), str(path)]) == 0
    )


@pytest.mark.parametrize("document", ['{"entries": [12]}', "{}", "not json"])
def test_invalid_baseline_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, document: str
) -> None:
    monkeypatch.chdir(tmp_path)
    baseline = Path("baseline.json")
    baseline.write_text(document)
    path = Path("source.py")
    path.write_text("REQUEST_TIMEOUT = 30\n")
    assert (
        kinds.main(["--kind", "threshold", str(path), "--baseline", str(baseline)]) == 1
    )


def test_nested_class_assignment_is_still_class_scope(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_text(
        "def factory():\n    class Config:\n        REQUEST_TIMEOUT = 30\n    return Config\n"
    )
    assert [f.line for f in checker.validate_file(path, RULES)] == [3]
