# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The Done-write receipt gate: one rule for every writer of a Done state.

OMN-20368. Operator ruling (2026-10-02): a ticket reaches Done only on a PASS
dod_verify whose checks bind every acceptance criterion; a merged PR or ticked
boxes is never enough. The evidence-autoclose closer (omnibase_infra) already
enforced that rule for its own flips. Every other code path that wrote a Done
state straight to the Linear API (the triage handler in omnimarket, the
sync-revert watchdog and the generic Linear adapters in omnibase_infra) did
not. This module is the rule lifted out of the closer into the lowest layer
both repos import, so those paths and the closer evaluate one implementation.

Pure logic, no I/O. A caller reads the ticket's description and runs
``onex skill dod_verify <ticket>``, then hands both to
:func:`evaluate_done_write_receipt`:

1. the verdict must exist and reach ``status == "verified"`` with at least one
   verified check, no failed check, and every verdict-bearing check either
   verified or non-probative (the closer's OMN-16821 arithmetic);
2. every acceptance criterion parsed from the description must be bound, by
   ``binds_ac``, to a VERIFIED check whose pin (if any) still matches the
   criterion's text (:func:`ac_binding_gap`, OMN-18056 / OMN-18135 / OMN-18238 /
   OMN-18330).

A description from which no criterion parses holds: a ticket whose criteria
cannot be read is a ticket nothing can be said about.

The helpers below were moved verbatim from ``handler_evidence_autoclose_sweep``
(omnibase_infra), dropping the leading underscore; their comments still speak
in the closer's voice.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

from omnibase_core.enums.ticket.enum_ac_binding_check_status import (
    EnumAcBindingCheckStatus,
)
from omnibase_core.models.ticket.model_ac_binding_row import ModelAcBindingRow
from omnibase_core.models.ticket.model_done_write_decision import (
    ModelDoneWriteDecision,
)

#: dod_verify's own terminal status for "every verdict-bearing check passed".
DOD_VERIFY_STATUS_VERIFIED = "verified"
dod_verify_non_probative_key = "non_probative_count"

# Where `onex skill dod_verify <ticket>` actually puts its verdict.
#
# `receipt_mode._run_and_emit` prints ONE of TWO receipt arms, and which one
# is decided by the run's own outcome (OMN-16961):
#
#   success-like AND a handler result exists
#       -> `result` IS the handler's own model, FLAT. The verdict keys
#          (status, total_checks, verified_count, ...) sit directly on
#          `result`, and there is no `terminal_payload` key anywhere.
#          `result_model` = ModelDodVerifyState.
#   anything else
#       -> `result` is a ModelReceiptRuntimeSummary (workflow_result,
#          exit_code, workflow, terminal_payload, handler_result, error,
#          capture_log) and the verdict is nested at `result.terminal_payload`.
#          `result_model` = ModelReceiptRuntimeSummary.
#
# OMN-16736 read the second arm only. Its constant was verified against a
# single live capture (tests/fixtures/omn16736/) that happened to be a
# `status: failed` run — the summary arm. Generalising it to every outcome
# inverted the sweep: dod_verify's workflow result is success-like exactly
# when its verdict is `verified`, so the arm the reader could not parse was
# precisely the FLIP-ELIGIBLE one. Run 33258391128 recorded 10 of 19
# verdict-eligible tickets as `error_verify_unparseable` at `exit_code=0`
# while the diagnose step — which falls back to the envelope itself — read
# full verdicts from the same bytes. `tickets_flipped` could not leave 0.
#
# `result_model` is the receipt's own declared type tag, so reading it is
# using the contract rather than sniffing the shape. Both arms are captured
# verbatim at tests/fixtures/omn16961/ (OMN-16961).
RECEIPT_SUMMARY_RESULT_MODEL = (
    "omnibase_infra.cli.model_receipt_runtime_summary.ModelReceiptRuntimeSummary"
)

DOD_VERIFY_STATE_RESULT_MODEL = (
    "omnimarket.nodes.node_dod_verify.models.model_dod_verify_state.ModelDodVerifyState"
)

dod_verify_verdict_key = "terminal_payload"

#: Per-check records on the dod_verify terminal payload. Read for the class-(c)
#: and class-(d) classifiers and for the gap fingerprint; every counter the
#: flip predicate consults is unchanged.
dod_verify_checks_key = "checks"

# The per-check fields this module reads, named once. They are declared on
# `ModelEvidenceCheckResult` in omnimarket; the closer sees them as JSON.
check_id_key = "evidence_id"

check_status_key = "status"

#: OMN-15911. What a passing check BOUND: behaviour, merge state, surrogate.
check_proof_class_key = "proof_class"

#: OMN-18056. The acceptance criteria this evidence item DECLARES it covers,
#: as `binds_ac` on the contract's `dod_evidence` item, carried through
#: dod_verify onto the per-check record. An ABSENT key and an EMPTY list are
#: different facts and the gap reason distinguishes them: absent means the
#: verifier predates OMN-18056 and cannot report a binding at all, empty means
#: the contract was read and declares none. Both hold; only one of them is a
#: contract-authoring gap.
check_binds_ac_key = "binds_ac"

#: OMN-18238. The subset of `binds_ac` on this check that is a PROPOSAL rather
#: than an accepted binding. A machine may propose; it may not decide.
#: A passing check whose name resembles a criterion is not proof of the
#: criterion it names, so a draft label is excluded from the discharge set and
#: its criterion stays unbound until a person accepts the proposal.
#:
#: ABSENT means "nothing here is a proposal", which is what every one of the
#: 67 contracts that declared a binding before this existed means: each was
#: hand-authored, which IS the acceptance this rule asks for. The key narrows
#: `binds_ac`; it can never add to it.
check_draft_binds_ac_key = "draft_binds_ac"

#: OMN-18330. WHICH REVISION OF EACH CRITERION THIS CHECK'S BINDINGS WERE
#: ACCEPTED AGAINST: `{label: criterion_hash}`, carried from the contract's
#: `dod_evidence[].ac_bindings[]` records (`onex_change_control`'s
#: `ModelAcBinding`) onto the per-check record, the same route `binds_ac` and
#: `draft_binds_ac` take and for the same reason -- the verifier is the only
#: component that resolves and reads the contract.
#:
#: ABSENT means this check declares no pin, which is 67 of the 68 contracts
#: that declare a binding at all. Those are hand-authored and bind exactly as
#: they did; the key can demote a criterion and can never introduce one.
check_ac_binding_hashes_key = "ac_binding_hashes"

#: Per-check statuses, as `EnumEvidenceCheckStatus` spells them.
CHECK_STATUS_VERIFIED = "verified"

#: OMN-18135 AC4. A check that read live state and asserted on it. It
#: discharges a state-shaped criterion and never a behaviour-shaped one.
CHECK_PROOF_CLASS_READBACK = "readback"


def has_verified_bound_check(verdict: dict[str, object]) -> bool:
    """Whether any check on this verdict VERIFIED a criterion binding.

    ``verified`` is the only status that is both a verdict and a proof:
    ``non_probative`` ran and could not have gone the other way (OMN-15391),
    ``skipped`` never ran, ``superseded`` was replaced. So "verified probative
    check" starts with "check whose status is verified". OMN-18106's
    post-revert release also requires that proof to be tied to at least one
    acceptance criterion through ``binds_ac``. A green but unbound provenance
    row is not enough to say the postdating evidence is the evidence the
    ticket is judged on.
    """
    for check in check_records(verdict):
        if check_status(check) != CHECK_STATUS_VERIFIED:
            continue
        raw = check.get(check_binds_ac_key)
        if not isinstance(raw, list):
            continue
        if any(canonical_ac_label(str(declared)) for declared in raw):
            return True
    return False


def as_int(value: object) -> int:
    """Best-effort int coercion for a loosely-typed dod_verify JSON field."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def extract_dod_verify_verdict(
    receipt: dict[str, object],
) -> tuple[dict[str, object] | None, str]:
    """Return the dod_verify verdict from either declared receipt arm.

    OMN-16961. `onex skill dod_verify` prints two structurally different
    receipts (see `RECEIPT_SUMMARY_RESULT_MODEL` above for the branch that
    picks between them). Both are legitimate, both are declared, and the
    receipt names which one it is in `result_model`. This reader dispatches
    on that tag and on nothing else.

    It does NOT sniff for whichever key happens to be present. A receipt
    whose `result_model` is absent or unrecognised is REFUSED by name — the
    sweep would rather stop than guess at an undeclared shape, because a
    wrong guess here is a Done flip on evidence nobody read (OMN-15715 /
    OMN-16832 AC2). Same for a declared arm that carries no `total_checks`:
    that is a dispatch which produced output but reached no verdict, and it
    stays an error, never a 0/0 "gap" that reads like a ticket problem.

    Returns ``(verdict, "")`` on success and ``(None, reason)`` on refusal,
    where ``reason`` names the specific cause rather than the generic "no
    verdict was reached".
    """
    result_model = receipt.get("result_model")
    result = receipt.get("result")
    result = result if isinstance(result, dict) else {}

    if not isinstance(result_model, str) or not result_model.strip():
        return None, (
            "the receipt declares no `result_model`, so which of the two "
            "`onex skill` result arms it carries cannot be established — "
            "refusing to guess at an undeclared shape."
        )

    if result_model == RECEIPT_SUMMARY_RESULT_MODEL:
        verdict = result.get(dod_verify_verdict_key)
        if not isinstance(verdict, dict):
            return None, (
                f"the receipt is a `{RECEIPT_SUMMARY_RESULT_MODEL}` whose "
                f"`result.{dod_verify_verdict_key}` is absent — the runtime "
                "emitted no terminal event, so the verifier genuinely reached "
                "no verdict."
            )
        arm = f"result.{dod_verify_verdict_key}"
    elif result_model == DOD_VERIFY_STATE_RESULT_MODEL:
        # Success arm: `result` IS the verdict, flat. No nesting exists.
        verdict = result
        arm = "result"
    else:
        return None, (
            f"unrecognised dod_verify receipt `result_model` {result_model!r} "
            f"— expected {DOD_VERIFY_STATE_RESULT_MODEL!r} (success arm) or "
            f"{RECEIPT_SUMMARY_RESULT_MODEL!r} (runtime-summary arm). The "
            "receipt contract drifted; refusing to infer a verdict from an "
            "unknown shape."
        )

    if "total_checks" not in verdict:
        return None, (
            f"the receipt declares `{result_model}` but its `{arm}` carries no "
            "`total_checks` — output was produced, no verdict was reached."
        )
    return verdict, ""


# A bullet or numbered list item.
LIST_ITEM_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+(.*)$")

# An `AC1: ...` / `AC-2 ...` line with no bullet at all -- a common shape in
# these tickets that a list-item-only parser would silently count as zero.
# OMN-18048: leading emphasis markers must not hide the item. Criteria written
# `**AC1** - ...` matched NEITHER regex -- not LIST_ITEM_RE (no bullet, no
# number) and not this one (the line starts with `*`, not `AC`). Measured on
# OMN-18035: four criteria in that shape, zero parsed. The optional `[*_]*`
# prefix is stripped from the captured text below so the item reads the same
# however it was written.
AC_ITEM_RE = re.compile(
    r"^[ \t]*([*_]*)[ \t]*(AC[-_ ]?\d+)(?!\d)[*_]*(.*?)[ \t]*$", re.IGNORECASE
)

# The closing half of a wrapped emphasis run, dropped ONLY when the item opened
# with one. Unconditional stripping would eat a legitimate trailing `_` from
# item text that never used emphasis at all.
TRAILING_EMPHASIS_RE = re.compile(r"[*_]+$")

# OMN-18048: a trailing parenthetical qualifier on an otherwise-recognised
# heading -- `Acceptance criteria (falsifiable)`, `DoD (per repo)`. Stripped
# before the closed-set membership test in is_ac_heading.
TRAILING_QUALIFIER_RE = re.compile(r"\s*\([^)]*\)\s*$")

# A leading `[ ]` / `[x]` task marker, stripped from item text for readability.
TASK_MARKER_RE = re.compile(r"^\[[ \t xX]\][ \t]*")

# Leading enumeration on a heading line: `3. Acceptance criteria`.
HEADING_ENUM_RE = re.compile(r"^\d+[.)]\s*")

# Heading texts that open an acceptance-criteria section, after normalization.
AC_HEADING_TEXTS = frozenset(
    {
        "acceptance criteria",
        "acceptance criteria (ac)",
        "acceptance criterion",
        "acceptance",
        "ac",
        "acs",
        # OMN-16106 D3. The same section under its other standing name. A
        # ticket that writes "Definition of done" instead of "Acceptance
        # criteria" is making the identical statement, and reading only one
        # spelling is the same formatting-dependence this revision removes
        # from the coverage rule below.
        "definition of done",
        "definition of done (dod)",
        "dod",
    }
)

# Cap on how many uncovered criteria are spelled out in the Linear comment.
# A description with 40 unchecked boxes does not need 40 quoted lines to make
# the point, and an unbounded splice is how a comment body hits an API limit.
MAX_UNCOVERED_LISTED = 20

# OMN-18056. The label a `binds_ac` entry can point AT. Matched against the
# item text `acceptance_criteria_items` returns, which has already had its
# bullet and any `[ ]`/`[x]` marker stripped -- so `**AC1** ...`, `AC-2: ...`,
# `DoD3 -- ...` and `ac 4)` all reach here with the label leading.
#
# A criterion with NO label is not a parse failure and is not skipped: it is
# an UNBINDABLE criterion, because `binds_ac: ["AC3"]` needs something stable
# to point at and an ordinal derived from parse position renumbers every
# binding below it the moment a bullet is inserted. Those tickets hold until
# their criteria are labelled, which is a ticket-authoring change, and saying
# so in the hold reason is the only honest way to report it.
AC_LABEL_RE = re.compile(
    r"^[\s>*_+-]*(?:\*\*)?\s*(AC|DOD)[-_ .]?(\d+)\b", re.IGNORECASE
)

# Ceiling on the criterion text carried into a binding row, so a ticket whose
# criteria are paragraphs cannot blow the comment body or the receipt.
MAX_AC_TEXT_CHARS = 200


def is_markdown_heading(line: str) -> bool:
    return line.lstrip().startswith("#")


# Multi-word members of AC_HEADING_TEXTS. Only these are eligible for the
# leading-qualifier match, so a heading that merely ends in "ac" or "dod" is
# not mistaken for one that names the section (OMN-18048 review).
AC_HEADING_PHRASES = frozenset(t for t in AC_HEADING_TEXTS if " " in t)


def is_ac_heading(line: str) -> bool:
    """True when ``line`` reads as an 'Acceptance criteria' heading.

    Tolerates ``## Acceptance Criteria``, ``**Acceptance criteria:**``,
    ``### 3. Acceptance criteria`` and bare ``AC``.

    OMN-18048 -- A QUALIFIER MUST NOT HIDE THE HEADING.
    ------------------------------------------------------
    ``AC_HEADING_TEXTS`` is a closed set of nine spellings, and the
    normalisation below did not remove qualifiers. So ``## Acceptance criteria
    (falsifiable)`` -- the house style on operator-authored tickets -- was NOT
    recognised, ``_saw_ac_heading`` was False, and the OMN-16106 whole-body
    fallback fired: the scan ran over the entire description and counted
    whatever unrelated bullets it found. On OMN-18035 that reported **2**
    acceptance criteria for a ticket declaring **four**, and the two were
    bullets from a ``## Fence`` section.

    That is not the over-count the fallback's docstring reasons about. It is a
    count of DIFFERENT ITEMS, so the "over-counting holds a flip" safety
    argument does not apply and both failure directions are reachable.

    Measured (OMN-18048 AC3, 110 ticket descriptions read at full text):
    **14.5%** carry an AC-looking heading this set does not recognise, across
    **12 distinct spellings**. Every one is a recognised base spelling plus a
    qualifier, which is why this strips the qualifier instead of adding twelve
    more strings -- that set would never close.

    Two qualifier positions, both measured in that corpus:

    * TRAILING, usually parenthesised -- ``Acceptance criteria (falsifiable)``,
      ``DoD (per repo)``, ``Definition of Done (dod_evidence)``.
    * LEADING -- ``Falsifiable acceptance criteria`` (5 occurrences). A fix
      that only stripped the trailing form would leave every one of these
      invisible.

    The leading form is gated on the line actually looking like a heading (a
    markdown ``#`` rule, or bold-wrapped). Without that gate an ordinary prose
    sentence ending in the phrase would open the section mid-paragraph, which
    is a real false positive -- it was hit while measuring the corpus.
    """
    raw = line.strip()
    if not raw:
        return False
    looks_like_heading = raw.startswith("#") or (
        raw.startswith("**") and raw.endswith("**")
    )
    text = raw.lstrip("#").strip()
    text = text.strip("*_").strip()
    text = HEADING_ENUM_RE.sub("", text)
    text = text.rstrip(":").strip()
    text = text.strip("*_").strip()
    folded = text.casefold()
    if folded in AC_HEADING_TEXTS:
        return True
    # Trailing qualifier: "acceptance criteria (falsifiable)" -> "acceptance criteria".
    trimmed = TRAILING_QUALIFIER_RE.sub("", folded).strip().rstrip(":").strip()
    if trimmed in AC_HEADING_TEXTS:
        return True
    # Leading qualifier: "falsifiable acceptance criteria". Heading-shaped only,
    # and only against MULTI-WORD spellings.
    #
    # OMN-18048 review [MINOR]: matching this way against the single-token
    # spellings ("ac", "acs", "dod") accepts any heading merely ENDING in one --
    # measured, "## Notes on AC", "## Why we need DoD" and "## Dropping the AC"
    # were all recognised, opening a criteria section over unrelated content.
    # A one-word suffix carries no evidence that the heading NAMES the section
    # rather than mentions it; a multi-word phrase does. "## Acceptance criteria"
    # itself is unaffected -- it matches the exact-membership test above.
    return looks_like_heading and any(
        trimmed.endswith(f" {known}") for known in AC_HEADING_PHRASES
    )


def acceptance_criteria_items(description: str) -> list[str]:
    """Items listed under an acceptance-criteria heading in ``description``.

    The section runs from the heading to the next markdown heading (or the end
    of the body). A non-``#`` heading -- a bold pseudo-heading, say -- does not
    close the section, so the count can be an OVER-count. That direction is
    deliberate: over-counting holds a flip, under-counting releases one.

    OMN-16106 -- WHEN THERE IS NO HEADING AT ALL, THE WHOLE BODY IS THE
    SECTION.
    ----------------------------------------------------------------------
    Requiring a recognised heading made this guard depend on markdown for the
    second time. ``AC_HEADING_TEXTS`` is a closed set of nine spellings; a
    ticket that opens with a prose sentence and then lists its criteria under
    no heading matched none of them, ``items`` came back empty, and BOTH
    counting bounds in :func:`_ac_coverage_gap` sit behind an ``if not items``
    early exit. The guard whose entire job is to notice criteria dod_verify
    never saw returned "no gap" without evaluating a single one.

    Measured: OMN-16025 -- five numbered links under the prose opener
    "Acceptance is the unified plan set 09 5.1 chain", plus the sentence
    "Verified by golden-chain replay on the stability lane" and the explicit
    "must not flip until each is Done". Zero items parsed;
    ``uncovered_acceptance_criteria: []`` in the outcome row of run
    34061364537; flipped Done on 6/12 verified with 6 non-probative.

    So the fallback: no heading anywhere means the whole description is the
    section. That over-counts on a body whose bullets are not all criteria,
    and over-counting is the direction that holds a flip rather than releasing
    one -- the same trade this function already declares above.
    """
    items: list[str] = []
    _saw_ac_heading = any(is_ac_heading(line) for line in description.splitlines())
    # No recognised heading anywhere: read the entire body (see above).
    in_section = not _saw_ac_heading
    for line in description.splitlines():
        if is_ac_heading(line):
            in_section = True
            continue
        if not in_section:
            continue
        if is_markdown_heading(line) and _saw_ac_heading:
            break
        list_match = LIST_ITEM_RE.match(line)
        if list_match:
            text = TASK_MARKER_RE.sub("", list_match.group(1)).strip()
            if text:
                items.append(text)
            continue
        ac_match = AC_ITEM_RE.match(line)
        if ac_match:
            # OMN-18048 review: the emphasis run is captured separately from the
            # AC token and its remainder, so `**AC1** - text` yields the SAME
            # string as the bulleted `- AC1 - text`. Capturing `.*` after the
            # token embedded the closing `**` mid-string, and the two spellings
            # of one criterion then compared and deduped as different items.
            lead, token, rest = ac_match.groups()
            text = f"{token}{rest}".strip()
            if lead:
                text = TRAILING_EMPHASIS_RE.sub("", text).strip()
            if text:
                items.append(text)
    return items


# -- OMN-18362: a criterion a later revision REPLACED is not a live one -------
#
# `acceptance_criteria_items` reads the CURRENT description text and has no
# notion of revision. House style, when a criterion is re-ruled, is to write the
# replacement and keep the old text in the body under an explicit
# `(superseded ...)` qualifier so the history stays legible. Both carry the same
# `AC<n>` label, so the reader returned BOTH and every consumer below counted a
# replaced declaration as one the ticket still has to satisfy.
#
# Measured on OMN-18035: five items parsed, labels AC1 AC2 AC3 AC3 AC4. Two
# consequences, and neither is clearable by any action the author can take.
# `_ac_coverage_gap` compares five listed items against the verified-probative
# count, so a ticket with four criteria and four verified checks reads as one
# criterion short. And in `ac_binding_gap` the replaced item's
# `criterion_pin_hash` can never match the pin its binding was accepted
# against, so AC3 reports stale-pinned or unbound for as long as the ticket
# exists. `documentContentHistory` settles that this is a REPLACEMENT and not an
# authoring slip: the creation revision carries one AC3 and no marker; both the
# duplicate and the marker appear only in the 2026-09-09 revision. That is the
# case the closeout plan's section 6 already names, read from the sweep's side.
#
# THE RULE NARROWS AND CANNOT WIDEN. An item leaves the live set only when BOTH
# halves hold: its own text carries a supersession qualifier ON ITS LABEL, and
# another item carrying the same canonical label is present and is NOT itself so
# marked. So the exclusion can only ever drop a DUPLICATE. It can never drop the
# sole declaration of a label, it can never shrink the set of labels the sweep
# sees, and an unrecognised spelling keeps both items. Dropping a criterion is
# the RELEASING direction -- the one this module refuses everywhere else -- so
# every ambiguous case counts both and holds, exactly as an over-count does.
#
# NOT AN EDIT TO THE READER. `acceptance_criteria_items` stays byte-equivalent:
# its item strings are the hash input `criterion_pin_hash` takes, and the
# change-control criterion reader pins the same shared digest vectors against
# them (`TestTheHashIsTheChangeControlHash`). The exclusion is a named filter
# over its output, so a criterion both readers see still yields one digest.
#
# The qualifier must be ATTACHED TO THE LABEL -- a parenthesised or bracketed
# run opening immediately after it, which is where house style puts it. The word
# appearing in the criterion's body is a criterion that TALKS about supersession
# (this module's own tests are full of them) and is not a claim about itself.
SUPERSEDED_QUALIFIER_RE = re.compile(
    r"^[ \t]*[(\[][^)\]]*\bsupersed(?:e|es|ed|ing)\b[^)\]]*[)\]]",
    re.IGNORECASE,
)


def declares_supersession(item: str) -> bool:
    """True when ``item``'s own label qualifier says a later revision replaced it.

    Scoped to the qualifier that opens immediately after the label, never the
    body: `AC1 (superseded 2026-09-09 -- replaced by the AC1 above)` declares
    itself replaced; `AC1 -- falsified by a superseded receipt being counted`
    does not, and reading the second as the first would drop a live criterion.
    """
    text = item.strip()
    match = AC_LABEL_RE.match(text)
    if not match:
        return False
    return SUPERSEDED_QUALIFIER_RE.match(text[match.end() :]) is not None


def live_acceptance_criteria_items(description: str) -> list[str]:
    """The criteria this ticket still has to satisfy, in description order.

    :func:`acceptance_criteria_items` with replaced declarations removed. See
    the block comment above for why the removal takes two conditions and why it
    is a filter over that function rather than a change to it.
    """
    items = acceptance_criteria_items(description)
    superseded = [
        index for index, item in enumerate(items) if declares_supersession(item)
    ]
    if not superseded:
        return items
    superseded_at = set(superseded)
    # The labels a LIVE item claims. A label absent from this set has no
    # replacement in the body, so its marked item is the only declaration there
    # is and it stays -- holding the ticket rather than releasing it.
    replaced_labels = {
        label
        for index, item in enumerate(items)
        if index not in superseded_at
        for label in (canonical_ac_label(item),)
        if label
    }
    live: list[str] = []
    for index, item in enumerate(items):
        if index in superseded_at and canonical_ac_label(item) in replaced_labels:
            continue
        live.append(item)
    return live


def canonical_ac_label(text: str) -> str:
    """`AC3` / `DOD2` parsed from a criterion or a `binds_ac` entry, or ``""``.

    Both sides of the join go through this one function, so a contract writing
    ``binds_ac: ["ac-3"]`` and a ticket writing ``**AC3**`` bind, and neither
    side can normalise differently from the other.
    """
    match = AC_LABEL_RE.match(text.strip())
    if not match:
        return ""
    return f"{match.group(1).upper()}{int(match.group(2))}"


# -- OMN-18330: the criterion-revision pin, and validating it -----------------
#
# OMN-18236 gave a binding a `criterion_hash`: the sha256 of the criterion text
# the binding was derived or accepted against. Nothing in THIS module read it.
# So a binding accepted against one sentence stayed "bound" after the sentence
# was rewritten into something its check does not prove, and the closer flipped.
# That is a false-close path, and it is the one this leg closes.
#
# THE HASH IS A PORT, NOT A SECOND HASH. The authority is `onex_change_control`
# `src/onex_change_control/validation/ac_criteria.py`
# (`normalise_criterion`, `criterion_hash`, `MAX_CRITERION_HASH_INPUT_CHARS`).
# It is ported rather than imported because that package is a DEV-group
# dependency of this repository, pinned to an immutable rev that predates the
# module, so importing it would make a production predicate depend on a
# test-time install and on a pin bump. The coupling runs the other way too and
# is already stated on that side: OCC's criterion READER is itself a verbatim
# port of `is_ac_heading` / `acceptance_criteria_items` / `canonical_ac_label`
# above. `TestTheHashIsTheChangeControlHash` in
# `tests/unit/nodes/node_evidence_autoclose_sweep_effect/test_omn_18330_criterion_hash.py`
# pins the shared digest vectors that OCC's own tests pin, so a change on either
# side fails with a test naming the other.
#
# WHICH TEXT IS HASHED. The item string `acceptance_criteria_items` returns,
# which is what `ac_binding_gap` already iterates. OCC's `item_text` is the
# same function over the same regexes, so a criterion BOTH readers see yields
# the identical string and the identical digest. The two readers disagree about
# WHICH criteria they see (OCC re-opens at a second criteria section; this one
# stops at the first non-criteria heading), and that disagreement cannot produce
# a spurious mismatch here: a criterion this reader never reads is one this leg
# never asks about.
CRITERION_WHITESPACE_RUN_RE = re.compile(r"\s+")

#: Ceiling on the text fed to the hash, so a pathological body cannot make the
#: digest depend on how much of it somebody pasted. Must equal OCC's
#: `MAX_CRITERION_HASH_INPUT_CHARS`; the shared-vector test pins that.
MAX_CRITERION_HASH_INPUT_CHARS = 4000


def normalise_criterion(text: str) -> str:
    """The criterion text the pin hash is taken over.

    Whitespace runs collapse to one space and the ends are stripped, so
    re-wrapping a paragraph or re-indenting a bullet is NOT a rewrite. Nothing
    else is normalised — not case, not punctuation, not markdown emphasis —
    because each of those can change what a criterion requires. A negation, a
    changed threshold and a changed modal verb all produce a different digest,
    which is the entire point.
    """
    return CRITERION_WHITESPACE_RUN_RE.sub(" ", text).strip()[
        :MAX_CRITERION_HASH_INPUT_CHARS
    ]


def criterion_pin_hash(text: str) -> str:
    """The sha256 hex digest identifying this criterion's current revision."""
    return hashlib.sha256(normalise_criterion(text).encode("utf-8")).hexdigest()


def pinned_criterion_hashes(verdict: dict[str, object]) -> dict[str, tuple[str, ...]]:
    """``{label: (pinned criterion hash, ...)}`` from the verdict's check records.

    A label ABSENT from the returned mapping carries no pin. That is 67 of the
    68 contracts that declare ``binds_ac`` as of 2026-09-13, and it keeps
    today's behaviour exactly: a hand-authored ``binds_ac`` is the evidence
    author speaking, which is the acceptance the rule asks for, and this leg
    does not widen the hold onto it. Widening there is named Out of scope on
    OMN-18330 and would hold the entire corpus on a pin that does not exist yet.

    A label PRESENT with an EMPTY tuple carries a binding record whose
    ``criterion_hash`` is missing or unreadable. That is a different fact and it
    does not release: a record asserting an acceptance while declining to say
    which revision was accepted is unvalidated, and unvalidated holds.

    Several records may pin one label -- a re-acceptance appended beside the
    original, which is the only shape the OCC append-only validator permits, and
    two evidence items may each bind the same criterion. Every pin is collected
    and ANY match releases, because "this criterion's current text was accepted"
    is the fact being asked about.

    WHY THE VERDICT AND NOT THE CONTRACT. The pin lives on the contract's
    ``dod_evidence[].ac_bindings[]``, and this node could fetch it. It does not,
    for the reason omnimarket states where it carries ``binds_ac`` itself: this
    sweep runs on a runner with no contract checkout, and a second contract
    parser would be a second truth that drifts from the verifier's. The verifier
    already resolves, pins and reads the contract, so it is the only place the
    pin can be reported from without adding a second reader. Reading it here
    would also put a network call on the flip path of an armed closer, where a
    transient failure has to choose between a false hold and a false flip.

    CONSEQUENCE, STATED RATHER THAN IMPLIED: this half of the join is live only
    once the verifier carries the key. `node_dod_verify` reads ``ac_bindings``
    today to compute ``draft_binds_ac`` and discards the hashes; carrying them
    forward is a one-field omnimarket change in the same surface, and it belongs
    with the autobinder work that will start producing accepted bindings at
    volume. Until it lands, one live contract records a pin and the predicate
    below is proven by fixture rather than by corpus. What this closes is the
    design hole -- the closer had no way to learn a criterion had moved, and now
    it does, unskippably, before the binding counts.
    """
    checks = verdict.get(dod_verify_checks_key)
    if not isinstance(checks, list):
        return {}
    pinned: dict[str, list[str]] = {}
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        raw = entry.get(check_ac_binding_hashes_key)
        if not isinstance(raw, dict):
            continue
        for declared, digest in raw.items():
            label = canonical_ac_label(str(declared))
            if not label:
                continue
            slot = pinned.setdefault(label, [])
            value = str(digest or "").strip().lower()
            if value and value not in slot:
                slot.append(value)
    return {label: tuple(digests) for label, digests in pinned.items()}


def declared_ac_bindings(
    verdict: dict[str, object],
) -> tuple[
    bool, dict[str, tuple[tuple[str, str, str], ...]], dict[str, tuple[str, ...]]
]:
    """Bindings the verdict's checks DECLARE, keyed by canonical AC label.

    Returns ``(field_present, bindings, drafts)``. Each binding value is a
    tuple of ``(check_id, status, proof_class)`` for every check naming that
    label -- including the ones that did NOT verify, so a declared-but-unproven
    binding is visible in the table rather than silently absent.

    ``field_present`` is True as soon as ANY check carries the key at all,
    even as an empty list. That distinction is the whole reason it is
    returned: an ABSENT key means the verifier cannot report bindings (it
    predates this change), an EMPTY one means the contract was read and
    declares none. Both hold the flip; only the second is a gap the ticket's
    author can close.

    OMN-18238 -- A PROPOSAL IS NOT A BINDING.
    -----------------------------------------
    A label the check also names in ``draft_binds_ac`` is a PROPOSAL awaiting
    acceptance. It is excluded from ``bindings`` and reported in ``drafts``, so the
    criterion stays unbound and the hold can say WHY in words that match the
    repair. The cheap way to make bindings plentiful is to let a machine guess
    a criterion from a matching check name, and a passing check with a matching
    name is not proof of the criterion it names -- so a machine may propose and
    a person decides.

    The exclusion narrows and never widens. A draft label the check does not
    also claim in ``binds_ac`` is ignored outright: ``draft_binds_ac`` cannot
    introduce a criterion, only demote one.
    """
    checks = verdict.get(dod_verify_checks_key)
    if not isinstance(checks, list):
        return False, {}, {}
    field_present = False
    collected: dict[str, list[tuple[str, str, str]]] = {}
    drafted: dict[str, list[str]] = {}
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        raw = entry.get(check_binds_ac_key)
        if raw is None:
            continue
        field_present = True
        if not isinstance(raw, list):
            continue
        check_id = str(entry.get(check_id_key) or "")
        status = str(entry.get(check_status_key) or "")
        proof_class = str(entry.get(check_proof_class_key) or "")
        raw_drafts = entry.get(check_draft_binds_ac_key)
        draft_labels: set[str] = set()
        if isinstance(raw_drafts, list):
            for proposed in raw_drafts:
                label = canonical_ac_label(str(proposed))
                if label:
                    draft_labels.add(label)
        for declared in raw:
            label = canonical_ac_label(str(declared))
            if not label:
                continue
            if label in draft_labels:
                drafted.setdefault(label, []).append(check_id)
                continue
            collected.setdefault(label, []).append((check_id, status, proof_class))
    return (
        field_present,
        {label: tuple(rows) for label, rows in collected.items()},
        {label: tuple(ids) for label, ids in drafted.items()},
    )


#: Positive evidence that a criterion asserts LIVE STATE — a condition, a
#: row, a count, a config value read from the running system. Every entry is
#: drawn from a criterion that actually exists in the corpus, not invented.
STATE_MARKER_RE: re.Pattern[str] = re.compile(
    r"""(?xi)
      \bread[\s-]?back\b
    | \breadback\b
    | \b\d+\s+rows?\b
    | \brows?\s+carrying\b
    | \b\d+\s+occurrences?\b
    | \bno\s+occurrences?\b
    # OMN-18135 follow-up, measured against OMN-17771's REAL criteria: the
    # first cut recognised only 2 of its 5, so the ticket the ruling names as
    # its worked example would still have held. Every phrase below is lifted
    # from one of those criteria, which is the standing rule for this set --
    # a marker earns its way in by appearing in a criterion that exists, not
    # by seeming plausible.
    | \bzero\b[^.]{0,80}\boccurrences?\b   # "Zero `client_id=x` ... occurrences"
    | \bcheckers?\b[^.]{0,24}\bgreen\b     # "`beta-layout` checkers green"
    | \bexists\s+on\s+the\b                # "a client that exists on the plane"
    | \bmerged\s+to\s+`?\w                 # "Merged to `main` and read back"
    | \bHTTP\s+\d{3}\b                     # "returns HTTP 200 with a form"
    | \bis\s+(running|ready|healthy|present|absent|enabled|disabled)\b
    | \breaches\s+(running|ready)\b
    | \b\d+\s+restarts?\b
    | \breturns?\b
    | \bresponds?\b
    | \bserves?\b
    | \bcontains?\b
    | \bdigest\b
    | \bconfig(uration)?\s+value\b
    | \bon\s+the\s+(live|running)\b
    | \b(live|running)\s+(plane|cluster|lane|realm|database|system|repository)\b
    """,
)

#: Language that asserts what the CODE DOES. Vetoes a state marker, because a
#: criterion carrying both is the ambiguous case and ambiguity must hold.
BEHAVIOUR_MARKER_RE: re.Pattern[str] = re.compile(
    r"""(?xi)
      \btests?\b
    | \bred[\s-]first\b
    | \bfails?\s+today\b
    | \brefuses?\b
    | \braises?\b
    | \bretr(y|ies|ied)\b
    | \bstops?\s+after\b
    | \bhandler\b
    | \bsuite\b
    """,
)


def criterion_is_state_shaped(criterion: str) -> bool:
    """Whether a readback may discharge this criterion.

    True only on POSITIVE evidence of live state and in the ABSENCE of
    behaviour language. Both conditions, never one: see the module comment
    above for why the veto wins ties.
    """
    if BEHAVIOUR_MARKER_RE.search(criterion) is not None:
        return False
    return STATE_MARKER_RE.search(criterion) is not None


def has_ac_heading(description: str) -> bool:
    """Whether the body carries a recognised acceptance-criteria heading."""
    return any(is_ac_heading(line) for line in description.splitlines())


def ac_binding_gap(
    description: str,
    verdict: dict[str, object],
    ticket_id: str,
) -> tuple[str, tuple[str, ...], tuple[ModelAcBindingRow, ...]]:
    """Decide whether every parsed criterion binds to a VERIFIED check.

    Returns ``(reason, unbound, rows)``. An empty ``reason`` releases the
    flip and ``rows`` then carry the bindings that released it.

    Two shapes hold, and they are reported differently because they tell the
    author to do different things:

    1. At least one parsed criterion is declared by no VERIFIED check. Named
       individually -- this is the fact the counters could not produce.
    2. NO criterion parses at all. Today's counting rules RELEASE that case
       through an ``if not items: return "", ()`` early exit, which reads
       "nothing written down" as "nothing to prove". A ticket the closer
       cannot read criteria from is a ticket it cannot say anything about, so
       it holds.

    ``verified`` is the only status that binds. ``non_probative`` is a
    verdict but not a proof (OMN-15391), ``skipped`` never ran, ``failed``
    would have been refused upstream -- none of them discharges a criterion,
    and each appears in the table with its status so the near-miss is legible.

    OMN-18330 -- THE PIN IS VALIDATED BEFORE THE BINDING COUNTS.
    -----------------------------------------------------------
    The pins come off the verdict's own check records, via
    :func:`pinned_criterion_hashes`, and are resolved INSIDE this function
    rather than handed in. There is deliberately no parameter and no caller
    switch: a pin validation a caller can forget to pass is one that gets
    skipped, which is the exact failure this leg exists to remove.

    A label that carries a pin must have one matching the criterion's text AS
    THE TICKET READS NOW, or it does not discharge -- the binding was accepted
    against a sentence that no longer exists.

    It NARROWS and never widens. A label carrying NO pin binds exactly as it
    did before: 68 live contracts declare ``binds_ac``, 67 of them carry no
    binding record at all, every one hand-authored, and holding them on a pin
    that does not exist yet is named Out of scope on OMN-18330.
    """
    pinned_hashes = pinned_criterion_hashes(verdict)
    contract = f"contracts/{ticket_id}.yaml"
    field_present, bindings, drafts = declared_ac_bindings(verdict)
    items = tuple(live_acceptance_criteria_items(description))

    if not items:
        return (
            "No acceptance criterion could be parsed from this ticket's Linear "
            "description, so there is nothing for the OCC contract's checks to "
            "be bound TO and no statement this sweep can make about coverage. "
            "A green tally over unbindable criteria is an arithmetic identity, "
            "not evidence. Write the criteria under an `Acceptance criteria` "
            "(or `Definition of done`) heading, label them `AC1`, `AC2`, ..., "
            f"and declare each one in `{contract}` via `binds_ac` on the "
            "evidence item that proves it.",
            (),
            (),
        )

    rows: list[ModelAcBindingRow] = []
    unbound: list[str] = []
    #: OMN-18135 AC4: criteria whose ONLY verified checks are readbacks and
    #: whose text is not state-shaped. Tracked separately from `unbound` so
    #: the hold can name the bar rather than say "declared by nothing", which
    #: would be false and would send the author to fix the wrong thing.
    readback_blocked: list[str] = []
    #: OMN-18330. Criteria whose binding record pins a DIFFERENT revision of
    #: the criterion text than the ticket carries now, and criteria whose
    #: record declines to say which revision it pinned at all. Tracked apart
    #: from `unbound` and from each other because the three repairs differ:
    #: write a binding, re-accept the existing one against the new wording, or
    #: record the hash the acceptance was taken against.
    stale_pinned: list[str] = []
    unpinned: list[str] = []
    for item in items:
        text = item[:MAX_AC_TEXT_CHARS]
        label = canonical_ac_label(item)
        declared = bindings.get(label, ()) if label else ()
        # OMN-18330. The pin is validated against the criterion AS IT READS
        # NOW, before any status or proof-class question, because a binding
        # accepted against a sentence that no longer exists is not evidence
        # about this criterion whatever its check did. A label absent from
        # `pinned_hashes` carries no record and is not touched here.
        pin_stale = False
        pin_absent = False
        if label and label in pinned_hashes:
            pins = pinned_hashes[label]
            if not pins:
                pin_absent = True
            elif criterion_pin_hash(item) not in pins:
                pin_stale = True
        verified_rows = tuple(
            row for row in declared if row[1] == CHECK_STATUS_VERIFIED
        )
        # OMN-18135 AC4, and this half is a TIGHTENING. Until now binding
        # keyed on status alone and never looked at proof class, so a readback
        # silently discharged a criterion asserting what the code DOES. The
        # ruling names that: readbacks are admissible for live STATE only.
        #
        # Scoped deliberately to readbacks. A criterion proved by a
        # merge-state, surrogate or indeterminate check binds exactly as it
        # did — narrowing those is a different argument nobody has made, and
        # making it here would retroactively un-close tickets that flipped on
        # that basis.
        readback_only = bool(verified_rows) and all(
            row[2] == CHECK_PROOF_CLASS_READBACK for row in verified_rows
        )
        proving: tuple[tuple[str, str, str], ...]
        if pin_stale or pin_absent:
            # OMN-18330. Named FIRST among the disqualifications: when the pin
            # is stale the readback question is moot, and reporting "no
            # behaviour check" about a criterion whose text moved sends the
            # author to bind a check to a sentence nobody has re-read.
            (stale_pinned if pin_stale else unpinned).append(label or text)
            proving = ()
        elif readback_only and not criterion_is_state_shaped(item):
            readback_blocked.append(canonical_ac_label(item) or text)
            proving = ()
        else:
            proving = verified_rows
        if proving:
            rows.extend(
                ModelAcBindingRow(
                    acceptance_criterion=text,
                    label=label,
                    evidence_check=check_id,
                    status=EnumAcBindingCheckStatus.from_verdict(status),
                    proof_class=proof_class,
                    bound=True,
                )
                for check_id, status, proof_class in proving
            )
            continue
        # Unbound. Every non-verifying declaration is still recorded, because
        # "declared by a check that did not verify" and "declared by nothing"
        # are different repairs.
        rows.extend(
            ModelAcBindingRow(
                acceptance_criterion=text,
                label=label,
                evidence_check=check_id,
                status=EnumAcBindingCheckStatus.from_verdict(status),
                proof_class=proof_class,
                bound=False,
            )
            for check_id, status, proof_class in declared
        )
        if not declared:
            rows.append(
                ModelAcBindingRow(acceptance_criterion=text, label=label, bound=False)
            )
        unbound.append(text)

    if not unbound:
        return "", (), tuple(rows)

    if not field_present:
        why = (
            "dod_verify's verdict carries no `binds_ac` on any check, so this "
            "verifier cannot report which criterion any check covers. Refusing "
            "to infer it: a count that happens to line up is not a mapping."
        )
    else:
        why = (
            f"`{contract}` declares no verified probative check for them. A "
            "check is bound to a criterion only when the contract's evidence "
            "item names it in `binds_ac` AND that check verified -- a "
            "non-probative or skipped declaration is a claim, not a proof."
        )
    readback_note = (
        (
            " OMN-18135: "
            + ", ".join(readback_blocked[:MAX_UNCOVERED_LISTED])
            + " IS declared by a verified check, but only by a READBACK — a "
            "command that read live state and asserted on it. A readback "
            "discharges a criterion asserting live STATE (a condition, a row, "
            "a count, a config value); this criterion reads as asserting what "
            "the code DOES, which needs a test runner or the ONEX CLI. Either "
            "bind a behaviour check, or reword the criterion to state the live "
            "fact it actually wants."
        )
        if readback_blocked
        else ""
    )
    # OMN-18238. A criterion whose only declaration is a PROPOSAL is unbound,
    # and saying so is not the same statement as "declared by nothing". The
    # repair differs: one needs a binding written, the other needs an existing
    # one reviewed and accepted. A hold that conflated them would send the
    # author to write a binding that is already sitting there.
    proposed = tuple(
        dict.fromkeys(
            label
            for text in unbound
            for label in (canonical_ac_label(text),)
            if label and label in drafts
        )
    )
    more_proposals = len(proposed) - MAX_UNCOVERED_LISTED
    proposal_suffix = f" and {more_proposals} more" if more_proposals > 0 else ""
    proposal_note = (
        (
            " OMN-18238: "
            + ", ".join(proposed[:MAX_UNCOVERED_LISTED])
            + proposal_suffix
            + " IS declared, but only as a PROPOSAL — an autobound draft "
            "awaiting acceptance. A machine may propose a binding; it may not decide "
            "one, because a passing check whose name resembles a criterion is "
            "not proof of the criterion it names. Accept the proposal on the "
            "contract's evidence item (record who accepted it and when) and "
            "this criterion binds."
        )
        if proposed
        else ""
    )
    # OMN-18330. A criterion whose text CHANGED after its binding was accepted,
    # and one whose record never said which revision it was accepted against.
    # Both are named apart from "declared by nothing" and from each other,
    # because the repair differs in each case and a hold that conflates them
    # sends the author to fix something that is not broken.
    more_stale = len(stale_pinned) - MAX_UNCOVERED_LISTED
    stale_note = (
        (
            " OMN-18330: "
            + ", ".join(stale_pinned[:MAX_UNCOVERED_LISTED])
            + (f" and {more_stale} more" if more_stale > 0 else "")
            + " IS declared by a binding, but the binding was accepted against "
            "a DIFFERENT revision of this criterion — the criterion's text on "
            "this ticket has changed since, so its pinned `criterion_hash` no "
            "longer matches what the criterion now says. A check that proved "
            "the old wording is not evidence about the new one. Re-read the "
            f"criterion, and re-accept the binding in `{contract}` against its "
            "current text (a fresh `criterion_hash`, acceptor and timestamp)."
        )
        if stale_pinned
        else ""
    )
    more_unpinned = len(unpinned) - MAX_UNCOVERED_LISTED
    unpinned_note = (
        (
            " OMN-18330: "
            + ", ".join(unpinned[:MAX_UNCOVERED_LISTED])
            + (f" and {more_unpinned} more" if more_unpinned > 0 else "")
            + " carries a binding record with NO readable `criterion_hash`, so "
            "which revision of the criterion it was accepted against cannot be "
            "established at all. That is unvalidated rather than stale, and it "
            "does not discharge the criterion. Record the hash of the criterion "
            "text the acceptance was taken against on that binding record."
        )
        if unpinned
        else ""
    )
    unlabelled = sum(1 for text in unbound if not canonical_ac_label(text))
    labelling = (
        f" {unlabelled} of them carry no `AC<n>`/`DoD<n>` label at all, so "
        "nothing in the contract can point at them until the ticket body "
        "labels them."
        if unlabelled
        else ""
    )
    fallback = (
        " NOTE: this description carries no acceptance-criteria heading, so "
        "the whole body was read as the criteria section (OMN-16106) and this "
        "list may over-count. Over-counting holds a flip; under-counting "
        "releases one."
        if not has_ac_heading(description)
        else ""
    )
    # NAME them. A hold whose reason states only a ratio is the same
    # unreadable arithmetic this leg exists to replace: the whole finding is
    # WHICH criterion nothing proves. Labelled criteria are named by label;
    # unlabelled ones by a bounded prefix of their own text, because that is
    # the only handle they have.
    named = ", ".join(
        canonical_ac_label(text) or f"'{text[:60]}'"
        for text in unbound[:MAX_UNCOVERED_LISTED]
    )
    return (
        f"{len(unbound)} of {len(items)} acceptance criterion(s) in this "
        f"ticket's description are bound to NO verified probative check in "
        f"`{contract}`: {named}. {why}{proposal_note}{stale_note}"
        f"{unpinned_note}{readback_note}{labelling}{fallback}",
        tuple(unbound),
        tuple(rows),
    )


def check_records(verdict: dict[str, object]) -> tuple[dict[str, object], ...]:
    """The per-check records, or nothing when the payload cannot be read.

    Every consumer of `checks` in this module goes through here so that an
    unreadable shape means the same thing in all of them: no attribution, no
    hold, no fingerprint contribution — the pre-existing behaviour, never a
    silent swallow.
    """
    checks = verdict.get(dod_verify_checks_key)
    if not isinstance(checks, list):
        return ()
    return tuple(check for check in checks if isinstance(check, dict))


def check_status(check: dict[str, object]) -> str:
    return str(check.get(check_status_key, "")).strip().lower()


def verdict_is_all_verified(verdict: Mapping[str, object]) -> bool:
    """Whether the verdict's own counters say every verdict-bearing check passed.

    Both dod_verify's own terminal status and the arithmetic must agree. The
    arithmetic is the stricter of the two: dod_verify reports VERIFIED when
    *some* checks were skipped (as long as not all of them were), and a skipped
    check is not proof of anything. OMN-16821: ``non_probative`` is a verdict
    but not a proof, so it joins the numerator; ``verified_count > 0`` keeps an
    all-provenance contract from satisfying the equality by arithmetic alone.
    """
    total_checks = as_int(verdict.get("total_checks"))
    verified_count = as_int(verdict.get("verified_count"))
    failed_count = as_int(verdict.get("failed_count"))
    non_probative_count = as_int(verdict.get(dod_verify_non_probative_key))
    verify_status = str(verdict.get("status") or "").strip().lower()
    return (
        verify_status == DOD_VERIFY_STATUS_VERIFIED
        and total_checks > 0
        and failed_count == 0
        and verified_count > 0
        and verified_count + non_probative_count == total_checks
    )


def evaluate_done_write_receipt(
    *,
    ticket_id: str,
    description: str,
    verdict: Mapping[str, object] | None,
) -> ModelDoneWriteDecision:
    """Decide whether a Done write may proceed. Pure and fail-closed.

    ``verdict`` is the dod_verify verdict dict (see
    :func:`extract_dod_verify_verdict`); ``None`` means no verdict was reached
    and refuses. ``description`` is the ticket's CURRENT description, read
    live: criteria are judged as the ticket reads now.
    """
    if verdict is None:
        return ModelDoneWriteDecision(
            allowed=False,
            reason=(
                f"no dod_verify verdict for {ticket_id}: a Done write needs a "
                "verified dod_verify receipt that binds every acceptance "
                "criterion through binds_ac (OMN-20368). A merged PR is "
                "necessary and never sufficient."
            ),
        )
    if not verdict_is_all_verified(verdict):
        return ModelDoneWriteDecision(
            allowed=False,
            reason=(
                f"dod_verify for {ticket_id} is not a PASS: status="
                f"{str(verdict.get('status') or '')!r}, total_checks="
                f"{as_int(verdict.get('total_checks'))}, verified_count="
                f"{as_int(verdict.get('verified_count'))}, failed_count="
                f"{as_int(verdict.get('failed_count'))}, non_probative_count="
                f"{as_int(verdict.get(dod_verify_non_probative_key))} (OMN-20368)."
            ),
        )
    reason, unbound, rows = ac_binding_gap(description, dict(verdict), ticket_id)
    if reason:
        return ModelDoneWriteDecision(
            allowed=False, reason=reason, unbound=unbound, rows=rows
        )
    return ModelDoneWriteDecision(allowed=True, rows=rows)


__all__ = [
    "dod_verify_non_probative_key",
    "DOD_VERIFY_STATUS_VERIFIED",
    "ac_binding_gap",
    "as_int",
    "canonical_ac_label",
    "check_records",
    "check_status",
    "criterion_is_state_shaped",
    "evaluate_done_write_receipt",
    "extract_dod_verify_verdict",
    "has_verified_bound_check",
    "live_acceptance_criteria_items",
    "verdict_is_all_verified",
]
