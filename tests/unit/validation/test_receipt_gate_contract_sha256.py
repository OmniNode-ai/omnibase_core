# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract_sha256 hash-binding in the receipt-gate (OMN-10421).

Four cases per the plan (T11):
1. Receipt with matching contract_sha256 → PASS.
2. Receipt with mismatched contract_sha256 → FAIL ("contract mutated post-receipt").
3. Receipt missing contract_sha256 on a legacy PR (pre-cutoff) → ADVISORY/FAIL with
   migration-window message.
4. Receipt missing contract_sha256 on a post-cutoff PR → hard FAIL.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.receipt_gate import (
    _CONTRACT_SHA256_REQUIRED_AFTER,
    compute_contract_sha256,
    validate_pr_receipts,
)

_TICKET_ID = "OMN-10421"
_EVIDENCE_ID = "dod-001"
_CHECK_TYPE = "command"

# A PR opened 8 days before the cutoff — within the legacy window.
_PRE_CUTOFF_OPENED_AT = _CONTRACT_SHA256_REQUIRED_AFTER - timedelta(days=8)
# A PR opened at the cutoff or after — must hard-fail without contract_sha256.
_POST_CUTOFF_OPENED_AT = _CONTRACT_SHA256_REQUIRED_AFTER


def _write_contract(contracts_dir: Path) -> Path:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "ticket_id": _TICKET_ID,
        "schema_version": "1.0.0",
        "summary": "hash-binding test",
        "dod_evidence": [
            {
                "id": _EVIDENCE_ID,
                "description": "test check",
                "checks": [{"check_type": _CHECK_TYPE, "check_value": "echo ok"}],
            }
        ],
    }
    path = contracts_dir / f"{_TICKET_ID}.yaml"
    path.write_text(yaml.safe_dump(body))
    return path


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_dict(
    *,
    contract_sha256: str | None,
    ticket_id: str = _TICKET_ID,
) -> dict[str, object]:
    d: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": _EVIDENCE_ID,
        "check_type": _CHECK_TYPE,
        "check_value": "echo ok",
        "status": "PASS",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "ci-receipt-gate",
        "verifier": "foreground-receipt-gate-2026-04-30",
        "probe_command": "echo ok",
        "probe_stdout": "ok\n",
    }
    if contract_sha256 is not None:
        d["contract_sha256"] = contract_sha256
    return d


def _write_receipt(receipts_dir: Path, data: dict[str, object]) -> None:
    p = receipts_dir / _TICKET_ID / _EVIDENCE_ID / f"{_CHECK_TYPE}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data))


@pytest.mark.unit
class TestContractSha256HashBinding:
    def test_matching_contract_sha256_passes(self, tmp_path: Path) -> None:
        """Receipt with correct contract_sha256 must PASS the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        contract_path = _write_contract(contracts)
        correct_sha = _sha256_of(contract_path)

        _write_receipt(receipts, _receipt_dict(contract_sha256=correct_sha))
        result = validate_pr_receipts(
            pr_body=f"Closes {_TICKET_ID}",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_POST_CUTOFF_OPENED_AT,
        )
        assert result.passed, result.message

    def test_mismatched_contract_sha256_fails(self, tmp_path: Path) -> None:
        """Receipt with wrong contract_sha256 must FAIL with 'contract mutated' message."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts)
        wrong_sha = "a" * 64  # valid format but wrong digest

        _write_receipt(receipts, _receipt_dict(contract_sha256=wrong_sha))
        result = validate_pr_receipts(
            pr_body=f"Closes {_TICKET_ID}",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_POST_CUTOFF_OPENED_AT,
        )
        assert not result.passed
        msg_lower = result.message.lower()
        assert "contract mutated" in msg_lower or "rerun probes" in msg_lower, (
            f"expected 'contract mutated' or 'rerun probes' in message; got: {result.message!r}"
        )

    def test_missing_contract_sha256_pre_cutoff_is_advisory_fail(
        self, tmp_path: Path
    ) -> None:
        """Legacy receipt without contract_sha256 on a pre-cutoff PR → ADVISORY downgrade, not hard FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts)
        _write_receipt(receipts, _receipt_dict(contract_sha256=None))

        result = validate_pr_receipts(
            pr_body=f"Closes {_TICKET_ID}",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_PRE_CUTOFF_OPENED_AT,
        )
        assert not result.passed
        msg_lower = result.message.lower()
        assert (
            "advisory" in msg_lower
            or "migration window" in msg_lower
            or "legacy" in msg_lower
        ), (
            f"expected advisory/migration/legacy in message for pre-cutoff legacy receipt; "
            f"got: {result.message!r}"
        )

    def test_missing_contract_sha256_post_cutoff_hard_fails(
        self, tmp_path: Path
    ) -> None:
        """Receipt without contract_sha256 on a post-cutoff PR → hard FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts)
        _write_receipt(receipts, _receipt_dict(contract_sha256=None))

        result = validate_pr_receipts(
            pr_body=f"Closes {_TICKET_ID}",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_POST_CUTOFF_OPENED_AT,
        )
        assert not result.passed
        msg_lower = result.message.lower()
        assert "contract_sha256" in msg_lower or "rerun probes" in msg_lower, (
            f"expected 'contract_sha256' or 'rerun probes' in post-cutoff failure; "
            f"got: {result.message!r}"
        )

    def test_missing_pr_opened_at_skips_hash_check(self, tmp_path: Path) -> None:
        """When pr_opened_at is None, the hash check is skipped entirely — backward-compatible."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts)
        _write_receipt(receipts, _receipt_dict(contract_sha256=None))

        result = validate_pr_receipts(
            pr_body=f"Closes {_TICKET_ID}",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=None,
        )
        assert result.passed, result.message


@pytest.mark.unit
class TestComputeContractSha256:
    def test_sha256_matches_hashlib(self, tmp_path: Path) -> None:
        """compute_contract_sha256 must return the same digest as hashlib directly."""
        f = tmp_path / "OMN-10421.yaml"
        f.write_bytes(b"ticket_id: OMN-10421\n")
        expected = hashlib.sha256(b"ticket_id: OMN-10421\n").hexdigest()
        assert compute_contract_sha256(f) == expected

    def test_sha256_is_64_lowercase_hex(self, tmp_path: Path) -> None:
        f = tmp_path / "test.yaml"
        f.write_bytes(b"x: 1\n")
        digest = compute_contract_sha256(f)
        assert len(digest) == 64
        assert digest == digest.lower()
        assert all(c in "0123456789abcdef" for c in digest)

    def test_sha256_changes_when_content_changes(self, tmp_path: Path) -> None:
        f = tmp_path / "test.yaml"
        f.write_bytes(b"original: true\n")
        sha1 = compute_contract_sha256(f)
        f.write_bytes(b"mutated: true\n")
        sha2 = compute_contract_sha256(f)
        assert sha1 != sha2
