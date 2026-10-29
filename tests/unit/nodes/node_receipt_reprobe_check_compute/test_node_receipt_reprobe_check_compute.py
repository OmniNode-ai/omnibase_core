# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the receipt re-probe check node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.ticket.model_receipt_reprobe_result import (
    ReprobeStatus,
)
from omnibase_core.models.nodes.receipt_reprobe_check.model_receipt_reprobe_check_input import (
    ModelReceiptReprobeCheckInput,
)
from omnibase_core.nodes.node_receipt_reprobe_check_compute.handler import (
    NodeReceiptReprobeCheckCompute,
)
from omnibase_core.nodes.node_receipt_reprobe_check_compute.runtime_receipt_reprobe_check import (
    main,
)

pytestmark = pytest.mark.unit


def _write_receipt(receipts_dir: Path, probe_command: str) -> Path:
    path = receipts_dir / "OMN-A" / "dod-001" / "command.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "ticket_id": "OMN-A",
                "evidence_item_id": "dod-001",
                "check_type": "command",
                "check_value": "x",
                "probe_command": probe_command,
                "probe_stdout": "",
                "exit_code": 0,
                "runner": "worker",
                "verifier": "foreground-X",
                "run_timestamp": "2026-04-26T12:00:00Z",
                "status": "PASS",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_handle_empty_tree_passes(tmp_path: Path) -> None:
    report = NodeReceiptReprobeCheckCompute().handle(
        ModelReceiptReprobeCheckInput(receipts_dir=str(tmp_path))
    )
    assert report.results == []
    assert report.passed is True
    assert report.receipts_dir == str(tmp_path)


def test_handle_non_allowlisted_probe_fails(tmp_path: Path) -> None:
    _write_receipt(tmp_path, "rm -rf /")
    report = NodeReceiptReprobeCheckCompute().handle(
        ModelReceiptReprobeCheckInput(receipts_dir=str(tmp_path))
    )
    assert report.passed is False
    assert [r.status for r in report.results] == [ReprobeStatus.FAIL]
    assert "allowlist" in report.results[0].detail


def test_main_empty_tree_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--receipts-dir", str(tmp_path)]) == 0
    assert f"::notice::no receipts found under {tmp_path}" in capsys.readouterr().out


def test_main_non_allowlisted_probe_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_receipt(tmp_path, "rm -rf /")
    assert main(["--receipts-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "::error::RE-PROBE FAILED: 1 of 1 receipt(s) did not re-verify." in out
