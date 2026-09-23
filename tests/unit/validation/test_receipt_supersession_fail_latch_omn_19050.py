# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19050 — a FAIL supersede record must not latch a key forever.

Measured on omnimarket#2751 (2026-09-21): the product-repo receipt runner
executed a declared ``test_passes`` check, it failed for an environment
reason, and the runner filed ``test_passes.supersede.2751.yaml`` with
``status: FAIL``. The cause was fixed and the check re-executed green, but
the key kept resolving FAIL and ``occ-preflight`` kept reporting
``reason=nonpass_receipt``. One pull request therefore got exactly one
executed attempt, ever.

Two independent defects produced that latch, and both are exercised here:

1. ``_SUPERSEDE_SUFFIX_RE`` excluded ``.`` from a suffix, so an attempt-scoped
   record named ``<check>.supersede.<pr>.<n>.yaml`` matched nothing and never
   entered resolution at all. It was not outranked — it was invisible.
2. Ordering was by numeric filename suffix, with a non-numeric suffix sorted
   to ``-1``. Even once visible, an attempt-scoped record lost to the very
   record it was filed to correct.

The repaired semantics, which these tests pin:

* A key's supersede chain is ordered by ``created_at`` first and by a total
  dotted-numeric sequence key second, so two records for one key resolve the
  same way in any filesystem order.
* A later PASS supersedes an earlier FAIL only as an INDEPENDENT OBSERVATION —
  its replacement must carry a different ``commit_sha``. A PASS re-filed at
  the same head is the same observation restated, and does not clear the FAIL.
* Self-attestation is unchanged: ``verifier == runner`` still downgrades a
  PASS to ADVISORY at the model layer, so an author cannot pass their own
  receipt through this path.
* Deferral vocabulary in a PASS is unchanged: the honesty validator still
  refuses it, and a supersede record is not a way around that.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.validation.validator_receipt_honesty import (
    EnumHonestyRule,
    check_receipt_honesty,
)
from omnibase_core.validation.validator_receipt_supersession import (
    _sequence_key,
    resolve_supersession,
)

TICKET = "OMN-18868"
ITEM = "dod-occ-diff-derived-behavior-proof-pr-2751"
CHECK = "test_passes"
PR = 2751

# The two real heads from the measured incident: the check failed at the
# first and passed at the second after the cause was fixed.
FAIL_SHA = "bab99887" + "0" * 32
PASS_SHA = "668a565b" + "1" * 32


def _receipt(
    *,
    status: EnumReceiptStatus,
    commit_sha: str,
    runner: str = "omnimarket-ci occ-receipt-runner",
    verifier: str = "github-actions product-repo test execution",
    probe_stdout: str = "31 passed in 13.14s\n",
) -> dict:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": CHECK,
        "check_value": "uv run pytest tests/unit/test_wire_compatibility.py",
        "status": status.value,
        "run_timestamp": datetime(2026, 9, 21, 16, 0, tzinfo=UTC),
        "commit_sha": commit_sha,
        "runner": runner,
        "verifier": verifier,
        "probe_command": "uv run pytest tests/unit/test_wire_compatibility.py",
        "probe_stdout": probe_stdout,
        "exit_code": 0 if status is EnumReceiptStatus.PASS else 1,
        "pr_number": PR,
        "contract_entry_sha256": "sha256:" + "0" * 64,
    }


def _record(*, replacement: dict, created_at: datetime) -> dict:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": CHECK,
        "supersedes": f"drift/dod_receipts/{TICKET}/{ITEM}/{CHECK}.yaml",
        "reason": "the declared check was executed for real in the product checkout",
        "superseder": "omnimarket-ci occ-receipt-runner",
        "created_at": created_at,
        "tombstone": False,
        "replacement": replacement,
    }


def _key_dir(root: Path) -> Path:
    key_dir = root / "receipts" / TICKET / ITEM
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / f"{CHECK}.yaml").write_text(
        yaml.safe_dump(
            _receipt(status=EnumReceiptStatus.PENDING, commit_sha="0" * 40),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return key_dir


def _write(key_dir: Path, suffix: str, record: dict) -> None:
    (key_dir / f"{CHECK}.supersede.{suffix}.yaml").write_text(
        yaml.safe_dump(record, sort_keys=True), encoding="utf-8"
    )


def _fail_then(
    root: Path,
    *,
    second_status: EnumReceiptStatus,
    second_sha: str,
    second_suffix: str = f"{PR}.0002",
    second_verifier: str = "github-actions product-repo test execution",
    second_runner: str = "omnimarket-ci occ-receipt-runner",
) -> Path:
    """Replay the #2751 sequence: a FAIL record, then a second executed record."""
    key_dir = _key_dir(root)
    _write(
        key_dir,
        f"{PR}.0001",
        _record(
            replacement=_receipt(
                status=EnumReceiptStatus.FAIL,
                commit_sha=FAIL_SHA,
                probe_stdout="ERROR: no tags found in a depth-1 checkout\n",
            ),
            created_at=datetime(2026, 9, 21, 16, 5, tzinfo=UTC),
        ),
    )
    _write(
        key_dir,
        second_suffix,
        _record(
            replacement=_receipt(
                status=second_status,
                commit_sha=second_sha,
                runner=second_runner,
                verifier=second_verifier,
            ),
            created_at=datetime(2026, 9, 21, 17, 30, tzinfo=UTC),
        ),
    )
    return root / "receipts"


# --------------------------------------------------------------------------- #
# AC1 — the latch itself
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_pass_at_a_new_head_supersedes_a_prior_fail(tmp_path: Path) -> None:
    """AC1: re-executed and now passing at a fixed head resolves PASS.

    This is the #2751 sequence exactly. Before OMN-19050 the second record
    could not even be filed, and had it been filed the resolver would not
    have seen it.
    """
    receipts = _fail_then(
        tmp_path, second_status=EnumReceiptStatus.PASS, second_sha=PASS_SHA
    )

    resolution = resolve_supersession(
        receipts, TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert resolution is not None
    assert resolution.error is None
    assert resolution.tombstoned is False
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS
    assert resolution.receipt.commit_sha == PASS_SHA


@pytest.mark.unit
def test_attempt_scoped_record_is_visible_without_pr_context(tmp_path: Path) -> None:
    """The legacy (no-PR-context) tier must rank attempt suffixes too.

    ``resolve_supersession`` has call sites that pass no PR number. If the
    dotted suffix is invisible or unranked there, the same latch reappears
    through a different door.
    """
    receipts = _fail_then(
        tmp_path, second_status=EnumReceiptStatus.PASS, second_sha=PASS_SHA
    )

    resolution = resolve_supersession(receipts, TICKET, ITEM, CHECK)

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS


# --------------------------------------------------------------------------- #
# AC2 — unambiguous by construction
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_two_records_resolve_identically_in_either_write_order(
    tmp_path: Path,
) -> None:
    """AC2: filesystem order must not change the answer."""
    forward = tmp_path / "forward"
    backward = tmp_path / "backward"
    forward.mkdir()
    backward.mkdir()

    fail_record = _record(
        replacement=_receipt(status=EnumReceiptStatus.FAIL, commit_sha=FAIL_SHA),
        created_at=datetime(2026, 9, 21, 16, 5, tzinfo=UTC),
    )
    pass_record = _record(
        replacement=_receipt(status=EnumReceiptStatus.PASS, commit_sha=PASS_SHA),
        created_at=datetime(2026, 9, 21, 17, 30, tzinfo=UTC),
    )

    forward_dir = _key_dir(forward)
    _write(forward_dir, f"{PR}.0001", fail_record)
    _write(forward_dir, f"{PR}.0002", pass_record)

    backward_dir = _key_dir(backward)
    _write(backward_dir, f"{PR}.0002", pass_record)
    _write(backward_dir, f"{PR}.0001", fail_record)

    first = resolve_supersession(
        forward / "receipts", TICKET, ITEM, CHECK, current_pr_number=PR
    )
    second = resolve_supersession(
        backward / "receipts", TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert first is not None and first.receipt is not None
    assert second is not None and second.receipt is not None
    assert first.receipt.status is second.receipt.status is EnumReceiptStatus.PASS
    assert first.receipt.commit_sha == second.receipt.commit_sha == PASS_SHA
    assert first.source_path.name == second.source_path.name


@pytest.mark.unit
def test_same_timestamp_breaks_by_attempt_sequence_not_by_string(
    tmp_path: Path,
) -> None:
    """AC2: a same-second pair still has exactly one winner.

    The runner stamps ``created_at`` to whole seconds, so two attempts CAN
    share a timestamp. The tiebreak must be the attempt sequence, and a
    dotted sequence must outrank the bare PR suffix it extends -- the old
    tiebreak sorted a dotted suffix to -1 and handed the win to the FAIL.
    """
    key_dir = _key_dir(tmp_path)
    stamp = datetime(2026, 9, 21, 17, 30, tzinfo=UTC)
    _write(
        key_dir,
        str(PR),
        _record(
            replacement=_receipt(status=EnumReceiptStatus.FAIL, commit_sha=FAIL_SHA),
            created_at=stamp,
        ),
    )
    _write(
        key_dir,
        f"{PR}.0002",
        _record(
            replacement=_receipt(status=EnumReceiptStatus.PASS, commit_sha=PASS_SHA),
            created_at=stamp,
        ),
    )

    resolution = resolve_supersession(
        tmp_path / "receipts", TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS


# --------------------------------------------------------------------------- #
# AC3 + negative controls — the gate must still bite
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_second_fail_keeps_the_key_failing(tmp_path: Path) -> None:
    """AC3: re-executed and still failing stays FAIL."""
    receipts = _fail_then(
        tmp_path, second_status=EnumReceiptStatus.FAIL, second_sha=PASS_SHA
    )

    resolution = resolve_supersession(
        receipts, TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL


@pytest.mark.unit
def test_pass_at_the_same_head_does_not_clear_a_fail(tmp_path: Path) -> None:
    """Negative control: a PASS re-filed at the FAIL's own head is refused.

    Nothing changed between the two records, so the second is the same
    observation restated rather than an independent one. Allowing it would
    turn the supersede chain into a retry-until-green channel.
    """
    receipts = _fail_then(
        tmp_path, second_status=EnumReceiptStatus.PASS, second_sha=FAIL_SHA
    )

    resolution = resolve_supersession(
        receipts, TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL
    assert resolution.receipt.commit_sha == FAIL_SHA


@pytest.mark.unit
def test_self_attested_pass_does_not_clear_a_fail(tmp_path: Path) -> None:
    """Negative control: the author cannot pass their own receipt.

    ``verifier == runner`` downgrades PASS to ADVISORY at the model layer.
    ADVISORY is not PASS, so the key stays ineligible however the chain is
    ordered.
    """
    identity = "omnimarket-ci occ-receipt-runner"
    receipts = _fail_then(
        tmp_path,
        second_status=EnumReceiptStatus.PASS,
        second_sha=PASS_SHA,
        second_runner=identity,
        second_verifier=identity,
    )

    resolution = resolve_supersession(
        receipts, TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is not EnumReceiptStatus.PASS
    assert resolution.receipt.status is EnumReceiptStatus.ADVISORY


@pytest.mark.unit
def test_pass_carrying_deferral_vocabulary_is_still_refused() -> None:
    """Negative control: supersession is not a route around honesty Rule B."""
    receipt = ModelDodReceipt.model_validate(
        _receipt(
            status=EnumReceiptStatus.PASS,
            commit_sha=PASS_SHA,
            probe_stdout="wire compatibility check TODO — deferred to a follow-up\n",
        )
    )

    violations = check_receipt_honesty(receipt)

    assert any(v.rule is EnumHonestyRule.PENDING_IN_PASS for v in violations)


# The cross-repo contract, spelled once on this side too. OCC's
# `_supersede_sequence` in scripts/validation/check_receipt_hardening.py must
# return exactly this for the same input, and that repo's OMN-19050 test
# module pins the identical table from its own side. The duplication is
# deliberate: onex_change_control pins omnibase-core from the registry, so it
# cannot import this helper until the pin carries this release. Both ends
# asserting the same literal table is what keeps them from drifting in the
# meantime -- a gate that validates one record while the merge is decided by
# another is a silent gate.
SEQUENCE_CONTRACT: list[tuple[str, tuple[int, ...] | None]] = [
    ("2751", (2751,)),
    ("2751.0002", (2751, 2)),
    ("0001", (1,)),
    ("9999.0010.0003", (9999, 10, 3)),
    ("2010-head", None),
    ("", None),
    ("abc", None),
]


@pytest.mark.unit
@pytest.mark.parametrize(("token", "expected"), SEQUENCE_CONTRACT)
def test_sequence_key_matches_the_cross_repo_contract(
    token: str, expected: tuple[int, ...] | None
) -> None:
    """The eligibility resolver and the OCC hardening gate must agree."""
    assert _sequence_key(token) == expected
