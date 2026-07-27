# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for validator_receipt_diff_consistency — attestation-vs-diff gate (OMN-13927).

The receipt-honesty gate (rules A-E) is pure per-receipt and cannot catch a
receipt that lies about its own PR diff. This gate closes that class. Golden
fixtures reproduce the OMN-13917 incident: a receipt attesting net-new-only while
its diff modified a merged contract + four merged receipts (must-FAIL), and a true
net-new-only PR whose diff is all-add (must-PASS).

Covers: both trigger paths (structured `diff_attestations` + legacy free-text
regexes), all three attestation predicates, the no-claim no-op, rename/copy status
normalization, and the CLI.
"""

from __future__ import annotations

from datetime import UTC, datetime

from omnibase_core.enums.ticket.enum_diff_attestation import EnumDiffAttestation
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.validation.validator_receipt_diff_consistency import (
    check_diff_consistency,
    main,
    parse_name_status,
    scan_receipt_files_with_diff,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_receipt(**overrides: object) -> ModelDodReceipt:
    """A valid PASS receipt that makes no diff claim unless overridden.

    ``check_type`` is a non-executable, non-weak type so no adversarial downgrade
    fires and the status stays PASS without a probe_stdout obligation.
    """
    base: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-13501",
        "evidence_item_id": "dod-self-binding",
        "check_type": "attestation",
        "check_value": "net-new-only self-binding receipt",
        "status": EnumReceiptStatus.PASS,
        "run_timestamp": datetime.now(tz=UTC),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "codex-worker",
        "verifier": "foreground-claude",
        "probe_command": "git diff --name-status origin/dev...HEAD",
        "probe_stdout": "A\tcontracts/OMN-13501.yaml",
    }
    base.update(overrides)
    return ModelDodReceipt.model_validate(base)


# The #3551 free-text claim, verbatim to the OMN-13917 incident.
_INCIDENT_CLAIM = (
    "No existing receipts or the OMN-13501 contract are modified "
    "(OMN-13888 net-new-only)."
)

# The #3551 diff: one modified contract + four modified merged receipts.
_INCIDENT_DIFF: list[tuple[str, str]] = [
    ("M", "contracts/OMN-13501.yaml"),
    ("M", "drift/dod_receipts/OMN-13501/dod-a/command.yaml"),
    ("M", "drift/dod_receipts/OMN-13501/dod-b/command.yaml"),
    ("M", "drift/dod_receipts/OMN-13501/dod-c/command.yaml"),
    ("M", "drift/dod_receipts/OMN-13501/dod-d/command.yaml"),
    ("A", "drift/dod_receipts/OMN-13501/dod-self-binding/command.yaml"),
]

# A true net-new-only diff (#3548-style): only adds.
_NET_NEW_DIFF: list[tuple[str, str]] = [
    ("A", "contracts/OMN-13501.yaml"),
    ("A", "drift/dod_receipts/OMN-13501/dod-self-binding/command.yaml"),
]


# ---------------------------------------------------------------------------
# Golden regression: the OMN-13917 / #3551 incident
# ---------------------------------------------------------------------------


class TestIncidentGolden:
    def test_3551_freetext_claim_against_mutating_diff_FAILS(self) -> None:
        """#3551: free-text net-new-only claim + a diff that modifies pre-existing files."""
        receipt = _make_receipt(actual_output=_INCIDENT_CLAIM)
        violations = check_diff_consistency(receipt, _INCIDENT_DIFF)
        assert len(violations) == 1
        v = violations[0]
        assert v.attestation is EnumDiffAttestation.NET_NEW_ONLY
        assert "contracts/OMN-13501.yaml" in v.detail
        # All four modified receipts are named.
        assert v.detail.count("drift/dod_receipts/OMN-13501/") == 4

    def test_3548_net_new_only_diff_PASSES(self) -> None:
        """#3548: identical claim, but the diff is genuinely all-add."""
        receipt = _make_receipt(actual_output=_INCIDENT_CLAIM)
        assert check_diff_consistency(receipt, _NET_NEW_DIFF) == []


# ---------------------------------------------------------------------------
# Trigger paths
# ---------------------------------------------------------------------------


class TestTriggerPaths:
    def test_structured_attestation_FAILS_on_mutation(self) -> None:
        receipt = _make_receipt(
            actual_output="clean run",
            diff_attestations=[EnumDiffAttestation.NET_NEW_ONLY],
        )
        violations = check_diff_consistency(receipt, _INCIDENT_DIFF)
        assert [v.attestation for v in violations] == [EnumDiffAttestation.NET_NEW_ONLY]

    def test_no_claim_receipt_is_noop(self) -> None:
        """A receipt with neither structured nor free-text claim is exempt."""
        receipt = _make_receipt(actual_output="42 passed in 1.23s")
        assert check_diff_consistency(receipt, _INCIDENT_DIFF) == []

    def test_none_actual_output_is_noop(self) -> None:
        receipt = _make_receipt(actual_output=None)
        assert check_diff_consistency(receipt, _INCIDENT_DIFF) == []

    def test_bare_net_new_only_phrase_triggers(self) -> None:
        receipt = _make_receipt(actual_output="This PR is net-new-only.")
        violations = check_diff_consistency(receipt, _INCIDENT_DIFF)
        assert [v.attestation for v in violations] == [EnumDiffAttestation.NET_NEW_ONLY]

    def test_structured_and_freetext_union_not_double_counted(self) -> None:
        """Both triggers imply NET_NEW_ONLY; it is enforced once, not twice."""
        receipt = _make_receipt(
            actual_output=_INCIDENT_CLAIM,
            diff_attestations=[EnumDiffAttestation.NET_NEW_ONLY],
        )
        violations = check_diff_consistency(receipt, _INCIDENT_DIFF)
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# Per-attestation predicates
# ---------------------------------------------------------------------------


class TestReceiptsUnmodified:
    def test_fails_on_modified_receipt(self) -> None:
        receipt = _make_receipt(
            actual_output="x",
            diff_attestations=[EnumDiffAttestation.RECEIPTS_UNMODIFIED],
        )
        violations = check_diff_consistency(receipt, _INCIDENT_DIFF)
        assert [v.attestation for v in violations] == [
            EnumDiffAttestation.RECEIPTS_UNMODIFIED
        ]

    def test_passes_when_only_adds_under_receipts(self) -> None:
        receipt = _make_receipt(
            actual_output="x",
            diff_attestations=[EnumDiffAttestation.RECEIPTS_UNMODIFIED],
        )
        # A modified contract does NOT violate RECEIPTS_UNMODIFIED.
        diff = [
            ("A", "drift/dod_receipts/OMN-13501/dod-x/command.yaml"),
            ("M", "contracts/OMN-13501.yaml"),
        ]
        assert check_diff_consistency(receipt, diff) == []


class TestContractUnmodified:
    def test_fails_on_modified_own_contract(self) -> None:
        receipt = _make_receipt(
            actual_output="x",
            diff_attestations=[EnumDiffAttestation.CONTRACT_UNMODIFIED],
        )
        violations = check_diff_consistency(receipt, _INCIDENT_DIFF)
        assert [v.attestation for v in violations] == [
            EnumDiffAttestation.CONTRACT_UNMODIFIED
        ]

    def test_passes_when_contract_absent(self) -> None:
        receipt = _make_receipt(
            actual_output="x",
            diff_attestations=[EnumDiffAttestation.CONTRACT_UNMODIFIED],
        )
        diff = [("M", "drift/dod_receipts/OMN-13501/dod-a/command.yaml")]
        assert check_diff_consistency(receipt, diff) == []

    def test_explicit_ticket_id_override_targets_other_contract(self) -> None:
        receipt = _make_receipt(
            actual_output="x",
            diff_attestations=[EnumDiffAttestation.CONTRACT_UNMODIFIED],
        )
        diff = [("M", "contracts/OMN-99999.yaml")]
        # Default (receipt.ticket_id == OMN-13501) does not fire.
        assert check_diff_consistency(receipt, diff) == []
        # Explicit override targeting OMN-99999 fires.
        violations = check_diff_consistency(receipt, diff, ticket_id="OMN-99999")
        assert [v.attestation for v in violations] == [
            EnumDiffAttestation.CONTRACT_UNMODIFIED
        ]


class TestStatusNormalization:
    def test_rename_score_counts_as_mutation(self) -> None:
        receipt = _make_receipt(actual_output=_INCIDENT_CLAIM)
        diff = [("R100", "drift/dod_receipts/OMN-13501/dod-a/command.yaml")]
        violations = check_diff_consistency(receipt, diff)
        assert [v.attestation for v in violations] == [EnumDiffAttestation.NET_NEW_ONLY]

    def test_unrelated_paths_ignored(self) -> None:
        receipt = _make_receipt(actual_output=_INCIDENT_CLAIM)
        diff = [("M", "src/omnibase_core/foo.py"), ("M", "README.md")]
        assert check_diff_consistency(receipt, diff) == []


# ---------------------------------------------------------------------------
# name-status parsing
# ---------------------------------------------------------------------------


class TestParseNameStatus:
    def test_parses_add_and_modify(self) -> None:
        text = "A\tcontracts/OMN-1.yaml\nM\tdrift/dod_receipts/OMN-1/x/command.yaml\n"
        assert parse_name_status(text) == [
            ("A", "contracts/OMN-1.yaml"),
            ("M", "drift/dod_receipts/OMN-1/x/command.yaml"),
        ]

    def test_rename_takes_destination_path(self) -> None:
        text = "R100\tcontracts/old.yaml\tcontracts/OMN-1.yaml\n"
        assert parse_name_status(text) == [("R100", "contracts/OMN-1.yaml")]

    def test_blank_and_malformed_lines_skipped(self) -> None:
        text = "\nA\tcontracts/OMN-1.yaml\ngarbage-no-tab\n"
        assert parse_name_status(text) == [("A", "contracts/OMN-1.yaml")]


# ---------------------------------------------------------------------------
# File scanning + CLI
# ---------------------------------------------------------------------------


def _write_receipt(tmp_path, actual_output: str):  # type: ignore[no-untyped-def]
    import yaml

    receipt_dir = tmp_path / "drift" / "dod_receipts" / "OMN-13501" / "dod-self-binding"
    receipt_dir.mkdir(parents=True)
    receipt_path = receipt_dir / "command.yaml"
    payload = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-13501",
        "evidence_item_id": "dod-self-binding",
        "check_type": "attestation",
        "check_value": "net-new-only self-binding receipt",
        "status": "PASS",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "codex-worker",
        "verifier": "foreground-claude",
        "probe_command": "git diff",
        "probe_stdout": "output",
        "actual_output": actual_output,
    }
    receipt_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return receipt_path


class TestScanAndCli:
    def test_scan_flags_lying_receipt(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        receipt_path = _write_receipt(tmp_path, _INCIDENT_CLAIM)
        findings = scan_receipt_files_with_diff([receipt_path], _INCIDENT_DIFF)
        assert len(findings) == 1
        assert findings[0].receipt_path == receipt_path
        assert findings[0].violations[0].receipt_path == receipt_path

    def test_scan_clean_receipt_no_finding(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        receipt_path = _write_receipt(tmp_path, _INCIDENT_CLAIM)
        findings = scan_receipt_files_with_diff([receipt_path], _NET_NEW_DIFF)
        assert findings == []

    def test_cli_fails_on_lying_receipt(self, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
        receipt_path = _write_receipt(tmp_path, _INCIDENT_CLAIM)
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text(
            "".join(f"{code}\t{path}\n" for code, path in _INCIDENT_DIFF),
            encoding="utf-8",
        )
        rc = main(["--diff-file", str(diff_file), str(receipt_path)])
        assert rc == 1
        assert "FAILED" in capsys.readouterr().out

    def test_cli_passes_on_clean_diff(self, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
        receipt_path = _write_receipt(tmp_path, _INCIDENT_CLAIM)
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text(
            "".join(f"{code}\t{path}\n" for code, path in _NET_NEW_DIFF),
            encoding="utf-8",
        )
        rc = main(["--diff-file", str(diff_file), str(receipt_path)])
        assert rc == 0
        assert "PASSED" in capsys.readouterr().out

    def test_cli_no_receipts_passes(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("M\tcontracts/OMN-13501.yaml\n", encoding="utf-8")
        assert main(["--diff-file", str(diff_file)]) == 0

    def test_cli_missing_diff_file_errors(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        assert main(["--diff-file", str(tmp_path / "nope.txt")]) == 1
