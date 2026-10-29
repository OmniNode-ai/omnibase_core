# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Baseline ratchet, runtime and validator entry of K6 families O, G, F, P, S, H, B (OMN-21537)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.private_vocabulary import ModelPrivateVocabularyResolution
from omnibase_core.validation.hardcoded_model_config import (
    runtime_hardcoded_model_config as runtime,
)
from omnibase_core.validation.hardcoded_model_config.handler import (
    added_entries,
    scan,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigBaselineEntry,
)
from omnibase_core.validation.validator_hardcoded_model_literals import (
    ValidatorHardcodedModelLiterals,
)

REPO_ROOT = Path(__file__).parents[4]
BASELINE = REPO_ROOT / "config/hardcoded_model_config_baseline.yaml"
LINE = "POLL_TIMEOUT_MS = 5000"
_NEUTRAL = ModelPrivateVocabularyResolution.model_construct(path=None, text=None)


def _sha1(line: str) -> str:
    return hashlib.sha1(line.strip().encode(), usedforsecurity=False).hexdigest()


def _write(root: Path, rel: str, text: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _baseline(root: Path, entries: list[dict[str, str]]) -> str:
    rel = "config/hardcoded_model_config_baseline.yaml"
    _write(root, rel, yaml.safe_dump({"schema_version": 1, "entries": entries}))
    return rel


def _entry(path: str = "src/pkg/a.py", line: str = LINE) -> dict[str, str]:
    return {"path": path, "family": "O", "content_sha1": _sha1(line)}


@pytest.mark.unit
def test_baseline_only_shrinks_a_new_literal_finding_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", LINE + "\n")
    rel = _baseline(tmp_path, [])
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1
    assert "src/pkg/a.py:1: [O in SOURCE]" in capsys.readouterr().out


@pytest.mark.unit
def test_baseline_only_shrinks_a_baselined_finding_passes_and_a_stale_entry_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", LINE + "\n")
    rel = _baseline(tmp_path, [_entry()])
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 0
    _write(tmp_path, "src/pkg/a.py", "POLL_TIMEOUT = None\n")
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1
    assert "stale baseline entry family=O" in capsys.readouterr().out


@pytest.mark.unit
def test_baseline_only_shrinks_growth_against_base_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", LINE + "\n")
    rel = _baseline(tmp_path, [_entry()])
    empty = yaml.safe_dump({"schema_version": 1, "entries": []})
    monkeypatch.setattr(runtime, "read_baseline_at_ref", lambda ref, path: empty)
    monkeypatch.setattr(runtime, "read_file_at_ref", lambda ref, path: None)
    argv = ["--baseline", rel, "--base", "origin/dev", "src/pkg/a.py"]
    assert runtime.main(argv) == 1
    assert "entries only leave" in capsys.readouterr().out
    head = [ModelHardcodedModelConfigBaselineEntry(**_entry())]
    assert added_entries([], head) == head
    assert added_entries(head, head) == []
    assert added_entries(head, []) == []


@pytest.mark.unit
def test_baseline_only_shrinks_admits_no_file_the_plan_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    policy = runtime.load_policy(_NEUTRAL)
    assert policy.unbaselinable_files
    committed = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))["entries"]
    assert {e["path"] for e in committed}.isdisjoint(policy.unbaselinable_files)
    named = policy.unbaselinable_files[0]
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, named, "x = 1\n")
    rel = _baseline(tmp_path, [_entry(named, "x = 1")])
    assert runtime.main(["--baseline", rel, named]) == 1
    assert "fixed, never baselined" in capsys.readouterr().out


@pytest.mark.unit
def test_baseline_only_shrinks_the_files_the_plan_names_hold_no_finding() -> None:
    policy = runtime.load_policy(_NEUTRAL)
    literals = runtime.load_literal_rule_set(policy)
    for rel in policy.unbaselinable_files:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert [
            f for f in scan(rel, text, policy, literals) if f.family in "OGFPSHB"
        ] == [], rel


@pytest.mark.unit
def test_baseline_only_shrinks_header_names_zero_date_and_burn_down() -> None:
    header = BASELINE.read_text(encoding="utf-8").split("schema_version")[0]
    assert re.search(r"Target zero: \d{4}-\d{2}-\d{2}", header)
    assert "Burn-down ticket" in header
    assert "OMN-21537" in header


@pytest.mark.unit
def test_the_validator_entry_loads_its_contract_and_judges_a_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "mod.py"
    target.write_text(LINE + "\n", encoding="utf-8")
    result = ValidatorHardcodedModelLiterals().validate([target])
    assert [i.rule_name for i in result.issues] == ["literal_operational_number"]


CHANGED_PRODUCTION_SOURCE = (
    "src/omnibase_core/validation/checker_hardcoded_model_literals.py",
    "src/omnibase_core/validation/checker_hardcoded_model_views.py",
    "src/omnibase_core/validation/validator_hardcoded_model_literals.py",
    "src/omnibase_core/validation/validator_hardcoded_model_scan.py",
    "src/omnibase_core/models/validation/model_hardcoded_literal_rule_set.py",
    "src/omnibase_core/validation/hardcoded_model_config/handler.py",
    "src/omnibase_core/validation/hardcoded_model_config/runtime_hardcoded_model_config.py",
    "src/omnibase_core/handlers/handler_internal_sibling_pins.py",
    "src/omnibase_core/handlers/handler_internal_sibling_pins_cli.py",
    "src/omnibase_core/nodes/node_dependency_pin_bump_effect/handler_dependency_pin_bump.py",
    ".github/workflows/publish-downstream-pin-bump.yml",
    ".github/workflows/internal-sibling-pins.yml",
)


@pytest.mark.unit
def test_changed_production_source_holds_no_literal_finding() -> None:
    policy = runtime.load_policy(_NEUTRAL)
    literals = runtime.load_literal_rule_set(policy)
    for rel in CHANGED_PRODUCTION_SOURCE:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert scan(rel, text, policy, literals) == [], rel


@pytest.mark.unit
def test_k10_reports_no_rule_table_in_the_checker_modules() -> None:
    from omnibase_core.validation.validator_checker_rule_data import (
        ValidatorCheckerRuleData,
    )

    paths = [
        REPO_ROOT / "src/omnibase_core/validation/checker_hardcoded_model_literals.py",
        REPO_ROOT
        / "src/omnibase_core/validation/validator_hardcoded_model_literals.py",
    ]
    result = ValidatorCheckerRuleData(root=REPO_ROOT).validate(paths)
    assert list(result.issues) == []
