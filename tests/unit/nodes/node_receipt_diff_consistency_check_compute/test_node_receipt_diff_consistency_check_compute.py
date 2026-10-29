# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the receipt diff-consistency node (OMN-21520)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_diff_attestation import EnumDiffAttestation
from omnibase_core.models.nodes.receipt_diff_consistency_check.model_receipt_diff_consistency_check_input import (
    ModelReceiptDiffConsistencyCheckInput,
)
from omnibase_core.nodes.node_receipt_diff_consistency_check_compute.handler import (
    NodeReceiptDiffConsistencyCheckCompute,
)
from omnibase_core.nodes.node_receipt_diff_consistency_check_compute.runtime_receipt_diff_consistency_check import (
    main,
)

pytestmark = pytest.mark.unit

_CLAIM = (
    "No existing receipts or the OMN-13501 contract are modified "
    "(OMN-13888 net-new-only)."
)
_MUTATING_DIFF = [
    ("M", "contracts/OMN-13501.yaml"),
    ("A", "drift/dod_receipts/OMN-13501/dod-self-binding/command.yaml"),
]
_NET_NEW_DIFF = [
    ("A", "contracts/OMN-13501.yaml"),
    ("A", "drift/dod_receipts/OMN-13501/dod-self-binding/command.yaml"),
]


def _write_receipt(tmp_path: Path) -> Path:
    path = (
        tmp_path
        / "drift"
        / "dod_receipts"
        / "OMN-13501"
        / "dod-self-binding"
        / "command.yaml"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "ticket_id": "OMN-13501",
                "evidence_item_id": "dod-self-binding",
                "check_type": "attestation",
                "check_value": "net-new-only self-binding receipt",
                "status": "PASS",
                "run_timestamp": datetime.now(tz=UTC).isoformat(),
                "commit_sha": "000000000000",
                "runner": "codex-worker",
                "verifier": "foreground-claude",
                "probe_command": "git diff",
                "probe_stdout": "output",
                "actual_output": _CLAIM,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_diff(tmp_path: Path, entries: list[tuple[str, str]]) -> Path:
    diff_file = tmp_path / "diff.txt"
    diff_file.write_text(
        "".join(f"{code}\t{path}\n" for code, path in entries), encoding="utf-8"
    )
    return diff_file


def test_handle_net_new_diff_passes(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path)
    output = NodeReceiptDiffConsistencyCheckCompute().handle(
        ModelReceiptDiffConsistencyCheckInput(
            receipt_paths=[str(receipt)], name_status=_NET_NEW_DIFF
        )
    )
    assert output.passed is True
    assert output.violations == []


def test_handle_mutating_diff_fails(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path)
    output = NodeReceiptDiffConsistencyCheckCompute().handle(
        ModelReceiptDiffConsistencyCheckInput(
            receipt_paths=[str(receipt)], name_status=_MUTATING_DIFF
        )
    )
    assert output.passed is False
    assert [v.attestation for v in output.violations] == [
        EnumDiffAttestation.NET_NEW_ONLY
    ]
    assert output.violations[0].receipt_path == str(receipt)


def test_main_net_new_diff_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    receipt = _write_receipt(tmp_path)
    diff_file = _write_diff(tmp_path, _NET_NEW_DIFF)
    assert main(["--diff-file", str(diff_file), str(receipt)]) == 0
    assert (
        "RECEIPT DIFF-CONSISTENCY GATE PASSED: "
        "0 contradicted attestations across 1 receipt(s)"
    ) in capsys.readouterr().out


def test_main_mutating_diff_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    receipt = _write_receipt(tmp_path)
    diff_file = _write_diff(tmp_path, _MUTATING_DIFF)
    assert main(["--diff-file", str(diff_file), str(receipt)]) == 1
    out = capsys.readouterr().out
    assert "RECEIPT DIFF-CONSISTENCY GATE FAILED: 1 contradicted attestation(s)" in out
    assert f"[{EnumDiffAttestation.NET_NEW_ONLY}] {receipt}" in out


def test_main_missing_diff_file_exits_one(tmp_path: Path) -> None:
    assert main(["--diff-file", str(tmp_path / "nope.txt")]) == 1
