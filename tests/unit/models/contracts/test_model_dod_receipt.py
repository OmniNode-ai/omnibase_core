# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDodReceipt — the receipt-gate proof artifact."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt


def _base_fields() -> dict[str, Any]:
    """Return a baseline kwargs dict for a valid PASS receipt.

    Independent verifier and runner identities and a non-empty
    ``probe_stdout`` keep this fixture out of the ADVISORY downgrade paths
    so callers that only test unrelated invariants (e.g. ticket_id format)
    see PASS as the resulting status.
    """
    return {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-9084",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "gh pr view --json state -q .state",
        "status": EnumReceiptStatus.PASS,
        "run_timestamp": datetime.now(tz=UTC),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "ci-receipt-gate",
        "verifier": "foreground-receipt-gate-2026-04-26",
        "probe_command": "gh pr view --json state -q .state",
        "probe_stdout": "OPEN\n",
    }


@pytest.mark.unit
class TestModelDodReceiptConstruction:
    def test_minimum_valid_receipt_constructs(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        assert receipt.ticket_id == "OMN-9084"
        assert receipt.status is EnumReceiptStatus.PASS
        assert receipt.actual_output is None
        assert receipt.exit_code is None

    def test_full_receipt_with_all_fields(self) -> None:
        fields = _base_fields()
        fields.update(
            actual_output="OPEN",
            exit_code=0,
            duration_ms=123,
            pr_number=1349,
        )
        receipt = ModelDodReceipt(**fields)
        assert receipt.actual_output == "OPEN"
        assert receipt.exit_code == 0
        assert receipt.duration_ms == 123
        assert receipt.pr_number == 1349

    def test_receipt_is_frozen(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        with pytest.raises(ValidationError):
            receipt.status = EnumReceiptStatus.FAIL  # type: ignore[misc]

    def test_receipt_rejects_extra_fields(self) -> None:
        fields = _base_fields()
        fields["rogue_field"] = "not allowed"
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptTicketIdValidator:
    def test_valid_ticket_id_passes(self) -> None:
        ModelDodReceipt(**_base_fields())

    @pytest.mark.parametrize(
        "bad_id",
        ["OMN-", "omn-9084", "9084", "OMN-abc", "OMN9084", "", "PROJ-1"],
    )
    def test_invalid_ticket_id_rejected(self, bad_id: str) -> None:
        fields = _base_fields()
        fields["ticket_id"] = bad_id
        with pytest.raises(ValidationError, match="ticket_id"):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptCommitShaValidator:
    def test_valid_sha_short_passes(self) -> None:
        fields = _base_fields()
        fields["commit_sha"] = "a1b2c3d"
        ModelDodReceipt(**fields)

    def test_valid_sha_full_passes(self) -> None:
        fields = _base_fields()
        fields["commit_sha"] = "a" * 40
        ModelDodReceipt(**fields)

    @pytest.mark.parametrize(
        "bad_sha",
        ["a1b2c3", "zzzzzzz", "A1B2C3D", "a" * 41, "", "not-a-sha"],
    )
    def test_invalid_sha_rejected(self, bad_sha: str) -> None:
        fields = _base_fields()
        fields["commit_sha"] = bad_sha
        with pytest.raises(ValidationError, match="commit_sha"):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptTimestampValidator:
    def test_naive_datetime_rejected(self) -> None:
        fields = _base_fields()
        fields["run_timestamp"] = datetime(2026, 4, 17, 20, 0, 0)  # no tz
        with pytest.raises(ValidationError, match="timezone-aware"):
            ModelDodReceipt(**fields)

    def test_non_utc_tz_normalized_to_utc(self) -> None:
        from datetime import timezone

        eastern = timezone(timedelta(hours=-5))
        fields = _base_fields()
        fields["run_timestamp"] = datetime(2026, 4, 17, 15, 0, 0, tzinfo=eastern)
        receipt = ModelDodReceipt(**fields)
        assert receipt.run_timestamp.tzinfo is UTC
        assert receipt.run_timestamp.hour == 20  # 15 EST → 20 UTC


@pytest.mark.unit
class TestModelDodReceiptDurationValidator:
    def test_negative_duration_rejected(self) -> None:
        fields = _base_fields()
        fields["duration_ms"] = -1
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)

    def test_zero_duration_allowed(self) -> None:
        fields = _base_fields()
        fields["duration_ms"] = 0
        ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptStatusEnum:
    def test_pass_status(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        assert receipt.status is EnumReceiptStatus.PASS

    def test_fail_status(self) -> None:
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.FAIL
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.FAIL

    def test_arbitrary_string_status_rejected(self) -> None:
        fields = _base_fields()
        fields["status"] = "MAYBE"
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestEnumReceiptStatusMembers:
    """OMN-9786: enum exposes exactly {PASS, FAIL, ADVISORY, PENDING}."""

    def test_enum_receipt_status_values(self) -> None:
        assert {s.value for s in EnumReceiptStatus} == {
            "PASS",
            "FAIL",
            "ADVISORY",
            "PENDING",
        }


@pytest.mark.unit
class TestModelDodReceiptAdversarialInvariants:
    """OMN-9786: Centralized Transition Policy enforced by model validator."""

    def test_receipt_with_distinct_verifier_and_runner_is_pass(self) -> None:
        receipt = ModelDodReceipt(
            schema_version="1.0.0",
            ticket_id="OMN-9762",
            evidence_item_id="dod-001",
            check_type="command",
            check_value="gh pr checks 916 --repo OmniNode-ai/omnibase_core",
            runner="worker-N1762",
            verifier="foreground-2026-04-26-session-abc",
            probe_command="gh pr checks 916 --repo OmniNode-ai/omnibase_core",
            probe_stdout="...all checks passed...",
            exit_code=0,
            run_timestamp=datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC),
            status=EnumReceiptStatus.PASS,
            commit_sha="a1b2c3d4e5f6",  # pragma: allowlist secret
        )
        assert receipt.status is EnumReceiptStatus.PASS

    def test_receipt_with_verifier_equal_runner_is_advisory(self) -> None:
        # Even if caller passes status=PASS, model must downgrade to ADVISORY.
        receipt = ModelDodReceipt(
            schema_version="1.0.0",
            ticket_id="OMN-9762",
            evidence_item_id="dod-001",
            check_type="command",
            check_value="gh pr checks 916",
            runner="worker-N1762",
            verifier="worker-N1762",
            probe_command="gh pr checks 916",
            probe_stdout="all green",
            exit_code=0,
            run_timestamp=datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC),
            status=EnumReceiptStatus.PASS,
            commit_sha="a1b2c3d4e5f6",  # pragma: allowlist secret
        )
        assert receipt.status is EnumReceiptStatus.ADVISORY

    def test_receipt_with_empty_probe_stdout_for_command_type_fails(self) -> None:
        with pytest.raises(ValidationError, match="probe_stdout"):
            ModelDodReceipt(
                schema_version="1.0.0",
                ticket_id="OMN-9762",
                evidence_item_id="dod-001",
                check_type="command",
                check_value="gh pr checks 916",
                runner="worker-N1762",
                verifier="foreground-X",
                probe_command="gh pr checks 916",
                probe_stdout="",  # empty stdout for a command check is rejected
                exit_code=0,
                run_timestamp=datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC),
                status=EnumReceiptStatus.PASS,
                commit_sha="a1b2c3d4e5f6",  # pragma: allowlist secret
            )

    @pytest.mark.parametrize(
        "executable_check_type", ["command", "test_passes", "endpoint", "grep"]
    )
    def test_empty_probe_stdout_fails_for_all_executable_check_types(
        self, executable_check_type: str
    ) -> None:
        with pytest.raises(ValidationError, match="probe_stdout"):
            ModelDodReceipt(
                schema_version="1.0.0",
                ticket_id="OMN-9762",
                evidence_item_id="dod-001",
                check_type=executable_check_type,
                check_value="probe",
                runner="worker-A",
                verifier="foreground-B",
                probe_command="probe",
                probe_stdout="   \n  ",  # whitespace-only also rejected
                run_timestamp=datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC),
                status=EnumReceiptStatus.PASS,
                commit_sha="a1b2c3d4e5f6",  # pragma: allowlist secret
            )

    def test_receipt_file_exists_check_alone_demoted_to_advisory(self) -> None:
        # file_exists is weak proof; status downgrades to ADVISORY regardless
        # of verifier/runner identity. Empty probe_stdout is allowed for this
        # check_type because file_exists has no stdout.
        receipt = ModelDodReceipt(
            schema_version="1.0.0",
            ticket_id="OMN-9762",
            evidence_item_id="dod-001",
            check_type="file_exists",
            check_value="drift/dod_receipts/OMN-9762/dod-001/file_exists.yaml",
            runner="worker-N1762",
            verifier="foreground-X",
            probe_command=(
                "test -f drift/dod_receipts/OMN-9762/dod-001/file_exists.yaml"
            ),
            probe_stdout="",  # file_exists has no stdout; allowed for this check_type
            exit_code=0,
            run_timestamp=datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC),
            status=EnumReceiptStatus.PASS,
            commit_sha="a1b2c3d4e5f6",  # pragma: allowlist secret
        )
        assert receipt.status is EnumReceiptStatus.ADVISORY

    @pytest.mark.parametrize(
        "bad_version",
        [
            "1.0",
            "v1.0.0",
            "1",
            "abc",
            "",
            "1.0.0.0",
            "01.0.0",  # SemVer 2.0.0: leading zero in MAJOR rejected
            "1.02.0",  # leading zero in MINOR
            "1.0.03",  # leading zero in PATCH
        ],
    )
    def test_invalid_schema_version_rejected(self, bad_version: str) -> None:
        fields = _base_fields()
        fields["schema_version"] = bad_version
        with pytest.raises(ValidationError, match="schema_version"):
            ModelDodReceipt(**fields)

    @pytest.mark.parametrize(
        "good_version",
        [
            "1.0.0",
            "0.0.0",
            "1.2.3-beta.1",
            "2.10.99+build.123",
            "1.0.0-rc.1+build-7",  # SemVer 2.0.0: build metadata may contain hyphens
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-0.3.7",
            "1.0.0-x.7.z.92",
            "10.20.30",
            "1.1.2-prerelease+meta",
        ],
    )
    def test_valid_schema_version_accepted(self, good_version: str) -> None:
        fields = _base_fields()
        fields["schema_version"] = good_version
        receipt = ModelDodReceipt(**fields)
        assert receipt.schema_version == good_version

    def test_advisory_status_passes_through_when_set_explicitly(self) -> None:
        # Caller asks for ADVISORY directly — the validator must not error,
        # and downgrade rules become no-ops because status is already ADVISORY.
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.ADVISORY
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.ADVISORY

    def test_pending_status_accepted_with_stdout(self) -> None:
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.PENDING
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.PENDING

    def test_pending_executable_check_allows_empty_probe_stdout(self) -> None:
        """PENDING means probe was allocated but not yet executed — empty stdout
        is the correct representation. Without this exemption, callers would
        be forced to invent fake stdout to express the pending state."""
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.PENDING
        fields["probe_stdout"] = ""
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.PENDING
        assert receipt.probe_stdout == ""

    def test_self_attestation_preserves_fail_status(self) -> None:
        """FAIL must survive verifier == runner — collapsing FAIL into
        ADVISORY would erase the meaning of the failure outcome."""
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.FAIL
        fields["runner"] = "worker-X"
        fields["verifier"] = "worker-X"  # self-attestation
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.FAIL

    def test_self_attestation_preserves_pending_status(self) -> None:
        """PENDING must survive verifier == runner — a queued probe with
        a single-identity verifier is still pending, not advisory."""
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.PENDING
        fields["runner"] = "worker-X"
        fields["verifier"] = "worker-X"
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.PENDING

    def test_file_exists_preserves_fail_status(self) -> None:
        """FAIL must survive a weak-proof check_type — the probe ran and the
        file was not present; that outcome must remain visible as FAIL."""
        fields = _base_fields()
        fields["check_type"] = "file_exists"
        fields["status"] = EnumReceiptStatus.FAIL
        fields["probe_stdout"] = ""  # file_exists has no stdout
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.FAIL

    def test_file_exists_preserves_pending_status(self) -> None:
        """PENDING must survive a weak-proof check_type — a queued
        file_exists probe is still pending, not advisory."""
        fields = _base_fields()
        fields["check_type"] = "file_exists"
        fields["status"] = EnumReceiptStatus.PENDING
        fields["probe_stdout"] = ""
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.PENDING

    def test_self_attestation_not_bypassable_by_whitespace(self) -> None:
        """``runner="worker-A"`` and ``verifier="worker-A "`` must not slip
        past Rule 1 — identity strings are whitespace-stripped before the
        equality comparison so trailing/leading spaces cannot be used to
        evade the ADVISORY downgrade."""
        fields = _base_fields()
        fields["runner"] = "worker-A"
        fields["verifier"] = "worker-A "  # trailing space
        receipt = ModelDodReceipt(**fields)
        # Both identity strings normalized to "worker-A"; Rule 1 fires.
        assert receipt.runner == "worker-A"
        assert receipt.verifier == "worker-A"
        assert receipt.status is EnumReceiptStatus.ADVISORY

    @pytest.mark.parametrize("blank", ["", "   ", "\t", "\n  \t"])
    def test_whitespace_only_identity_rejected(self, blank: str) -> None:
        """Whitespace-only ``runner`` or ``verifier`` must be rejected at
        construction — silently empty identities would make every receipt
        self-attest under Rule 1 (both normalize to '')."""
        fields = _base_fields()
        fields["runner"] = blank
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)
        fields = _base_fields()
        fields["verifier"] = blank
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptConsolidationFields:
    """OMN-9792: extended fields for EvidenceReceipt + ModelVerifierCheckResult migration."""

    def test_branch_field_optional_defaults_none(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        assert receipt.branch is None

    def test_branch_field_accepts_string(self) -> None:
        fields = _base_fields()
        fields["branch"] = "jonah/omn-9792-consolidate-receipts"
        receipt = ModelDodReceipt(**fields)
        assert receipt.branch == "jonah/omn-9792-consolidate-receipts"

    def test_working_dir_field_optional_defaults_none(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        assert receipt.working_dir is None

    def test_working_dir_field_accepts_string(self) -> None:
        fields = _base_fields()
        fields["working_dir"] = "/home/runner/work/omnibase_core"
        receipt = ModelDodReceipt(**fields)
        assert receipt.working_dir == "/home/runner/work/omnibase_core"

    def test_both_branch_and_working_dir_together(self) -> None:
        fields = _base_fields()
        fields["branch"] = "main"
        fields["working_dir"] = "/workspace"
        receipt = ModelDodReceipt(**fields)
        assert receipt.branch == "main"
        assert receipt.working_dir == "/workspace"

    def test_blank_branch_rejected(self) -> None:
        fields = _base_fields()
        fields["branch"] = "   "
        with pytest.raises(ValidationError, match="non-blank"):
            ModelDodReceipt(**fields)

    def test_relative_working_dir_rejected(self) -> None:
        fields = _base_fields()
        fields["working_dir"] = "relative/path"
        with pytest.raises(ValidationError, match="absolute"):
            ModelDodReceipt(**fields)

    def test_working_dir_none_accepted(self) -> None:
        fields = _base_fields()
        fields["working_dir"] = None
        receipt = ModelDodReceipt(**fields)
        assert receipt.working_dir is None

    def test_branch_none_accepted(self) -> None:
        fields = _base_fields()
        fields["branch"] = None
        receipt = ModelDodReceipt(**fields)
        assert receipt.branch is None
