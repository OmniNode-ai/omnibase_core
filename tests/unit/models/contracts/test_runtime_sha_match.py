# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime SHA match contract classifier and receipt-gate semantics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract
from omnibase_core.validation.receipt_gate import validate_pr_receipts
from omnibase_core.validation.runtime_sha_match import CHECK_TYPE_RUNTIME_SHA_MATCH

pytestmark = pytest.mark.unit

_TICKET_ID = "OMN-9334"
_EVIDENCE_ID = "dod-003"
_MERGE_SHA = "abc123def456"  # pragma: allowlist secret
_STALE_SHA = "deadbeef0000"  # pragma: allowlist secret


def test_classify_runtime_change_requires_infra_source() -> None:
    assert ModelTicketContract.classify_runtime_change(
        ["omnibase_infra/src/omnibase_infra/runtime/service.py"]
    )


def test_classify_runtime_change_requires_deployed_omnimarket_node() -> None:
    assert ModelTicketContract.classify_runtime_change(
        ["omnimarket/src/omnimarket/nodes/node_redeploy/handlers/handler.py"],
        deployed_nodes=frozenset({"node_redeploy"}),
    )


def test_classify_runtime_change_skips_undeployed_node_when_registry_supplied() -> None:
    assert not ModelTicketContract.classify_runtime_change(
        ["omnimarket/src/omnimarket/nodes/node_experiment/handlers/handler.py"],
        deployed_nodes=frozenset({"node_redeploy"}),
    )


def test_classify_runtime_change_skips_docs_tests_and_local_plugins() -> None:
    assert not ModelTicketContract.classify_runtime_change(
        [
            "omnibase_infra/tests/test_runtime.py",
            "omnimarket/src/omnimarket/nodes/node_redeploy/tests/test_handler.py",
            "omniclaude/plugins/onex/skills/foo/SKILL.md",
            "docs/runtime.md",
        ]
    )


def test_receipt_gate_rejects_stale_runtime_sha_receipt(tmp_path: Path) -> None:
    contracts_dir = tmp_path / "contracts"
    receipts_dir = tmp_path / "drift" / "dod_receipts"
    _write_contract(contracts_dir)
    _write_receipt(
        receipts_dir,
        status=EnumReceiptStatus.FAIL,
        deployed_sha=_STALE_SHA,
        merge_sha=_MERGE_SHA,
        match=False,
    )

    result = validate_pr_receipts(
        pr_body=f"Implements {_TICKET_ID}",
        pr_title=f"{_TICKET_ID}: runtime sha gate",
        contracts_dir=contracts_dir,
        receipts_dir=receipts_dir,
    )

    assert result.passed is False
    assert "runtime_sha_match" in result.message
    assert "FAIL" in result.message or "blocking" in result.message


def test_receipt_gate_accepts_matching_runtime_sha_receipt(tmp_path: Path) -> None:
    contracts_dir = tmp_path / "contracts"
    receipts_dir = tmp_path / "drift" / "dod_receipts"
    _write_contract(contracts_dir)
    _write_receipt(
        receipts_dir,
        status=EnumReceiptStatus.PASS,
        deployed_sha=_MERGE_SHA,
        merge_sha=_MERGE_SHA,
        match=True,
    )

    result = validate_pr_receipts(
        pr_body=f"Implements {_TICKET_ID}",
        pr_title=f"{_TICKET_ID}: runtime sha gate",
        contracts_dir=contracts_dir,
        receipts_dir=receipts_dir,
    )

    assert result.passed is True


def _write_contract(contracts_dir: Path) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ticket_id": _TICKET_ID,
        "title": "Runtime SHA gate",
        "dod_evidence": [
            {
                "id": _EVIDENCE_ID,
                "description": "Runtime SHA matches merged SHA",
                "checks": [
                    {
                        "check_type": CHECK_TYPE_RUNTIME_SHA_MATCH,
                        "check_value": _MERGE_SHA,
                    }
                ],
            }
        ],
    }
    (contracts_dir / f"{_TICKET_ID}.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=True),
        encoding="utf-8",
    )


def _write_receipt(
    receipts_dir: Path,
    *,
    status: EnumReceiptStatus,
    deployed_sha: str,
    merge_sha: str,
    match: bool,
) -> None:
    receipt = ModelDodReceipt(
        schema_version="1.0.0",
        ticket_id=_TICKET_ID,
        evidence_item_id=_EVIDENCE_ID,
        check_type=CHECK_TYPE_RUNTIME_SHA_MATCH,
        check_value=merge_sha,
        status=status,
        run_timestamp=datetime.now(tz=UTC),
        commit_sha=deployed_sha,
        runner="integration-sweep-verifier",
        verifier="receipt-gate-test-verifier",
        probe_command="ssh 192.168.86.201 git -C /data/omninode/omni_home/omnimarket rev-parse HEAD",
        probe_stdout=f"{deployed_sha}\n",
        actual_output=json.dumps(
            {
                "runtime_host": "192.168.86.201",
                "deployed_sha": deployed_sha,
                "merge_sha": merge_sha,
                "match": match,
            }
        ),
    )
    receipt_path = receipts_dir / _TICKET_ID / _EVIDENCE_ID / "runtime_sha_match.yaml"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        yaml.safe_dump(receipt.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )
