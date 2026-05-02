# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Adversarial integration test — receipt-gate cascade proof (OMN-10423).

Simulates the 2026-04-30 incident pattern (24 PRs merging without evidence)
and validates all new attack surfaces identified by hostile review.

Wave 4 functions (parse_evidence_source, _verify_ticket_identity,
compute_contract_sha256, contract_sha256 field) are now enforced directly.

Categories:
    1. Cascade fixtures — original incident pattern (I1)
    2. Identity-binding fixtures — Findings 1, 2 (I2, I3)
    3. Hash-binding fixture — Finding 5 (I4)
    4. Skip-token fixtures — Findings 3, 4, 8 (I5, I10)
    5. Replay-determinism check — Finding 12 (I6)
    6. Gate invariants — one function per I1-I10
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.ticket.model_receipt_gate_result import (
    ModelReceiptGateResult,
)
from omnibase_core.validation.receipt_gate import (
    _CONTRACT_SHA256_REQUIRED_AFTER,
    validate_pr_receipts,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _future(days: int = 7) -> str:
    return (datetime.now(tz=UTC) + timedelta(days=days)).isoformat()


def _write_contract(
    contracts_dir: Path,
    ticket_id: str,
    *,
    check_type: str = "command",
    contract_ticket_id: str | None = None,
) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "ticket_id": contract_ticket_id or ticket_id,
        "schema_version": "1.0.0",
        "summary": f"Test contract for {ticket_id}",
        "dod_evidence": [
            {
                "id": "dod-001",
                "description": "integration check",
                "checks": [{"check_type": check_type, "check_value": "echo ok"}],
            }
        ],
    }
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _receipt_dict(
    *,
    ticket_id: str,
    runner: str = "worker-cascade",
    verifier: str = "foreground-claude-verifier",
    status: str = "PASS",
    probe_stdout: str = "ok\n",
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "echo ok",
        "status": status,
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": runner,
        "verifier": verifier,
        "probe_command": "echo ok",
        "probe_stdout": probe_stdout,
    }


def _write_receipt(receipts_dir: Path, ticket_id: str, data: dict[str, object]) -> Path:
    p = receipts_dir / ticket_id / "dod-001" / "command.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data))
    return p


def _write_allowlist(path: Path, entries: list[dict[object, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"approvals": entries}))


def _valid_allowlist_entry(
    *,
    entry_id: str = "appr-cascade-001",
    granted_by: str = "platform-lead",
    scope_repos: list[str] | None = None,
    scope_pr_numbers: list[int] | None = None,
    expires_at: str | None = None,
) -> dict[object, object]:
    return {
        "id": entry_id,
        "granted_by": granted_by,
        "granted_at": "2026-04-30T00:00:00+00:00",
        "expires_at": expires_at or _future(),
        "scope_repos": scope_repos or ["omnibase_core"],
        "scope_pr_numbers": scope_pr_numbers
        if scope_pr_numbers is not None
        else [9001],
    }


def _compute_contract_sha256(contract_path: Path) -> str:
    return f"sha256:{hashlib.sha256(contract_path.read_bytes()).hexdigest()}"


def _post_cutoff_opened_at() -> datetime:
    return _CONTRACT_SHA256_REQUIRED_AFTER + timedelta(days=1)


# ---------------------------------------------------------------------------
# Category 1 — Cascade fixtures (original incident pattern)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCascadeOriginalPattern:
    """5 fake code PRs touching different OMN-XXXX tickets, 0 OCC contracts.

    All must fail — this is the exact pattern that caused 24 PRs to merge
    on 2026-04-30 without evidence.
    """

    @pytest.mark.parametrize(
        ("ticket_id", "pr_body"),
        [
            ("OMN-10501", "feat(OMN-10501): wave-cascade PR 1\n\nCloses OMN-10501"),
            ("OMN-10502", "feat(OMN-10502): wave-cascade PR 2\n\nCloses OMN-10502"),
            ("OMN-10503", "fix(OMN-10503): wave-cascade PR 3\n\nCloses OMN-10503"),
            ("OMN-10504", "refactor(OMN-10504): wave-cascade PR 4\n\nCloses OMN-10504"),
            ("OMN-10505", "test(OMN-10505): wave-cascade PR 5\n\nCloses OMN-10505"),
        ],
    )
    def test_pr_without_contract_fails(
        self, tmp_path: Path, ticket_id: str, pr_body: str
    ) -> None:
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed, (
            f"Expected FAIL for {ticket_id} with no contract; got PASS: {result.message}"
        )
        assert (
            "contract" in result.message.lower() or "receipt" in result.message.lower()
        ), (
            f"Failure message must mention 'contract' or 'receipt'; got: {result.message!r}"
        )

    def test_all_five_cascade_prs_fail(self, tmp_path: Path) -> None:
        tickets = [
            ("OMN-10501", "Closes OMN-10501"),
            ("OMN-10502", "Closes OMN-10502"),
            ("OMN-10503", "Closes OMN-10503"),
            ("OMN-10504", "Closes OMN-10504"),
            ("OMN-10505", "Closes OMN-10505"),
        ]
        for ticket_id, pr_body in tickets:
            result = validate_pr_receipts(
                pr_body=pr_body,
                contracts_dir=tmp_path / "contracts",
                receipts_dir=tmp_path / "receipts",
            )
            assert not result.passed, (
                f"Cascade PR for {ticket_id} must FAIL without a contract"
            )

    def test_pr_with_contract_but_empty_receipts_dir_fails(
        self, tmp_path: Path
    ) -> None:
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-10501")
        (tmp_path / "receipts").mkdir(parents=True, exist_ok=True)

        result = validate_pr_receipts(
            pr_body="Closes OMN-10501",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no receipt" in result.message.lower(), (
            f"Expected 'no receipt' in message; got: {result.message!r}"
        )


# ---------------------------------------------------------------------------
# Category 2 — Identity-binding fixtures (Findings 1, 2)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIdentityBinding:
    """Evidence-Source / ticket identity mismatches must fail the gate."""

    def test_contract_exists_for_different_ticket_fails(self, tmp_path: Path) -> None:
        """Contract exists for OMN-10600 but PR cites OMN-10601 — identity mismatch."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10600")
        _write_receipt(receipts, "OMN-10600", _receipt_dict(ticket_id="OMN-10600"))

        result = validate_pr_receipts(
            pr_body="Closes OMN-10601",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed, (
            "Gate must fail when contract exists for a different ticket than cited in PR"
        )
        assert "contract" in result.message.lower() or "OMN-10601" in result.message, (
            f"Must mention missing contract for OMN-10601; got: {result.message!r}"
        )

    def test_contract_present_but_receipts_dir_empty_fails(
        self, tmp_path: Path
    ) -> None:
        """Contract present but no receipts directory → sham contract."""
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-10602")

        result = validate_pr_receipts(
            pr_body="Closes OMN-10602",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no receipt" in result.message.lower(), (
            f"Expected 'no receipt'; got: {result.message!r}"
        )

    def test_contract_ticket_id_mismatches_pr_title_fails(self, tmp_path: Path) -> None:
        """Contract YAML ticket_id field is OMN-10603, PR cites OMN-10604 → fail."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        # Write a contract file named OMN-10604.yaml but with wrong ticket_id inside
        contracts.mkdir(parents=True, exist_ok=True)
        body = {
            "ticket_id": "OMN-10603",  # mismatch with filename OMN-10604
            "schema_version": "1.0.0",
            "summary": "mismatched ticket_id",
            "dod_evidence": [
                {
                    "id": "dod-001",
                    "description": "check",
                    "checks": [{"check_type": "command", "check_value": "echo ok"}],
                }
            ],
        }
        (contracts / "OMN-10604.yaml").write_text(yaml.safe_dump(body))

        # Write a receipt with wrong ticket_id (matching what the contract declares)
        receipt = _receipt_dict(ticket_id="OMN-10603")
        _write_receipt(receipts, "OMN-10604", receipt)

        result = validate_pr_receipts(
            pr_body="Closes OMN-10604",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        # The receipt path is under OMN-10604/ but declares ticket_id=OMN-10603 → mismatch
        assert not result.passed, (
            f"Gate must fail when receipt ticket_id mismatches lookup ticket; got: {result.message!r}"
        )
        assert "OMN-10603" in result.message or "OMN-10604" in result.message

    def test_evidence_ticket_missing_fails(self, tmp_path: Path) -> None:
        """PR body has no OMN-XXXX citation at all → gate must fail."""
        result = validate_pr_receipts(
            pr_body="This PR has no ticket reference whatsoever.",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "ticket" in result.message.lower() or "OMN" in result.message, (
            f"Must mention missing ticket; got: {result.message!r}"
        )

    def test_receipt_ticket_id_mismatches_expected_fails(self, tmp_path: Path) -> None:
        """Receipt on disk declares wrong ticket_id — path/content mismatch."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10605")
        # Write receipt with wrong ticket_id inside the YAML
        wrong_receipt = _receipt_dict(ticket_id="OMN-99999")
        _write_receipt(receipts, "OMN-10605", wrong_receipt)

        result = validate_pr_receipts(
            pr_body="Closes OMN-10605",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "OMN-99999" in result.message or "OMN-10605" in result.message


# ---------------------------------------------------------------------------
# Category 3 — Hash-binding fixture (Finding 5 / invariant I4)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHashBinding:
    """Contract YAML mutated after receipt produced → contract_sha256 mismatch → fail.

    The contract_sha256 field on ModelDodReceipt and gate-side hash verification
    landed via OMN-10421. These tests assert the final invariant directly.
    """

    def test_missing_contract_sha256_post_cutoff_fails(self, tmp_path: Path) -> None:
        """Post-cutoff receipts without contract_sha256 fail hard."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10700")
        _write_receipt(receipts, "OMN-10700", _receipt_dict(ticket_id="OMN-10700"))

        result = validate_pr_receipts(
            pr_body="Closes OMN-10700",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_post_cutoff_opened_at(),
        )
        assert not result.passed
        assert "contract_sha256" in result.message.lower() or "rerun probes" in (
            result.message.lower()
        )

    def test_mutated_contract_invalidates_receipt(self, tmp_path: Path) -> None:
        """Mutating contract YAML after receipt creation causes hash-mismatch fail."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10702")
        contract_path = contracts / "OMN-10702.yaml"

        receipt_data = _receipt_dict(ticket_id="OMN-10702")
        receipt_data["contract_sha256"] = _compute_contract_sha256(contract_path)
        _write_receipt(receipts, "OMN-10702", receipt_data)

        # Mutate contract after receipt — the stored hash must no longer match.
        original_content = yaml.safe_load(contract_path.read_text())
        original_content["summary"] = "MUTATED after receipt — should invalidate"
        contract_path.write_text(yaml.safe_dump(original_content))

        result = validate_pr_receipts(
            pr_body="Closes OMN-10702",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_post_cutoff_opened_at(),
        )
        assert not result.passed, (
            "Gate must fail when contract was mutated after receipt was produced"
        )
        assert (
            "sha256" in result.message.lower()
            or "hash" in result.message.lower()
            or "mutated" in result.message.lower()
        ), f"Must mention hash mismatch; got: {result.message!r}"

    def test_matching_contract_sha256_passes(self, tmp_path: Path) -> None:
        """Receipt with correct contract_sha256 satisfies the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10703")
        contract_path = contracts / "OMN-10703.yaml"

        sha = _compute_contract_sha256(contract_path)
        receipt_data = _receipt_dict(ticket_id="OMN-10703")
        receipt_data["contract_sha256"] = sha
        _write_receipt(receipts, "OMN-10703", receipt_data)

        result = validate_pr_receipts(
            pr_body="Closes OMN-10703",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_post_cutoff_opened_at(),
        )
        assert result.passed, f"Matching sha256 must pass; got: {result.message!r}"


# ---------------------------------------------------------------------------
# Category 4 — Skip-token fixtures (Findings 3, 4, 8)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSkipTokenAdversarial:
    """Adversarial skip-token scenarios from hostile review."""

    def test_skip_token_self_approved_fails(self, tmp_path: Path) -> None:
        """granted_by == PR author → self-approval rejected."""
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [
                _valid_allowlist_entry(
                    entry_id="appr-self-cascade",
                    granted_by="jonahgabriel",
                    scope_pr_numbers=[9001],
                )
            ],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-self-cascade]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="jonahgabriel",
            current_repo="omnibase_core",
            current_pr_number=9001,
        )
        assert not result.passed
        assert (
            "self" in result.message.lower()
            or "self-approval" in result.message.lower()
            or "jonahgabriel" in result.message
        ), f"Must cite self-approval rejection; got: {result.message!r}"

    def test_skip_token_missing_scope_pr_numbers_fails(self, tmp_path: Path) -> None:
        """Allowlist entry missing scope_pr_numbers → hard fail."""
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        entry: dict[object, object] = {
            "id": "appr-no-scope-prs",
            "granted_by": "platform-lead",
            "granted_at": "2026-04-30T00:00:00+00:00",
            "expires_at": _future(),
            "scope_repos": ["omnibase_core"],
            # scope_pr_numbers intentionally omitted
        }
        _write_allowlist(allowlist, [entry])

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-no-scope-prs]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="worker-A",
            current_repo="omnibase_core",
            current_pr_number=9001,
        )
        assert not result.passed
        assert "scope_pr_numbers" in result.message, (
            f"Must cite missing scope_pr_numbers; got: {result.message!r}"
        )

    def test_merge_group_head_sha_matching_multiple_prs_fails(
        self, tmp_path: Path
    ) -> None:
        """merge_group head_sha resolving to 2+ PRs → exactly-one-PR violation.

        This test validates the invariant I10 gate behavior. Because the
        gate library (receipt_gate.py) doesn't directly resolve PRs via
        gh CLI — that lives in the GHA workflow — we simulate this at the
        gate result level: if the caller cannot resolve exactly one PR,
        it must pass a sentinel that triggers a FAIL.

        The gate enforces this by rejecting a PR body that contains a
        merge-group-ambiguity marker. This test documents the expected
        behavior contract so the GHA caller knows the failure surface.
        """
        # When head_sha resolves to 0 or 2+ PRs, the GHA caller fails before
        # invoking the Python gate. We verify the gate itself fails fast when
        # given a PR body with no valid ticket AND no valid skip token —
        # the cascading ambiguity must never produce a silent PASS.
        result = validate_pr_receipts(
            pr_body="merge_group event: head_sha abc123 resolved to 2 PRs",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed, (
            "Gate must fail when no valid ticket or skip token is present "
            "(simulates merge_group ambiguity producing no usable PR body)"
        )

    def test_free_text_skip_token_fails(self, tmp_path: Path) -> None:
        """Free-text [skip-receipt-gate: ...] with spaces → OVERRIDE_PATTERN won't match."""
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: this is a free text justification]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "skip-*" in result.message or "allowlist" in result.message.lower()

    def test_skip_token_no_allowlist_path_fails(self, tmp_path: Path) -> None:
        """Valid-looking token but no allowlist_path provided → hard fail."""
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-cascade-001]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=None,
        )
        assert not result.passed
        assert "allowlist" in result.message.lower()

    def test_skip_token_valid_with_platform_lead_approval_passes(
        self, tmp_path: Path
    ) -> None:
        """Properly approved skip token with external approver → PASS with friction."""
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [
                _valid_allowlist_entry(
                    entry_id="appr-platform-approved",
                    granted_by="platform-lead",
                    scope_repos=["omnibase_core"],
                    scope_pr_numbers=[9001],
                )
            ],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-platform-approved]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="worker-A",
            current_repo="omnibase_core",
            current_pr_number=9001,
        )
        assert result.passed, f"Valid token must pass; got: {result.message!r}"
        assert result.friction_logged, "Bypass must set friction_logged=True"
        assert "appr-platform-approved" in result.message


# ---------------------------------------------------------------------------
# Category 5 — Replay-determinism check (Finding 12 / invariant I6)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestReplayDeterminism:
    """Each fixture executed twice with identical inputs must yield identical outcome + message."""

    def _run_twice(
        self,
        pr_body: str,
        contracts_dir: Path,
        receipts_dir: Path,
        allowlist_path: Path | None = None,
        pr_author: str | None = None,
        current_repo: str | None = None,
        current_pr_number: int | None = None,
    ) -> tuple[ModelReceiptGateResult, ModelReceiptGateResult]:
        r1 = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
            allowlist_path=allowlist_path,
            pr_author=pr_author,
            current_repo=current_repo,
            current_pr_number=current_pr_number,
        )
        r2 = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
            allowlist_path=allowlist_path,
            pr_author=pr_author,
            current_repo=current_repo,
            current_pr_number=current_pr_number,
        )
        return r1, r2

    def test_cascade_failure_is_deterministic(self, tmp_path: Path) -> None:
        """Category 1 fixture replayed twice → identical FAIL + identical message."""
        r1, r2 = self._run_twice(
            pr_body="Closes OMN-10501",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert r1.passed == r2.passed
        assert not r1.passed
        assert r1.message == r2.message

    def test_identity_mismatch_is_deterministic(self, tmp_path: Path) -> None:
        """Category 2 fixture replayed twice → identical FAIL + identical message."""
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-10600")

        r1, r2 = self._run_twice(
            pr_body="Closes OMN-10601",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert r1.passed == r2.passed
        assert not r1.passed
        assert r1.message == r2.message

    def test_self_approved_token_is_deterministic(self, tmp_path: Path) -> None:
        """Category 4 self-approval fixture replayed twice → identical FAIL + identical message."""
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [
                _valid_allowlist_entry(
                    entry_id="appr-self-det",
                    granted_by="jonahgabriel",
                    scope_pr_numbers=[9001],
                )
            ],
        )

        r1, r2 = self._run_twice(
            pr_body="[skip-receipt-gate: appr-self-det]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="jonahgabriel",
            current_repo="omnibase_core",
            current_pr_number=9001,
        )
        assert r1.passed == r2.passed
        assert not r1.passed
        assert r1.message == r2.message

    def test_missing_scope_pr_numbers_is_deterministic(self, tmp_path: Path) -> None:
        """Missing scope_pr_numbers fixture replayed twice → identical FAIL."""
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        entry: dict[object, object] = {
            "id": "appr-det-no-scope",
            "granted_by": "platform-lead",
            "granted_at": "2026-04-30T00:00:00+00:00",
            "expires_at": _future(),
            "scope_repos": ["omnibase_core"],
        }
        _write_allowlist(allowlist, [entry])

        r1, r2 = self._run_twice(
            pr_body="[skip-receipt-gate: appr-det-no-scope]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="worker-A",
            current_repo="omnibase_core",
            current_pr_number=9001,
        )
        assert r1.passed == r2.passed
        assert not r1.passed
        assert r1.message == r2.message

    def test_pass_receipt_is_deterministic(self, tmp_path: Path) -> None:
        """Valid contract + receipt replayed twice → identical PASS + identical message."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10800")
        _write_receipt(receipts, "OMN-10800", _receipt_dict(ticket_id="OMN-10800"))

        r1, r2 = self._run_twice(
            pr_body="Closes OMN-10800",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert r1.passed == r2.passed
        assert r1.passed
        assert r1.message == r2.message


# ---------------------------------------------------------------------------
# Category 6 — Gate invariants (one function per I1-I10)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGateInvariants:
    """One named test per formal invariant I1-I10."""

    def test_invariant_i1_no_merge_without_evidence(self, tmp_path: Path) -> None:
        """I1: No PR merges without contract + PASS receipt."""
        result = validate_pr_receipts(
            pr_body="Closes OMN-10901",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed, "I1: Gate must block when no evidence exists"

    def test_invariant_i2_evidence_pinned_to_occ_commit(self, tmp_path: Path) -> None:
        """I2: Evidence must be pinned to a specific OCC commit-ish.

        Validated by confirming gate does not silently accept a PR body
        that opts into Evidence-Source without the matching Evidence-Ticket identity.
        """
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10902")
        _write_receipt(receipts, "OMN-10902", _receipt_dict(ticket_id="OMN-10902"))

        result = validate_pr_receipts(
            pr_body=(
                "feat(OMN-10902): some change\n\n"
                "Closes OMN-10902\n"
                "Evidence-Source: OCC#616"
            ),
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed, (
            "I2: Gate must block Evidence-Source without matching Evidence-Ticket"
        )
        assert "Evidence-Ticket" in result.message

    def test_invariant_i3_evidence_corresponds_to_same_ticket(
        self, tmp_path: Path
    ) -> None:
        """I3: Evidence must correspond to the same ticket as the PR."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10903")
        _write_receipt(receipts, "OMN-10903", _receipt_dict(ticket_id="OMN-10903"))

        result_different_ticket = validate_pr_receipts(
            pr_body="Closes OMN-10904",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result_different_ticket.passed, (
            "I3: Gate must fail when evidence is for a different ticket than the PR cites"
        )

        result_correct_ticket = validate_pr_receipts(
            pr_body="Closes OMN-10903",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result_correct_ticket.passed, (
            f"I3: Gate must pass when evidence matches the cited ticket; got: {result_correct_ticket.message!r}"
        )

    def test_invariant_i4_evidence_content_hash_bound(self, tmp_path: Path) -> None:
        """I4: Evidence content is hash-bound; mutating contract invalidates receipt."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10904")
        contract_path = contracts / "OMN-10904.yaml"

        receipt_data = _receipt_dict(ticket_id="OMN-10904")
        receipt_data["contract_sha256"] = _compute_contract_sha256(contract_path)
        _write_receipt(receipts, "OMN-10904", receipt_data)

        # Mutate contract after receipt produced
        original_content = yaml.safe_load(contract_path.read_text())
        original_content["summary"] = "mutated post-receipt"
        contract_path.write_text(yaml.safe_dump(original_content))

        result = validate_pr_receipts(
            pr_body="Closes OMN-10904",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_opened_at=_post_cutoff_opened_at(),
        )
        assert not result.passed, "I4: Mutated contract must invalidate receipt"
        assert "sha256" in result.message.lower() or "hash" in result.message.lower(), (
            f"I4: Must mention hash mismatch; got: {result.message!r}"
        )

    def test_invariant_i5_skip_tokens_externally_approved(self, tmp_path: Path) -> None:
        """I5: Skip tokens must be externally approved, scoped, non-self-issued."""
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [
                _valid_allowlist_entry(
                    entry_id="appr-i5-test",
                    granted_by="the-pr-author",
                    scope_pr_numbers=[1000],
                )
            ],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-i5-test]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="the-pr-author",
            current_repo="omnibase_core",
            current_pr_number=1000,
        )
        assert not result.passed, "I5: Self-issued approval must be rejected"

    def test_invariant_i6_gate_deterministic_under_replay(self, tmp_path: Path) -> None:
        """I6: Gate is deterministic under replay (no time/network beyond fetch)."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10905")
        _write_receipt(receipts, "OMN-10905", _receipt_dict(ticket_id="OMN-10905"))

        results = [
            validate_pr_receipts(
                pr_body="Closes OMN-10905",
                contracts_dir=contracts,
                receipts_dir=receipts,
            )
            for _ in range(3)
        ]
        assert all(r.passed == results[0].passed for r in results), (
            "I6: passed must be identical across all replays"
        )
        assert all(r.message == results[0].message for r in results), (
            "I6: message must be identical across all replays"
        )

    def test_invariant_i7_retroactive_evidence_requires_correct_receipt(
        self, tmp_path: Path
    ) -> None:
        """I7: Retroactive evidence pushed to OCC main does not satisfy prior PRs.

        The gate checks receipts at the path corresponding to the cited ticket.
        A retroactively added contract without a paired receipt must still fail.
        """
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-10906")
        # No receipt — simulates retroactive contract push without proof

        result = validate_pr_receipts(
            pr_body="Closes OMN-10906",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed, (
            "I7: Contract without receipt must fail even if added retroactively"
        )

    def test_invariant_i8_occ_fetch_failure_is_hard_fail(self, tmp_path: Path) -> None:
        """I8: OCC fetch failure → hard fail, never silent fallback.

        The Python gate surface: when contracts_dir does not exist (simulates
        OCC checkout failure), the gate must hard-fail, not silently pass.
        """
        result = validate_pr_receipts(
            pr_body="Closes OMN-10907",
            contracts_dir=tmp_path / "nonexistent" / "contracts",
            receipts_dir=tmp_path / "nonexistent" / "receipts",
        )
        assert not result.passed, (
            "I8: Missing contracts dir (OCC fetch failure) must hard-fail"
        )

    def test_invariant_i9_merge_group_reevaluates_fully(self, tmp_path: Path) -> None:
        """I9: merge_group entry re-evaluates fully (no cached PASS reuse).

        The Python gate is stateless — each call to validate_pr_receipts
        reads from disk fresh. This test confirms that invalidating the
        receipt between two calls causes the second call to fail, proving
        no in-process cache is maintained.
        """
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10908")
        _write_receipt(receipts, "OMN-10908", _receipt_dict(ticket_id="OMN-10908"))

        first_result = validate_pr_receipts(
            pr_body="Closes OMN-10908",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert first_result.passed, (
            f"First eval must pass; got: {first_result.message!r}"
        )

        # Simulate cached PASS reuse attempt: remove receipt between calls
        receipt_path = receipts / "OMN-10908" / "dod-001" / "command.yaml"
        receipt_path.unlink()

        second_result = validate_pr_receipts(
            pr_body="Closes OMN-10908",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not second_result.passed, (
            "I9: Gate must re-evaluate fully; removing receipt between calls must cause FAIL"
        )

    def test_invariant_i10_skip_token_pr_resolution_exactly_one(
        self, tmp_path: Path
    ) -> None:
        """I10: Skip-token PR resolution returns exactly-one-PR or gate fails.

        The GHA workflow layer enforces exactly-one-PR resolution for merge_group.
        At the Python gate level, we verify that a skip token requires full
        PR context (pr_author, current_repo, current_pr_number) — missing any
        context fails, ensuring the caller cannot present ambiguous inputs.
        """
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [_valid_allowlist_entry(entry_id="appr-i10-test", scope_pr_numbers=[9001])],
        )

        # Simulate merge_group confusion: no current_pr_number provided
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-i10-test]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="worker-A",
            current_repo="omnibase_core",
            current_pr_number=None,  # simulates 0 or 2+ PRs → cannot resolve to one
        )
        assert not result.passed, (
            "I10: Gate must fail when PR number cannot be resolved to exactly one"
        )
        assert "current_pr_number" in result.message, (
            f"I10: Must cite missing pr_number context; got: {result.message!r}"
        )
