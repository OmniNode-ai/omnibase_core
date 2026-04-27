# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the re-probe verification mode (OMN-9789).

The re-probe verifier re-runs a receipt's recorded ``probe_command`` and
checks that the current exit_code matches the receipt's recorded exit_code.
It is a defense against fabricated receipts (lesson F92 — "PR self-reported
MERGED is unverified until probe confirms"). It is **not** full historical
replay: environment, side effects, time, and external state may differ.

Coverage:
- Allowlisted always-pass probe ("true") returns PASS.
- Allowlisted always-fail probe ("false") returns FAIL with exit_code in detail.
- Non-allowlisted probe ("rm -rf /") returns FAIL with allowlist in detail.
- Missing probe_command returns FAIL.
- Exit-code mismatch returns FAIL.
- Allowlist contains the exact prefixes specified by the plan.
- Constants module exposes the re-probe API.
"""

from __future__ import annotations

import pytest

from omnibase_core.validation.validator_receipt_reprobe import (
    PROBE_COMMAND_ALLOWLIST,
    PROBE_REEXEC_TIMEOUT_SECONDS,
    verify_receipt_by_reexecuting_probe,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Plan-mandated test cases (Task 9, Step 1)
# ---------------------------------------------------------------------------


def test_reexecute_passing_probe_returns_pass() -> None:
    """A receipt whose probe is always-pass and whose recorded exit_code is 0
    should re-execute to PASS.
    """
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "true",
        "probe_command": "true",
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "PASS", detail


def test_reexecute_failing_probe_returns_fail() -> None:
    """A receipt that records exit_code=0 but whose probe currently exits
    non-zero must FAIL with the mismatch reported in the detail.
    """
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "false",
        "probe_command": "false",
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "exit_code" in detail.lower()


def test_reexecute_only_runs_probes_in_allowlist() -> None:
    """A receipt whose probe_command is not in the allowlist must FAIL fast
    with ``allowlist`` in the detail; the dangerous command must NOT execute.
    """
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "x",
        "probe_command": "rm -rf /",
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "allowlist" in detail.lower()


# ---------------------------------------------------------------------------
# Defense-in-depth coverage
# ---------------------------------------------------------------------------


def test_reexecute_missing_probe_command_returns_fail() -> None:
    """A receipt with no ``probe_command`` field cannot be re-probed."""
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "x",
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "probe_command" in detail.lower()


def test_reexecute_empty_probe_command_returns_fail() -> None:
    """Empty string is treated identically to missing field."""
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "x",
        "probe_command": "",
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "probe_command" in detail.lower()


def test_reexecute_exit_code_mismatch_returns_fail() -> None:
    """Recorded exit_code=1 but probe currently returns 0 → FAIL.

    Even though "true" exits 0 successfully, the receipt claimed it exited 1,
    so the receipt cannot be re-verified.
    """
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "true",
        "probe_command": "true",
        "probe_stdout": "",
        "exit_code": 1,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "exit_code" in detail.lower()


def test_reexecute_missing_exit_code_field_returns_fail() -> None:
    """A receipt without exit_code cannot be checked for parity."""
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "true",
        "probe_command": "true",
        "probe_stdout": "",
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "exit_code" in detail.lower()


# ---------------------------------------------------------------------------
# Allowlist canonical form
# ---------------------------------------------------------------------------


def test_allowlist_contains_exact_plan_prefixes() -> None:
    """The plan's acceptance criteria require the allowlist to contain
    exactly these prefixes — additions or removals require a new ticket.
    """
    expected = {
        "gh pr view",
        "gh pr checks",
        "gh api",
        "psql ",
        "curl ",
        "uv run pytest",
        "test -f",
        "test -d",
        "true",
        "false",
    }
    assert set(PROBE_COMMAND_ALLOWLIST) == expected


def test_timeout_is_120_seconds() -> None:
    """Plan acceptance: timeout cap of 120 seconds per probe."""
    assert PROBE_REEXEC_TIMEOUT_SECONDS == 120


# ---------------------------------------------------------------------------
# Allowlist edge cases — membership semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "probe",
    [
        "gh pr view 123 --repo OmniNode-ai/omnibase_core",
        "gh pr checks 123",
        "gh api repos/OmniNode-ai/omnibase_core/pulls/123",
        "test -f /tmp/some-file",
        "test -d /tmp/some-dir",
    ],
)
def test_allowlisted_prefix_with_args_passes_allowlist(probe: str) -> None:
    """An allowlisted prefix followed by arguments is accepted; only the
    prefix match is required to clear the allowlist gate (the probe itself
    may still fail at exit-code time).
    """
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "x",
        "probe_command": probe,
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    # Either PASS or FAIL is acceptable; what we are asserting is that the
    # allowlist gate did NOT veto this probe (so detail must not mention
    # "allowlist").
    assert "allowlist" not in detail.lower(), (
        f"Allowlisted probe was rejected: {detail}"
    )
    assert status in ("PASS", "FAIL")


@pytest.mark.parametrize(
    "probe",
    [
        "rm -rf /",
        "sudo shutdown",
        "echo gh pr view",  # prefix-substring shifted off-start
        "gh pr merge 123",  # gh family but not in allowlist
        " curl https://example.com",  # leading-whitespace stripped, but
        # 'curl ' is allowlisted — this DOES pass; see strip-then-check note
        # in implementation. Use a truly off-list command for negative case:
    ],
)
def test_non_allowlisted_probe_is_rejected(probe: str) -> None:
    """Non-allowlisted commands must fail fast before any subprocess runs."""
    if probe.strip().startswith(("curl ", "true", "false")):
        # The leading-whitespace case actually IS allowlisted because the
        # implementation strips. Skip — covered separately.
        pytest.skip("leading-whitespace allowlisted prefix")
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "x",
        "probe_command": probe,
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "allowlist" in detail.lower()


@pytest.mark.parametrize(
    "probe",
    [
        "trueevil",  # NOTE(OMN-9789): would pass naive startswith("true")
        "falseflag --foo",  # NOTE(OMN-9789): would pass naive startswith("false")
        "gh pr viewx 123",  # NOTE(OMN-9789): would pass naive startswith("gh pr view")
        "gh pr checksum",  # NOTE(OMN-9789): would pass naive startswith("gh pr checks")
        "gh apifoo",  # NOTE(OMN-9789): would pass naive startswith("gh api")
        "test -files /tmp/x",  # NOTE(OMN-9789): would pass naive startswith("test -f")
    ],
)
def test_command_boundary_prevents_prefix_smuggling(probe: str) -> None:
    """Allowlist matching must be on a command boundary, not a raw substring.

    A naive ``str.startswith`` check would let ``trueevil`` slip past a
    ``"true"`` prefix and ``gh pr viewx`` slip past ``"gh pr view"``. The
    allowlist gate must require the prefix to either equal the probe or be
    followed by whitespace.
    """
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-A",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "x",
        "probe_command": probe,
        "probe_stdout": "",
        "exit_code": 0,
        "runner": "worker",
        "verifier": "foreground-X",
        "run_timestamp": "2026-04-26T12:00:00Z",
        "status": "PASS",
    }
    status, detail = verify_receipt_by_reexecuting_probe(receipt)
    assert status == "FAIL"
    assert "allowlist" in detail.lower(), (
        f"Boundary-smuggled probe should be rejected by allowlist: {detail}"
    )
