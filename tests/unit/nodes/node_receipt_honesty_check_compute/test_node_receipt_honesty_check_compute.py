# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the receipt honesty node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_check_input import (
    ModelReceiptHonestyCheckInput,
)
from omnibase_core.nodes.node_receipt_honesty_check_compute.handler import (
    NodeReceiptHonestyCheckCompute,
)
from omnibase_core.nodes.node_receipt_honesty_check_compute.runtime_receipt_honesty_check import (
    main,
)

pytestmark = pytest.mark.unit


def _receipt(probe_command: str, probe_stdout: str) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-9999",
        "evidence_item_id": "dod-unit-tests",
        "check_type": "command",
        "check_value": probe_command,
        "status": "PASS",
        "run_timestamp": "2026-06-07T21:00:00+00:00",
        "commit_sha": "000000000000",
        "runner": "codex-worker",
        "verifier": "foreground-claude",
        "probe_command": probe_command,
        "probe_stdout": probe_stdout,
        "exit_code": 0,
    }


def _write(receipts_dir: Path, payload: dict[str, object]) -> Path:
    path = receipts_dir / "OMN-9999" / "dod-unit-tests" / "command.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


_HONEST = _receipt("uv run pytest tests/ -v", "42 passed in 1.23s")
_GAMED = _receipt("echo all-good", "all-good\n")


def test_handle_honest_receipt_passes(tmp_path: Path) -> None:
    _write(tmp_path, _HONEST)
    output = NodeReceiptHonestyCheckCompute().handle(
        ModelReceiptHonestyCheckInput(receipts_dir=str(tmp_path))
    )
    assert output.passed is True
    assert output.findings == []


def test_handle_gamed_receipt_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, _GAMED)
    output = NodeReceiptHonestyCheckCompute().handle(
        ModelReceiptHonestyCheckInput(receipts_dir=str(tmp_path))
    )
    assert output.passed is False
    assert [f.receipt_path for f in output.findings] == [str(path)]
    assert "NO_OP_PROBE" in {v.rule for v in output.findings[0].violations}


def test_handle_explicit_paths_skip_directory_walk(tmp_path: Path) -> None:
    gamed = _write(tmp_path / "a", _GAMED)
    output = NodeReceiptHonestyCheckCompute().handle(
        ModelReceiptHonestyCheckInput(
            receipts_dir=str(tmp_path / "missing"), receipt_paths=[str(gamed)]
        )
    )
    assert [f.receipt_path for f in output.findings] == [str(gamed)]


def test_main_honest_receipt_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, _HONEST)
    assert main(["--receipts-dir", str(tmp_path)]) == 0
    assert (
        f"RECEIPT HONESTY GATE PASSED: 0 violations in {tmp_path}"
        in capsys.readouterr().out
    )


def test_main_gamed_receipt_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, _GAMED)
    assert main(["--receipts-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "RECEIPT HONESTY GATE FAILED:" in out
    assert f"[NO_OP_PROBE] {path}" in out


def test_main_missing_receipts_dir_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--receipts-dir", str(tmp_path / "nope")]) == 1
    assert "ERROR: receipts-dir does not exist" in capsys.readouterr().err
