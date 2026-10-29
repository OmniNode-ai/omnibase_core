# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the OCC merge-eligibility node (OMN-21520)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.nodes.node_occ_merge_eligibility_check_compute.handler import (
    NodeOccMergeEligibilityCheckCompute,
)
from omnibase_core.nodes.node_occ_merge_eligibility_check_compute.runtime_occ_merge_eligibility_check import (
    main,
)

pytestmark = pytest.mark.unit

_TICKET = "OMN-10484"
_PR_SHA = "1" * 40
_OCC_SHA = "b" * 40
_COMMAND = "uv run pytest tests/unit/validation/test_occ_merge_eligibility.py -q"


def _write_evidence(root: Path, *, with_receipt: bool) -> None:
    contract_text = yaml.safe_dump(
        {
            "ticket_id": _TICKET,
            "title": "OCC eligibility",
            "dod_evidence": [
                {
                    "id": "dod-001",
                    "description": "focused tests pass",
                    "checks": [{"check_type": "command", "check_value": _COMMAND}],
                }
            ],
        },
        sort_keys=True,
    )
    (root / "contracts").mkdir()
    (root / "contracts" / f"{_TICKET}.yaml").write_text(contract_text, encoding="utf-8")
    if not with_receipt:
        return
    receipt = {
        "schema_version": "1.0.0",
        "ticket_id": _TICKET,
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": _COMMAND,
        "status": "PASS",
        "run_timestamp": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "commit_sha": _PR_SHA,
        "runner": "worker",
        "verifier": "foreground",
        "probe_command": _COMMAND,
        "probe_stdout": "1 passed\n",
        "exit_code": 0,
        "pr_number": 123,
        "contract_sha256": (
            f"sha256:{hashlib.sha256(contract_text.encode()).hexdigest()}"
        ),
    }
    path = root / "receipts" / _TICKET / "dod-001" / "command.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(receipt, sort_keys=True), encoding="utf-8")


def _snapshot(root: Path) -> ModelOccEligibilityInput:
    return ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title=f"feat({_TICKET}): harden OCC eligibility",
        pr_body=f"Closes: {_TICKET}",
        pr_branch=f"jonah/{_TICKET.lower()}-occ-eligibility",
        pr_commit_shas=(_PR_SHA,),
        pr_commit_texts=(f"feat({_TICKET}): add eligibility",),
        occ_commit_sha=_OCC_SHA,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


def _argv(root: Path) -> list[str]:
    return [
        "--repo",
        "omnibase_core",
        "--pr-number",
        "123",
        "--pr-title",
        f"feat({_TICKET}): harden OCC eligibility",
        "--pr-body",
        f"Closes: {_TICKET}",
        "--pr-branch",
        f"jonah/{_TICKET.lower()}-occ-eligibility",
        "--pr-commit-sha",
        _PR_SHA,
        "--occ-commit-sha",
        _OCC_SHA,
        "--contracts-dir",
        str(root / "contracts"),
        "--receipts-dir",
        str(root / "receipts"),
    ]


def test_handle_bound_pass_receipt_is_eligible(tmp_path: Path) -> None:
    _write_evidence(tmp_path, with_receipt=True)
    result = NodeOccMergeEligibilityCheckCompute().handle(_snapshot(tmp_path))
    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.ticket_ids == (_TICKET,)


def test_handle_missing_receipt_is_ineligible(tmp_path: Path) -> None:
    _write_evidence(tmp_path, with_receipt=False)
    result = NodeOccMergeEligibilityCheckCompute().handle(_snapshot(tmp_path))
    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT


def test_main_eligible_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_evidence(tmp_path, with_receipt=True)
    assert main(_argv(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible"] is True
    assert payload["reason"] == "eligible"


def test_main_ineligible_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_evidence(tmp_path, with_receipt=False)
    assert main(_argv(tmp_path)) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible"] is False
    assert payload["reason"] == "missing_receipt"
