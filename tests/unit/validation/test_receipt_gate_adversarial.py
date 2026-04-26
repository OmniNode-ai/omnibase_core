# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Adversarial-invariant tests for the canonical Receipt-Gate (OMN-9788).

These tests harden ``omnibase_core.validation.receipt_gate`` against the
loopholes that the OMN-9786 ``ModelDodReceipt`` invariants closed at the
model layer:

1. ``verifier == runner`` (self-attestation) must NOT satisfy the gate.
2. Missing ``verifier`` field (legacy / pre-OMN-9786 receipts) must NOT
   satisfy the gate, and the failure message must mention ``verifier``
   so the operator can fix the receipt.
3. Receipts that produced no captured stdout for an executable
   ``check_type`` must NOT satisfy the gate (these are
   indistinguishable from "never ran").
4. Distinct verifier/runner with non-empty stdout and PASS status must
   pass.

Each test writes a literal receipt YAML to disk and asserts the literal
gate output, per the plan's "literal command + literal stdout
assertions" acceptance criterion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.receipt_gate import validate_pr_receipts


def _write_contract(
    contracts_dir: Path, ticket_id: str, check_type: str = "command"
) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "ticket_id": ticket_id,
        "schema_version": "1.0.0",
        "summary": "test",
        "dod_evidence": [
            {
                "id": "dod-001",
                "description": "test check",
                "checks": [{"check_type": check_type, "check_value": "echo ok"}],
            }
        ],
    }
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _receipt_dict(
    *,
    ticket_id: str = "OMN-9084",
    runner: str = "worker-A",
    verifier: str = "foreground-claude-X",
    status: str = "PASS",
    probe_stdout: str = "ok\n",
    check_type: str = "command",
    check_value: str = "echo ok",
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": "dod-001",
        "check_type": check_type,
        "check_value": check_value,
        "status": status,
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": runner,
        "verifier": verifier,
        "probe_command": check_value,
        "probe_stdout": probe_stdout,
    }


def _write_receipt_yaml(
    receipts_dir: Path, ticket_id: str, data: dict[str, object]
) -> Path:
    p = receipts_dir / ticket_id / "dod-001" / "command.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data))
    return p


@pytest.mark.unit
class TestReceiptGateAdversarialVerifier:
    """Verifier ≠ runner enforcement."""

    def test_receipt_with_verifier_equal_runner_fails(self, tmp_path: Path) -> None:
        """verifier == runner self-attestation must FAIL the gate.

        ``ModelDodReceipt`` auto-downgrades PASS→ADVISORY when
        ``verifier == runner``; the gate must surface this as a failure
        whose detail mentions ``advisory`` or ``verifier`` so the
        operator can fix the receipt.
        """
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        # verifier == runner triggers the OMN-9786 ADVISORY downgrade
        data = _receipt_dict(runner="worker-A", verifier="worker-A")
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        msg_lower = result.message.lower()
        assert "advisory" in msg_lower or "verifier" in msg_lower, (
            f"detail must mention 'advisory' or 'verifier'; got: {result.message!r}"
        )

    def test_receipt_with_verifier_equal_runner_after_whitespace_strip_fails(
        self, tmp_path: Path
    ) -> None:
        """Whitespace-padded verifier must not bypass the self-attestation rule.

        The model normalizes runner/verifier by stripping surrounding
        whitespace, so ``"worker-A"`` and ``"worker-A "`` collapse to
        the same identity — the gate must still FAIL.
        """
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict(runner="worker-A", verifier="worker-A   ")
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed

    def test_receipt_with_distinct_verifier_and_runner_passes(
        self, tmp_path: Path
    ) -> None:
        """Distinct verifier + runner + non-empty stdout + PASS must satisfy the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict(runner="worker-A", verifier="foreground-claude-X")
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed, result.message

    def test_receipt_missing_verifier_field_fails(self, tmp_path: Path) -> None:
        """Legacy receipt without ``verifier`` field must FAIL with 'verifier' in detail."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict()
        # Simulate a legacy / pre-OMN-9786 receipt
        del data["verifier"]
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "verifier" in result.message.lower(), (
            f"missing-verifier failure must mention 'verifier'; got: {result.message!r}"
        )


@pytest.mark.unit
class TestReceiptGateAdversarialProbeFields:
    """probe_command and probe_stdout completeness."""

    def test_receipt_missing_probe_command_field_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict()
        del data["probe_command"]
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "probe_command" in result.message.lower()

    def test_receipt_missing_probe_stdout_field_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict()
        del data["probe_stdout"]
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "probe_stdout" in result.message.lower()

    def test_receipt_with_empty_probe_stdout_for_executable_check_fails(
        self, tmp_path: Path
    ) -> None:
        """Executable check_type with empty probe_stdout must FAIL (cannot prove probe ran)."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict(probe_stdout="")
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert (
            "probe_stdout" in result.message.lower()
            or "stdout" in result.message.lower()
        )

    def test_receipt_with_whitespace_only_probe_command_fails(
        self, tmp_path: Path
    ) -> None:
        """probe_command must be non-empty after whitespace strip."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict()
        data["probe_command"] = "   "
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "probe_command" in result.message.lower()


@pytest.mark.unit
class TestReceiptGateAdvisoryDowngrade:
    """ADVISORY status must FAIL the gate — advisory-only is not merge-blocking proof."""

    def test_explicit_advisory_status_fails(self, tmp_path: Path) -> None:
        """Receipt with status=ADVISORY (no auto-downgrade) must FAIL the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        # PENDING is preserved by ModelDodReceipt; ADVISORY survives, FAIL stays.
        # Use distinct verifier/runner so the only weakness is ADVISORY status.
        data = _receipt_dict(status="ADVISORY", probe_stdout="ok")
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "advisory" in result.message.lower()

    def test_pending_status_fails(self, tmp_path: Path) -> None:
        """PENDING is allocated-but-not-executed; gate must FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        data = _receipt_dict(status="PENDING", probe_stdout="")
        _write_receipt_yaml(receipts, "OMN-9084", data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "pending" in result.message.lower()

    def test_file_exists_check_with_pass_status_downgrades_to_advisory_and_fails(
        self, tmp_path: Path
    ) -> None:
        """file_exists is structurally weak; PASS auto-downgrades to ADVISORY → gate FAILs."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084", check_type="file_exists")
        data = _receipt_dict(check_type="file_exists", probe_stdout="")
        # Receipt at file_exists.yaml not command.yaml
        p = receipts / "OMN-9084" / "dod-001" / "file_exists.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(data))

        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "advisory" in result.message.lower()
