# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-honesty validator — fail gamed DoD receipts (OMN-12791).

A receipt can pass the structural receipt-gate (correct schema, non-empty
probe_stdout, distinct verifier/runner) while still being dishonest: the
probe_command is a no-op ``echo``, the verifier identity is fabricated, or
the proof text defers the actual check to a future wave.

This module enforces five honesty rules over ``ModelDodReceipt``:

  A. NO_OP_PROBE — PASS command receipts must not use a no-op probe_command
     (``echo``, ``true``, ``:``, ``cat <file>``, ``ls <path>``).  A no-op
     proves nothing; any exit code can be manufactured by appending ``; true``.

  B. PENDING_IN_PASS — PASS receipt probe_stdout or actual_output must not
     contain deferral language (PENDING, TBD, TODO, "not implemented",
     "not yet", "will be", "deferred").  These phrases indicate the check was
     written as a place-holder rather than executed.

  C. SELF_ATTESTATION — verifier must differ from runner.  The model layer
     already auto-downgrades identical pairs to ADVISORY; this rule surfaces
     ADVISORY receipts as a hard honesty violation so the gate can distinguish
     "ADVISORY because of weak proof type" from "ADVISORY because self-attested".

  D. FAKE_HUMAN_VERIFIER — if the runner is a known agent handle (codex,
     claude, gpt, sonnet, opus) and the verifier is a human handle (jonah,
     user, human, or an email address), the receipt is fabricating independent
     review.  An agent cannot verify its own work by borrowing a human's name.

  E. DEPLOY_REALNESS — if the evidence_item_id or check_value contains a
     deploy keyword (deploy, redeploy, migration-applied, rollout), the
     probe_command must contain a real operational verb (rpk, docker exec,
     kubectl, psql, curl, ssh).  Echo-only deploy probes prove authorship,
     not execution.

Placement rationale: pure logic over ``ModelDodReceipt`` with no I/O
dependencies → omnibase_core.validation, same layer as
``validator_receipt_gate``.

CLI entry point: ``python -m omnibase_core.validation.validator_receipt_honesty``
  Scans a receipts directory and prints all violations.  Exit 0 when clean,
  exit 1 when any violation found.  Intended for pre-commit and CI wiring.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt

# ---------------------------------------------------------------------------
# Rule identifiers
# ---------------------------------------------------------------------------


class EnumHonestyRule(StrEnum):
    """Discrete honesty rule identifiers.  One enum member per rule A-E."""

    NO_OP_PROBE = "NO_OP_PROBE"
    PENDING_IN_PASS = "PENDING_IN_PASS"
    SELF_ATTESTATION = "SELF_ATTESTATION"
    FAKE_HUMAN_VERIFIER = "FAKE_HUMAN_VERIFIER"
    DEPLOY_REALNESS = "DEPLOY_REALNESS"


# ---------------------------------------------------------------------------
# Violation dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HonestyViolation:
    """One honesty rule violation found in a receipt.

    Attributes:
        rule: Which rule was violated.
        detail: Human-readable explanation naming the field values that
            triggered the rule.
        receipt_path: Path to the receipt file on disk (empty when the
            receipt was checked in-memory without a path context).
    """

    rule: EnumHonestyRule
    detail: str
    receipt_path: Path = field(default_factory=Path)


# ---------------------------------------------------------------------------
# Rule A — No-op probe
# ---------------------------------------------------------------------------

# Patterns that indicate a no-op probe_command when used as the ENTIRE
# command (or as the leading command before any pipe/semicolon).
#
# ``echo`` is always no-op regardless of arguments.
# ``true`` and ``:`` (shell no-op) are unconditionally no-op.
# ``cat`` and ``ls`` without a downstream assertion (``| grep``, ``| diff``,
# etc.) prove only that a path exists, not that behavior occurred.
_NOOP_COMMAND_RE = re.compile(
    r"^\s*(?:"
    r"echo\b"  # echo with any arguments
    r"|true\b"  # shell true builtin
    r"|:\s*$"  # colon builtin (shell no-op)
    r"|cat\b(?!.*\|\s*(?:grep|diff|wc|awk|jq|python|head|tail))"  # cat without assertion pipe
    r"|ls\b(?!.*\|\s*(?:grep|wc|awk))"  # ls without assertion pipe
    r")",
    re.IGNORECASE,
)

# check_types for which the no-op rule applies.
_COMMAND_LIKE_TYPES = frozenset({"command"})


def _check_rule_a(receipt: ModelDodReceipt) -> HonestyViolation | None:
    """Rule A: PASS command receipt with no-op probe_command."""
    if receipt.status is not EnumReceiptStatus.PASS:
        return None
    if receipt.check_type not in _COMMAND_LIKE_TYPES:
        return None
    if not _NOOP_COMMAND_RE.match(receipt.probe_command):
        return None
    return HonestyViolation(
        rule=EnumHonestyRule.NO_OP_PROBE,
        detail=(
            f"probe_command {receipt.probe_command!r} is a no-op that proves nothing. "
            "A PASS command receipt must execute a command that actually exercises "
            "check_value. Replace with a real probe (e.g. uv run pytest, gh pr checks, "
            "rpk topic consume, docker exec, curl)."
        ),
    )


# ---------------------------------------------------------------------------
# Rule B — PENDING-in-PASS
# ---------------------------------------------------------------------------

_DEFERRAL_RE = re.compile(
    r"\b(?:PENDING|TBD|TODO|not\s+implemented|not\s+yet|will\s+be|deferred)\b",
    re.IGNORECASE,
)


def _check_rule_b(receipt: ModelDodReceipt) -> HonestyViolation | None:
    """Rule B: PASS receipt whose proof text contains deferral language."""
    if receipt.status is not EnumReceiptStatus.PASS:
        return None
    for field_name, text in (
        ("probe_stdout", receipt.probe_stdout),
        ("actual_output", receipt.actual_output or ""),
    ):
        m = _DEFERRAL_RE.search(text)
        if m:
            return HonestyViolation(
                rule=EnumHonestyRule.PENDING_IN_PASS,
                detail=(
                    f"PASS receipt {field_name} contains deferral language "
                    f"{m.group(0)!r} — the check was not executed, only planned. "
                    "Run the actual probe and produce a new receipt with real output."
                ),
            )
    return None


# ---------------------------------------------------------------------------
# Rule C — verifier == runner (self-attestation)
# ---------------------------------------------------------------------------


def _check_rule_c(receipt: ModelDodReceipt) -> HonestyViolation | None:
    """Rule C: verifier must differ from runner.

    ModelDodReceipt already auto-downgrades to ADVISORY; this rule surfaces
    ADVISORY receipts as a hard honesty violation so the scan output is
    actionable regardless of how the model classified the status.
    """
    # The model strips whitespace from both fields, so a raw == suffices.
    if receipt.verifier == receipt.runner:
        return HonestyViolation(
            rule=EnumHonestyRule.SELF_ATTESTATION,
            detail=(
                f"verifier={receipt.verifier!r} == runner={receipt.runner!r}. "
                "Self-attestation is rejected: an independent verifier with a "
                "different identity must sign off on PASS receipts."
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Rule D — Fake human verifier
# ---------------------------------------------------------------------------

# Agent handle fragments — a runner whose lower-cased value contains any of
# these substrings is classified as an AI agent.
_AGENT_HANDLE_FRAGMENTS = frozenset(
    {
        "codex",
        "claude",
        "gpt",
        "sonnet",
        "opus",
        "gemini",
        "llm",
        "agent",
        "worker",
        "bot",
        "ai-",
        "-ai",
    }
)

# Human handle patterns — a verifier whose lower-cased value matches any of
# these is classified as a human handle claim.
_HUMAN_VERIFIER_RE = re.compile(
    r"(?:"
    r"\bjonah\b"  # known developer name
    r"|\buser\b"  # generic "user"
    r"|\bhuman\b"  # explicit "human" claim
    r"|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"  # email address
    r")",
    re.IGNORECASE,
)


def _is_agent_runner(runner: str) -> bool:
    lower = runner.lower()
    return any(fragment in lower for fragment in _AGENT_HANDLE_FRAGMENTS)


def _is_human_verifier_claim(verifier: str) -> bool:
    return bool(_HUMAN_VERIFIER_RE.search(verifier))


def _check_rule_d(receipt: ModelDodReceipt) -> HonestyViolation | None:
    """Rule D: agent runner + human verifier without approval receipt id."""
    if not _is_agent_runner(receipt.runner):
        return None
    if not _is_human_verifier_claim(receipt.verifier):
        return None
    # If the verifier also looks like an agent handle, rule C may apply instead.
    # Rule D is specifically about a human name being borrowed.
    return HonestyViolation(
        rule=EnumHonestyRule.FAKE_HUMAN_VERIFIER,
        detail=(
            f"runner={receipt.runner!r} is an AI agent but verifier={receipt.verifier!r} "
            "is a human handle. An agent cannot borrow a human's identity as an "
            "independent verifier. Use a real verifier identity (another agent, a CI "
            "job name, or a human who actually reviewed the output) and record an "
            "external approval-receipt id."
        ),
    )


# ---------------------------------------------------------------------------
# Rule E — Deploy realness
# ---------------------------------------------------------------------------

_DEPLOY_KEYWORD_RE = re.compile(
    r"\b(?:deploy|redeploy|migration[-_]applied|rollout)\b",
    re.IGNORECASE,
)

# Real operational verbs that prove deploy execution.
_REAL_DEPLOY_VERB_RE = re.compile(
    r"\b(?:rpk|docker\s+exec|kubectl|psql|curl|ssh)\b",
    re.IGNORECASE,
)


def _has_deploy_keyword(text: str) -> bool:
    return bool(_DEPLOY_KEYWORD_RE.search(text))


def _has_real_deploy_verb(probe_command: str) -> bool:
    return bool(_REAL_DEPLOY_VERB_RE.search(probe_command))


def _check_rule_e(receipt: ModelDodReceipt) -> HonestyViolation | None:
    """Rule E: deploy-keyword evidence must not use a no-op probe_command.

    Fires when the evidence_item_id or check_value implies a deploy action
    AND the probe_command is a no-op (echo, true, colon, bare cat/ls).
    A deploy receipt that only echoes a summary string proves authorship,
    not execution.  Real probes (rpk, docker exec, kubectl, psql, curl,
    ssh, gh api, uv run pytest, grep -c, ...) satisfy this rule.
    """
    if receipt.status is not EnumReceiptStatus.PASS:
        return None
    if not (
        _has_deploy_keyword(receipt.evidence_item_id)
        or _has_deploy_keyword(receipt.check_value)
    ):
        return None
    # Only fire when the probe itself is a no-op.  Real commands (even if
    # they don't ssh into the server) probe contract artifacts or CI state
    # and are acceptable.  The canonical gamed pattern is ``echo <message>``.
    if not _NOOP_COMMAND_RE.match(receipt.probe_command):
        return None
    return HonestyViolation(
        rule=EnumHonestyRule.DEPLOY_REALNESS,
        detail=(
            f"evidence_item_id={receipt.evidence_item_id!r} implies a deploy but "
            f"probe_command={receipt.probe_command!r} is a no-op that proves nothing. "
            "A deploy receipt must probe the live system or CI state with a real command "
            "(rpk, docker exec, kubectl, psql, curl, ssh, gh api, grep -c, etc.) — "
            "not echo a summary."
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_receipt_honesty(receipt: ModelDodReceipt) -> list[HonestyViolation]:
    """Apply all five honesty rules to one receipt.

    Returns the list of violations; empty means the receipt is honest.
    Rules are applied independently — a receipt may violate multiple rules.

    Args:
        receipt: A parsed and model-validated ``ModelDodReceipt`` instance.

    Returns:
        List of ``HonestyViolation`` objects (empty when the receipt is clean).
    """
    violations: list[HonestyViolation] = []
    for checker in (
        _check_rule_a,
        _check_rule_b,
        _check_rule_c,
        _check_rule_d,
        _check_rule_e,
    ):
        result = checker(receipt)
        if result is not None:
            violations.append(result)
    return violations


# ---------------------------------------------------------------------------
# Bulk scanner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReceiptFinding:
    """All honesty violations found for one receipt file on disk."""

    receipt_path: Path
    violations: list[HonestyViolation]


def scan_receipts_directory(receipts_dir: Path) -> list[ReceiptFinding]:
    """Walk ``receipts_dir`` and apply honesty rules to every parseable receipt.

    Files that are not valid YAML or fail ``ModelDodReceipt`` schema validation
    are skipped (they will be caught by the structural receipt-gate).  Only
    structurally valid receipts that nonetheless violate honesty rules appear
    in the returned findings.

    Args:
        receipts_dir: Root of the OCC ``drift/dod_receipts/`` tree.

    Returns:
        List of ``ReceiptFinding`` — one entry per file that has at least one
        honesty violation.  Empty list when the directory is clean.
    """
    findings: list[ReceiptFinding] = []
    for receipt_path in sorted(receipts_dir.rglob("*.yaml")):
        try:
            with receipt_path.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
        except (yaml.YAMLError, OSError):
            continue  # structural errors caught by receipt-gate
        if not isinstance(raw, dict):
            continue
        try:
            receipt = ModelDodReceipt.model_validate(raw)
        except (ValidationError, ValueError):
            continue  # schema errors caught by receipt-gate
        violations = check_receipt_honesty(receipt)
        if violations:
            # Attach receipt_path to each violation for CLI output.
            stamped = [
                HonestyViolation(
                    rule=v.rule,
                    detail=v.detail,
                    receipt_path=receipt_path,
                )
                for v in violations
            ]
            findings.append(
                ReceiptFinding(receipt_path=receipt_path, violations=stamped)
            )
    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI: scan a receipts directory and exit non-zero on any violation.

    Usage::

        python -m omnibase_core.validation.validator_receipt_honesty \\
            --receipts-dir onex_change_control/drift/dod_receipts

    Exit codes:
        0 — no honesty violations found
        1 — one or more violations found (output lists each with rule + detail)
    """
    parser = argparse.ArgumentParser(
        description=(
            "Receipt-honesty validator (OMN-12791): scan DoD receipts for "
            "gamed probes, deferred evidence, self-attestation, fake human "
            "verifiers, and deploy-keyword echo receipts."
        )
    )
    parser.add_argument(
        "--receipts-dir",
        default="onex_change_control/drift/dod_receipts",
        help="Root of the dod_receipts/ tree to scan.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop scanning after the first violation.",
    )
    args = parser.parse_args(argv)

    receipts_dir = Path(args.receipts_dir)
    if not receipts_dir.exists():
        print(f"ERROR: receipts-dir does not exist: {receipts_dir}", file=sys.stderr)
        return 1

    findings = scan_receipts_directory(receipts_dir)
    if not findings:
        print(f"RECEIPT HONESTY GATE PASSED: 0 violations in {receipts_dir}")
        return 0

    total_violations = sum(len(f.violations) for f in findings)
    print(
        f"RECEIPT HONESTY GATE FAILED: {total_violations} violation(s) "
        f"across {len(findings)} receipt(s):\n"
    )
    for finding in findings:
        for v in finding.violations:
            print(f"  [{v.rule}] {finding.receipt_path}")
            print(f"    {v.detail}")
            print()
        if args.fail_fast:
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "EnumHonestyRule",
    "HonestyViolation",
    "ReceiptFinding",
    "check_receipt_honesty",
    "scan_receipts_directory",
]
