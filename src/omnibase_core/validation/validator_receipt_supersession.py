# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Supersession-chain resolution for DoD receipts (OMN-13888, scope item 3).

A receipt key ``(<TICKET>, <EVIDENCE_ITEM>, <CHECK_TYPE>)`` maps to a base file::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.yaml

plus an append-only chain of net-new correction records::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.supersede.<SUFFIX>.yaml

A tombstone record (``tombstone: true``, no replacement) invalidates the key; a
replacement record re-binds the key to a new receipt embedded in the record.
When no supersession file exists, the key resolves to its base receipt file.
No merged file is ever edited — corrections are always net-new files.

Two resolution tiers (OMN-16432):

1. **Target-aware.** When the caller supplies ``current_pr_number``, a single
   shared ``evidence_item_id`` may legitimately be re-bound to *several*
   different downstream consumer PRs by separate supersession records (e.g.
   an ``occ-self-bind-pr-<N>`` anchor rebound once per consumer). The record
   whose ``replacement.pr_number`` matches ``current_pr_number`` — or a
   tombstone, which invalidates the key for everyone — wins, using the
   chronologically latest (``created_at``) applicable record. This makes
   resolution correct regardless of what convention a record's filename
   suffix follows.
2. **Legacy fallback.** From the original OMN-13888 design: the record with
   the highest ``NNNN`` filename suffix is authoritative. This is the sole
   path when no candidate explicitly targets ``current_pr_number`` (including
   when the caller passes no PR context at all), so existing single-consumer
   chains — the overwhelming majority, and the only shape that predates
   per-target binding — resolve exactly as before. Non-numeric suffixes never
   participate in this tiebreak, matching pre-OMN-16432 behavior.

Repeated attempts on one consumer (OMN-19050):

A record used to be named for its consumer PR alone, so one pull request got
exactly one executed attempt, ever. A check that failed for ANY reason —
including an environment one, which is what happened on omnimarket#2751 —
blocked that PR through the evidence chain permanently, because the second
execution had nowhere to be filed and the first kept resolving FAIL. A chain
may now carry an attempt-scoped record, ``<CHECK>.supersede.<PR>.<NNNN>.yaml``,
and two rules make that safe rather than merely possible:

* **Order is total by construction.** Records sort by ``created_at`` first and
  by a dotted-numeric sequence key second (``_sequence_key``), so two records
  for one key resolve identically in any filesystem order, and a same-second
  pair still has exactly one winner.
* **A PASS supersedes a FAIL only as an independent observation**
  (``_guarded_winner``). Re-filing a PASS over the FAIL's own code changes
  nothing and clears nothing, so the chain cannot be used as a
  retry-until-green channel. Self-attestation is refused upstream and
  unchanged: ``ModelDodReceipt`` downgrades a PASS whose ``verifier`` equals
  its ``runner`` to ADVISORY.

What counts as the same observation (OMN-19050, second pass):

The guard first compared ``commit_sha`` alone, and omnimarket#2839 showed that
was wrong both ways. An empty commit (``9c09739``, the same tree as
``f490fba``) got a new commit id with no code change and cleared a FAIL. That
works for any FAIL, a flaky one included. And a real correction of the
declared check, re-executed at the SAME head, was refused because the commit
id matched. Two receipts now describe the same observation only when both of
these hold:

* **Same code.** Both ``tree_sha`` values match when both records carry one.
  Otherwise ``commit_sha`` is compared, which is exactly the prior rule, so a
  record written before ``tree_sha`` existed resolves as it always did.
* **Same check.** A definition change needs BOTH a different
  ``contract_entry_sha256`` AND a different declared command. The entry hash
  also covers the item's description, so a prose edit alone must not count.
  The runner's per-commit ``repos/<owner>/<repo>/commits/<sha>`` line is not
  part of the command.

A PASS is refused against ANY earlier FAIL that is the same observation, not
only the latest one. When a PASS is accepted over a FAIL at the same code
because the check changed, the resolution records why in ``guard_note``.

This module keeps the path-local O(1) glob the receipt tree was built for; it
does not scan a global supersessions directory, and chain length for a single
key is always small (this is not a global scan).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_receipt_supersession import (
    ModelReceiptSupersession,
)

# Suffix is everything between ".supersede." and ".yaml" — deliberately not
# digit-only. A prior digit-only pattern silently dropped non-numeric-suffix
# files (e.g. "command.supersede.2010-head.yaml") from consideration with no
# error; widening this keeps every real record visible to resolution below.
#
# OMN-19050 widened it again, from "[^./]+" to "[^/]+", so a DOTTED suffix is
# visible too. The prior pattern excluded ".", which meant an attempt-scoped
# record — "test_passes.supersede.2751.0002.yaml" — matched nothing and never
# entered resolution. It was not outranked by the record it corrected; it was
# invisible, with no error, which is the same silent-drop failure the previous
# widening was written to fix.
_SUPERSEDE_SUFFIX_RE = re.compile(r"\.supersede\.([^/]+)\.yaml$")

# The product-repo receipt runner prefixes every executed command with the
# reference for its own commit (OMN-17794). That line differs on every commit,
# so it identifies where the check ran, not what the check was.
_COMMIT_REFERENCE_LINE_RE = re.compile(
    r"^repos/[^/\s]+/[^/\s]+/commits/[0-9a-f]{7,40}$"
)


@dataclass(frozen=True)
class SupersessionResolution:
    """Outcome of resolving a receipt key's supersession chain.

    Exactly one of ``receipt``, ``tombstoned``, or ``error`` is meaningful:

    - ``receipt`` set → the key is re-bound to this replacement receipt.
    - ``tombstoned`` True → the key is deliberately invalidated (no active
      receipt); the caller must treat it as MISSING / non-satisfied.
    - ``error`` set → the authoritative supersession record is
      unreadable/invalid; the caller must fail closed.

    ``source_path`` names the record used, for operator-facing messages.

    ``guard_note`` is set when the anti-retry guard shaped the outcome: it
    refused a PASS that restated a FAIL, or it accepted a PASS over a FAIL at
    the same code because the check definition changed. None otherwise.
    """

    receipt: ModelDodReceipt | None
    tombstoned: bool
    error: str | None
    source_path: Path
    guard_note: str | None = None


def _load_supersede_record(
    path: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
) -> tuple[ModelReceiptSupersession | None, str | None]:
    """Load, parse, and key-validate one supersession record.

    Returns ``(record, None)`` on success or ``(None, error_message)`` on any
    read/parse/key-mismatch failure.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except (yaml.YAMLError, OSError) as exc:
        return None, f"supersession record {path} is unreadable: {exc}"

    try:
        record = ModelReceiptSupersession.model_validate(raw)
    except ValidationError as exc:
        return None, f"supersession record {path} is invalid: {exc}"

    if (record.ticket_id, record.evidence_item_id, record.check_type) != (
        ticket_id,
        evidence_item_id,
        check_type,
    ):
        return None, (
            f"supersession record {path} declares key "
            f"({record.ticket_id}, {record.evidence_item_id}, "
            f"{record.check_type}) but is filed under "
            f"({ticket_id}, {evidence_item_id}, {check_type})"
        )
    return record, None


def _sequence_key(suffix: str) -> tuple[int, ...] | None:
    """Total order over a dotted-numeric suffix, or None when it is not one.

    ``"2751"`` → ``(2751,)`` and ``"2751.0002"`` → ``(2751, 2)``, so an
    attempt-scoped record sorts strictly after the bare-PR record it extends
    by plain tuple comparison. A single-component suffix keys to a 1-tuple,
    which compares exactly as the pre-OMN-19050 ``int(suffix)`` did for every
    chain that has only ever used one — the overwhelming majority.

    ``None`` for anything else (``"2010-head"``, an empty component), which
    keeps a non-numeric suffix out of the sequence tiebreak exactly as the
    prior ``str.isdigit`` filter did.
    """
    parts = suffix.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _order_key(
    created_at: datetime, suffix: str
) -> tuple[datetime, tuple[int, tuple[int, ...]]]:
    """Total order for one record: authoring time first, sequence second.

    The old tiebreak was ``int(suffix) if suffix.isdigit() else -1``, which
    ranked a dotted suffix BELOW every bare one. Two records stamped in the
    same second — the runner writes ``created_at`` to whole seconds, so this
    is reachable — therefore handed the win to the record being corrected.
    Sorting a non-numeric suffix under a ``0`` discriminator keeps it last
    without ever comparing an ``int`` against a tuple.
    """
    sequence = _sequence_key(suffix)
    if sequence is None:
        return created_at, (0, ())
    return created_at, (1, sequence)


def _declared_command(receipt: ModelDodReceipt) -> str:
    """The command a receipt executed, without the runner's commit reference.

    Whitespace is collapsed, so re-wrapping a long command is not a change.
    """
    lines = [
        line
        for line in receipt.check_value.splitlines()
        if not _COMMIT_REFERENCE_LINE_RE.match(line.strip())
    ]
    return " ".join(" ".join(lines).split())


def _code_identity(
    fail: ModelDodReceipt, candidate: ModelDodReceipt
) -> tuple[bool, str]:
    """Whether two receipts observed the same code, and the identity compared.

    The tree is the code. Two commits with one tree differ only in metadata,
    so a new commit id over an unchanged tree is not a new observation. The
    tree is compared only when BOTH receipts carry one. Otherwise the commit
    id is compared, which is the rule every earlier record was resolved under.

    A tree may only ever ADD sameness. One commit has one tree, and
    ``tree_sha`` is written by the record's author with nothing binding it to
    ``commit_sha``, so the same commit id is the same code whatever trees the
    two records claim. Letting a claimed tree split one commit into two
    observations would be weaker than the commit-only rule this replaces.
    """
    if fail.commit_sha == candidate.commit_sha:
        return True, f"commit {fail.commit_sha}"
    if fail.tree_sha is not None and candidate.tree_sha is not None:
        return fail.tree_sha == candidate.tree_sha, f"tree {fail.tree_sha}"
    return False, f"commit {fail.commit_sha}"


def _check_definition_changed(
    fail: ModelDodReceipt, candidate: ModelDodReceipt
) -> bool:
    """Whether a different check ran, not just a differently described one.

    Both signals must move. The entry hash alone also changes when only the
    item's description is edited, and the command text alone is what OCC
    commit 66946494a5 left inconsistent with a hand-edited entry hash. A
    missing hash on either side is not evidence of a change.
    """
    if fail.contract_entry_sha256 is None or candidate.contract_entry_sha256 is None:
        return False
    return (
        fail.contract_entry_sha256 != candidate.contract_entry_sha256
        and _declared_command(fail) != _declared_command(candidate)
    )


def _guarded_winner(
    ordered: list[tuple[Path, ModelReceiptSupersession]],
) -> tuple[Path, ModelReceiptSupersession, str | None]:
    """The last record in chain order, unless it launders a prior FAIL.

    OMN-19050. Ordering alone would let any later PASS erase any earlier
    FAIL, which turns an append-only chain into a retry-until-green channel:
    re-file the same observation often enough and the gate stops biting. So a
    PASS supersedes a prior FAIL only as an INDEPENDENT OBSERVATION: different
    code (``_code_identity``) or a different check
    (``_check_definition_changed``). The same check over the same code is the
    same observation restated, and the FAIL stands.

    Every earlier FAIL is checked, not only the latest. With only the latest,
    FAIL at T1, then FAIL at T2, then PASS at T1 again would clear T1.

    Returns the winning record and a note when the guard shaped the outcome
    (see ``SupersessionResolution.guard_note``).

    This is deliberately the ONLY distinctness test applied here. The other
    half of the two-actor rule is enforced upstream and unchanged: a
    replacement whose ``verifier`` equals its ``runner`` is downgraded from
    PASS to ADVISORY by ``ModelDodReceipt`` itself, so an author still cannot
    pass their own receipt through a supersession. Re-testing that here would
    be a second copy of a rule that already holds.

    Scope: the supersede chain only. A base receipt is not read — a chain's
    records are the executed observations, and the base is the minted
    placeholder they correct.
    """
    winner_path, winner = ordered[-1]
    replacement = winner.replacement
    if replacement is None or replacement.status is not EnumReceiptStatus.PASS:
        return winner_path, winner, None

    accepted_note: str | None = None
    for path, record in reversed(ordered[:-1]):
        prior = record.replacement
        if prior is None or prior.status is not EnumReceiptStatus.FAIL:
            continue
        same_code, identity = _code_identity(prior, replacement)
        if not same_code:
            continue
        if _check_definition_changed(prior, replacement):
            if accepted_note is None:
                accepted_note = (
                    f"PASS {winner_path.name} supersedes FAIL {path.name} at the "
                    f"same {identity} because the check definition changed: "
                    f"contract_entry_sha256 {prior.contract_entry_sha256} -> "
                    f"{replacement.contract_entry_sha256}"
                )
            continue
        return (
            path,
            record,
            (
                f"PASS {winner_path.name} refused: it restates FAIL {path.name} "
                f"at the same {identity} under the same check definition "
                f"(contract_entry_sha256 {prior.contract_entry_sha256}); an "
                "independent observation needs different code or a changed check"
            ),
        )
    return winner_path, winner, accepted_note


def _resolution_from_record(
    record: ModelReceiptSupersession, path: Path, guard_note: str | None = None
) -> SupersessionResolution:
    if record.tombstone:
        return SupersessionResolution(
            receipt=None,
            tombstoned=True,
            error=None,
            source_path=path,
            guard_note=guard_note,
        )
    return SupersessionResolution(
        receipt=record.replacement,
        tombstoned=False,
        error=None,
        source_path=path,
        guard_note=guard_note,
    )


def resolve_supersession(
    receipts_dir: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
    current_pr_number: int | None = None,
) -> SupersessionResolution | None:
    """Resolve the active receipt for a key from its supersession chain.

    ``current_pr_number``, when supplied, scopes resolution to the record
    that explicitly targets that consumer PR (see module docstring, tier 1).
    Omitting it reproduces the original numeric-highest-suffix behavior
    exactly (tier 2) — every existing call site that has not been updated to
    pass PR context keeps behaving as it always has.

    Returns ``None`` when no supersession file exists for the key — the caller
    then proceeds with the base receipt file exactly as before (backward
    compatible). Otherwise returns a :class:`SupersessionResolution` describing
    the re-bind, the tombstone, or a load error from the authoritative record.
    """
    key_dir = receipts_dir / ticket_id / evidence_item_id
    if not key_dir.is_dir():
        return None

    candidates: list[tuple[str, Path]] = []
    for candidate in key_dir.glob(f"{check_type}.supersede.*.yaml"):
        match = _SUPERSEDE_SUFFIX_RE.search(candidate.name)
        if match is not None:
            candidates.append((match.group(1), candidate))
    if not candidates:
        return None

    # Load every candidate up front. This chain is already scoped to a single
    # receipt key (never a global scan) so it stays bounded by chain length —
    # in practice 1-5 files even for a heavily-corrected key.
    loaded: list[tuple[str, Path, ModelReceiptSupersession | None, str | None]] = []
    for suffix, path in candidates:
        record, err = _load_supersede_record(
            path, ticket_id, evidence_item_id, check_type
        )
        loaded.append((suffix, path, record, err))

    sequenced = sorted(
        (item for item in loaded if _sequence_key(item[0]) is not None),
        # mypy: the generator above admits only suffixes with a sequence key.
        key=lambda item: _sequence_key(item[0]) or (),
    )

    def _legacy_winner() -> SupersessionResolution | None:
        """Tier 2: highest-sequence suffix wins (pre-OMN-16432 behavior)."""
        if not sequenced:
            return None
        _, error_path, highest, err = sequenced[-1]
        if highest is None:
            return SupersessionResolution(
                receipt=None, tombstoned=False, error=err, source_path=error_path
            )
        ordered = [
            (path, record) for _s, path, record, _e in sequenced if record is not None
        ]
        path, record, note = _guarded_winner(ordered)
        return _resolution_from_record(record, path, note)

    if current_pr_number is None:
        return _legacy_winner()

    # Tier 1: records that explicitly apply to this consumer — a tombstone
    # (key-wide invalidation, applies to every consumer) or a rebind whose
    # replacement targets current_pr_number exactly. Latest created_at wins;
    # numeric suffix is only a same-timestamp tiebreak.
    applicable: list[
        tuple[
            tuple[datetime, tuple[int, tuple[int, ...]]],
            Path,
            ModelReceiptSupersession,
        ]
    ] = []
    for suffix, path, record, _err in loaded:
        if record is None:
            continue
        if record.tombstone:
            applicable.append((_order_key(record.created_at, suffix), path, record))
            continue
        if (
            record.replacement is not None
            and record.replacement.pr_number == current_pr_number
        ):
            applicable.append((_order_key(record.created_at, suffix), path, record))

    if applicable:
        applicable.sort(key=lambda item: item[0])
        winner_path, winner_record, note = _guarded_winner(
            [(path, record) for _key, path, record in applicable]
        )
        return _resolution_from_record(winner_record, winner_path, note)

    # No record targets this consumer specifically — behave exactly as a
    # caller with no PR context would (legacy / untargeted chain).
    return _legacy_winner()


__all__ = ["SupersessionResolution", "resolve_supersession"]
