# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for the receipt runtime-identity check node (OMN-21520)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.enums.enum_runtime_identity_rule import EnumRuntimeIdentityRule
from omnibase_core.models.nodes.receipt_runtime_identity_check.model_receipt_runtime_identity_check_input import (
    ModelReceiptRuntimeIdentityCheckInput,
)
from omnibase_core.nodes.node_receipt_runtime_identity_check_compute.handler import (
    NodeReceiptRuntimeIdentityCheckCompute,
)
from omnibase_core.nodes.node_receipt_runtime_identity_check_compute.runtime_receipt_runtime_identity_check import (
    main,
)
from omnibase_core.validation.validator_receipt_runtime_identity import (
    DEFAULT_REQUIRED_PACKAGES,
)

pytestmark = pytest.mark.unit


def _receipt(*, with_identity: bool) -> dict[str, object]:
    receipt: dict[str, object] = {
        "skill_name": "delegate",
        "node_name": "node_delegate_skill_orchestrator",
        "status": "success",
        "run_id": "0f0f0f0f-0000-4000-8000-000000000000",
        "schema_version": {"major": 1, "minor": 1, "patch": 0},
    }
    if with_identity:
        receipt["runtime_identity"] = {
            "host": "runtime-host",
            "packages": {
                name: {
                    "name": name,
                    "version": "0.0.1",
                    "commit": "a" * 40,
                    "source": "vcs",
                }
                for name in DEFAULT_REQUIRED_PACKAGES
            },
        }
    return receipt


def _write(tmp_path: Path, name: str, *, with_identity: bool) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(_receipt(with_identity=with_identity)), encoding="utf-8")
    return path


def test_handle_passes_complete_identity(tmp_path: Path) -> None:
    path = _write(tmp_path, "ok.json", with_identity=True)
    result = NodeReceiptRuntimeIdentityCheckCompute().handle(
        ModelReceiptRuntimeIdentityCheckInput(receipt_paths=(str(path),))
    )
    assert result.violations == ()
    assert result.receipts_found == 1


def test_handle_flags_missing_identity(tmp_path: Path) -> None:
    path = _write(tmp_path, "bad.json", with_identity=False)
    result = NodeReceiptRuntimeIdentityCheckCompute().handle(
        ModelReceiptRuntimeIdentityCheckInput(receipt_paths=(str(path),))
    )
    assert [v.rule for v in result.violations] == [
        EnumRuntimeIdentityRule.MISSING_IDENTITY
    ]
    assert result.receipts_found == 1


def test_main_exit_zero_on_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "ok.json", with_identity=True)
    assert main([str(path)]) == 0
    assert "RUNTIME IDENTITY GATE PASSED: 0 violations across 1 receipt(s)" in (
        capsys.readouterr().out
    )


def test_main_exit_one_on_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "bad.json", with_identity=False)
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "RUNTIME IDENTITY GATE FAILED: 1 violation(s)" in out
    assert "[missing_identity]" in out


def test_main_exit_two_without_target(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "ERROR: pass receipt files, or --receipts-dir" in capsys.readouterr().err
