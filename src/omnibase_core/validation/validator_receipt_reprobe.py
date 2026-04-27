# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-probe verification mode for ModelDodReceipt artifacts (OMN-9789).

The Receipt Gate (``omnibase_core.validation.receipt_gate``) statically
checks that every cited ticket has a PASS receipt on disk. That is a
necessary but not sufficient guarantee: a fabricated receipt is
indistinguishable from a real one if you only inspect the file.

This module adds an *active* verification path. It re-runs each receipt's
recorded ``probe_command`` and compares the current ``exit_code`` against
the value the receipt claims. If the recorded probe still produces the
recorded exit code, the receipt is **re-verified**. If not, the receipt is
flagged as drifted (or fabricated).

Truth boundary: this is re-probe verification, not full historical replay.
It validates that a recorded ``probe_command`` can be rerun under current
conditions and exits as recorded. It does not prove temporal correctness,
environment equivalence, side-effect identity, or that the original claim
was true at the original time.

Active-drive lesson F92: "PR self-reported MERGED is unverified until probe
confirms." A receipt is a self-attested artifact; rerunning the probe is
the cheapest available externalization of trust.

Safety: probes execute via ``subprocess.run(shell=False)`` with arguments
split by ``shlex.split`` — there is no shell interpolation. Only commands
whose stripped form matches one of the command-boundary prefixes in
:data:`PROBE_COMMAND_ALLOWLIST` are allowed to run. Anything else fails fast
with detail mentioning ``allowlist``. Each probe is wall-clock-capped at
:data:`PROBE_REEXEC_TIMEOUT_SECONDS`.

Public API: :func:`verify_receipt_by_reexecuting_probe` (single-receipt)
and :func:`verify_receipts_by_reexecuting_probes` (batch, producing a
:class:`ModelReceiptReprobeReport`).

CLI: ``python -m omnibase_core.validation.validator_receipt_reprobe``
exposes a ``--receipts-dir`` driver. The receipt-gate CLI in
``receipt_gate_cli.py`` accepts ``--reexecute-probes`` (default OFF in CI;
ON in the manual scaffold session-end ritual).
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

from omnibase_core.models.contracts.ticket.model_receipt_reprobe_report import (
    ModelReceiptReprobeReport,
)
from omnibase_core.models.contracts.ticket.model_receipt_reprobe_result import (
    ModelReceiptReprobeResult,
    ReprobeStatus,
)

# ---------------------------------------------------------------------------
# Allowlist + constants
# ---------------------------------------------------------------------------

# Command-prefix allowlist for re-execution. A probe is permitted to run only
# if its stripped form matches one of these prefixes on a command boundary.
# Listing here (not in code body) makes the policy grep-able and easy to extend
# by ticket review.
#
# Ordering is documentation, not semantics — the membership check is
# whitespace-stripped command-boundary prefix match.
PROBE_COMMAND_ALLOWLIST: tuple[str, ...] = (
    "gh pr view",
    "gh pr checks",
    "gh api",
    "psql ",
    "curl ",
    "uv run pytest",
    "test -f",
    "test -d",
)

# Wall-clock cap per probe re-execution. Anything slower indicates the probe
# is hung, not slow — fail closed.
PROBE_REEXEC_TIMEOUT_SECONDS: int = 120


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _probe_in_allowlist(probe: str) -> bool:
    """Return True iff the probe matches an allowlisted prefix on a command boundary.

    Plain ``str.startswith`` is too permissive: ``"trueevil"`` would slip past a
    ``"true"`` prefix, and ``"gh pr viewx"`` would slip past ``"gh pr view"``.
    Each prefix is treated as a command form: the probe must equal the prefix or
    be followed by whitespace.
    """
    stripped = probe.strip()
    for prefix in PROBE_COMMAND_ALLOWLIST:
        canonical = prefix.rstrip()
        if stripped == canonical or stripped.startswith(f"{canonical} "):
            return True
    return False


# ---------------------------------------------------------------------------
# Single-receipt verifier (plan-mandated dict-based signature)
# ---------------------------------------------------------------------------


def verify_receipt_by_reexecuting_probe(
    receipt: dict[str, object],
) -> tuple[ReprobeStatus, str]:
    """Re-execute the receipt's probe_command and compare ``exit_code``.

    The receipt is supplied as a raw mapping (the YAML/JSON form on disk)
    rather than as a :class:`ModelDodReceipt` so this function can be called
    against legacy receipts that may not validate against the current
    schema. Schema enforcement is the receipt-gate's job; this function
    answers the narrower question: does the recorded probe still exit as
    recorded?

    Args:
        receipt: Raw receipt mapping. Must contain ``probe_command`` and
            ``exit_code``.

    Returns:
        ``("PASS", detail)`` if and only if:

        * ``probe_command`` is non-empty and allowlisted;
        * the probe re-executes within :data:`PROBE_REEXEC_TIMEOUT_SECONDS`;
        * the re-execution's return code equals the recorded ``exit_code``;
        * the re-execution exited 0 (success).

        ``("FAIL", detail)`` on every other path. ``detail`` always
        identifies the failure mode (``probe_command``, ``allowlist``,
        ``exit_code``, etc.) so the caller can render a useful CI message.
    """
    probe = receipt.get("probe_command", "")
    if not isinstance(probe, str) or not probe:
        return "FAIL", "receipt has no probe_command field"
    if not _probe_in_allowlist(probe):
        return "FAIL", f"probe_command not in allowlist: {probe!r}"

    if "exit_code" not in receipt:
        return (
            "FAIL",
            "receipt has no exit_code field; cannot verify re-execution parity",
        )
    expected_exit = receipt.get("exit_code")
    if type(expected_exit) is not int:
        return (
            "FAIL",
            f"receipt.exit_code must be int, got {type(expected_exit).__name__}",
        )

    try:
        result = subprocess.run(
            shlex.split(probe),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=PROBE_REEXEC_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        return (
            "FAIL",
            f"probe re-execution timed out after {PROBE_REEXEC_TIMEOUT_SECONDS}s: {e}",
        )
    except (OSError, ValueError) as e:
        # OSError: binary not found, perms; ValueError: shlex unbalanced quotes
        return "FAIL", f"probe re-execution failed: {e}"

    if result.returncode != expected_exit:
        return (
            "FAIL",
            (
                f"re-execution exit_code={result.returncode} does not match "
                f"receipt.exit_code={expected_exit}"
            ),
        )
    if result.returncode != 0:
        return (
            "FAIL",
            f"probe failed on re-execution (exit_code={result.returncode})",
        )
    return "PASS", "probe re-execution matches receipt"


# ---------------------------------------------------------------------------
# Batch verifier
# ---------------------------------------------------------------------------


def verify_receipts_by_reexecuting_probes(
    receipts_dir: Path,
) -> ModelReceiptReprobeReport:
    """Walk ``receipts_dir`` and re-probe every receipt found.

    Args:
        receipts_dir: Root of the receipt tree
            (``<root>/<ticket-id>/<evidence-item-id>/<check-type>.yaml``).

    Returns:
        A :class:`ModelReceiptReprobeReport` with one
        :class:`ModelReceiptReprobeResult` per receipt file.
    """
    results: list[ModelReceiptReprobeResult] = []
    if not receipts_dir.is_dir():
        return ModelReceiptReprobeReport(
            receipts_dir=str(receipts_dir),
            results=[],
        )

    for receipt_path in sorted(receipts_dir.rglob("*.yaml")):
        try:
            with receipt_path.open(encoding="utf-8") as fh:
                # yaml-ok: re-probe verifies raw legacy receipts that may not
                # validate against the current ModelDodReceipt schema; schema
                # enforcement is the receipt-gate's job, not this verifier's.
                raw = yaml.safe_load(fh)
        except (yaml.YAMLError, OSError) as e:
            results.append(
                ModelReceiptReprobeResult(
                    receipt_path=str(receipt_path),
                    ticket_id="*",
                    evidence_item_id="*",
                    check_type="*",
                    status="FAIL",
                    detail=f"corrupt receipt: {e}",
                )
            )
            continue

        if not isinstance(raw, dict):
            results.append(
                ModelReceiptReprobeResult(
                    receipt_path=str(receipt_path),
                    ticket_id="*",
                    evidence_item_id="*",
                    check_type="*",
                    status="FAIL",
                    detail=f"receipt root is not a mapping: {type(raw).__name__}",
                )
            )
            continue

        status, detail = verify_receipt_by_reexecuting_probe(raw)
        ticket_id = raw.get("ticket_id", "*")
        evidence_item_id = raw.get("evidence_item_id", "*")
        check_type = raw.get("check_type", "*")
        results.append(
            ModelReceiptReprobeResult(
                receipt_path=str(receipt_path),
                ticket_id=ticket_id if isinstance(ticket_id, str) else "*",
                evidence_item_id=(
                    evidence_item_id if isinstance(evidence_item_id, str) else "*"
                ),
                check_type=check_type if isinstance(check_type, str) else "*",
                status=status,
                detail=detail,
            )
        )

    return ModelReceiptReprobeReport(
        receipts_dir=str(receipts_dir),
        results=results,
    )


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry: re-probe every receipt under ``--receipts-dir``.

    Exit codes:
        0 — every receipt re-verifies (PASS)
        1 — at least one receipt failed re-verification
    """
    parser = argparse.ArgumentParser(
        description=(
            "Re-probe verification — re-run every recorded probe_command "
            "and verify the current exit_code matches the recorded one. "
            "Defense against fabricated receipts (active-drive lesson F92)."
        )
    )
    parser.add_argument(
        "--receipts-dir",
        default="onex_change_control/drift/dod_receipts",
        help="Directory tree containing ModelDodReceipt YAML files.",
    )
    args = parser.parse_args(argv)

    report = verify_receipts_by_reexecuting_probes(Path(args.receipts_dir))

    if not report.results:
        print(f"::notice::no receipts found under {args.receipts_dir}")
        return 0

    failures = [r for r in report.results if r.status != "PASS"]
    for r in report.results:
        line = (
            f"{r.status}: {r.ticket_id}/{r.evidence_item_id}/{r.check_type} "
            f"({r.receipt_path}): {r.detail}"
        )
        if r.status == "PASS":
            print(f"::notice::{line}")
        else:
            print(f"::error::{line}")

    if failures:
        print(
            f"::error::RE-PROBE FAILED: {len(failures)} of {len(report.results)} "
            "receipt(s) did not re-verify. Receipts may be drifted or fabricated."
        )
        return 1
    print(
        f"::notice::RE-PROBE PASSED: all {len(report.results)} receipt(s) re-verified."
    )
    return 0


__all__ = [
    "PROBE_COMMAND_ALLOWLIST",
    "PROBE_REEXEC_TIMEOUT_SECONDS",
    "verify_receipt_by_reexecuting_probe",
    "verify_receipts_by_reexecuting_probes",
]


if __name__ == "__main__":
    sys.exit(main())
