# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure substantive-report-text validation (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's
``validate_substantive_report_text`` (originally
``steel_onslaught.contracts.dispatch_report``). Lives in ``utils/`` rather
than ``models/dispatch/report/`` so the dispatch report models
(``omnibase_core.models.dispatch.report``) can call it from a
``@field_validator`` without a ``models -> validation`` import back-edge --
the same relocation precedent as ``util_name_validation``/``util_hex_color``/
``util_topic_suffix`` under OMN-14331 (epic OMN-3210). Every function here is
pure (standard library ``re`` only); nothing imports
``omnibase_core.models`` or any higher layer.

Background (the failure this module exists to close). On 2026-07-25, seven
dispatched agents completed correct underlying work and then returned bare
acknowledgements -- ``"Done."``, ``"Task complete."``,
``"No further action taken."`` -- in place of any typed result. The worst
class filled a required 4-field schema with the literal string ``"test"`` in
every field, and it VALIDATED, because the schema checked shape only (field
present, field is a string) and never checked content. Shape-only validation
and prose exhortation ("please return a real report") are both proven
insufficient by that data.

``validate_substantive_report_text`` rejects placeholder literals (``"test"``,
``"todo"``, ``"placeholder"``, ``"lorem"``, ...), bare-acknowledgement
literals (``"done"``, ``"task complete"``, ``"no further action taken"``,
...), any report under ``_MIN_SUBSTANTIVE_LENGTH`` characters, and repetitive
low-content padding used to defeat the length floor without saying anything
-- a banned literal repeated with separators past the minimum length
(``"Done. Done. Done. Done. Done. Done. Done."``) or a short unit repeated
with no separators at all (keyboard-mash filler like
``"asdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdf"``) are both rejected, not
just the exact single-literal case.
"""

from __future__ import annotations

import re

__all__ = ["validate_substantive_report_text"]

_MIN_SUBSTANTIVE_LENGTH = 40

# Exact-match (post-normalization) literal placeholder fills. Deliberately a
# closed set of known-bad literals, not a substring/contains check -- a real
# report that happens to use the word "test" in a sentence (e.g. "ran the
# integration test suite") must never be flagged.
_PLACEHOLDER_LITERALS = frozenset(
    {
        "test",
        "todo",
        "placeholder",
        "lorem",
        "lorem ipsum",
        "n/a",
        "na",
        "tbd",
        "xxx",
        "fixme",
        "wip",
        "asdf",
        "foo",
        "foo bar",
        "example",
        "sample",
        "string",
        "changeme",
        "unknown",
    }
)

# Exact-match (post-normalization) bare-acknowledgement fills -- the class
# proven in the 2026-07-25 incident: real work happened, but the returned
# report carries no typed result content at all.
_BARE_ACKNOWLEDGEMENT_LITERALS = frozenset(
    {
        "done",
        "task complete",
        "task completed",
        "no further action taken",
        "no further action needed",
        "no further action required",
        "complete",
        "completed",
        "finished",
        "all done",
        "ok",
        "okay",
        "ack",
        "acknowledged",
        "confirmed",
        "will do",
        "sounds good",
        "got it",
        "on it",
        "yes",
        "no",
        "nothing further",
        "n/a - complete",
    }
)


def _normalize_for_literal_match(value: str) -> str:
    """Lowercase, strip whitespace, and strip trailing sentence punctuation.

    ``"Done."`` and ``"done"`` must compare equal; matching stays exact
    (never substring), so a genuine report that mentions "test" or "done"
    inside a longer sentence is never flagged.
    """
    stripped = value.strip().lower()
    return stripped.rstrip(".!? \t").strip()


# Splits on one-or-more sentence-terminating characters, used by the
# repeated-padding detector below to find "Done. Done. Done." style repeats
# of a single literal that individually normalize past the exact-match check
# (the whole string ``"done. done. done."`` is not itself equal to ``"done"``)
# but are transparently the same banned literal repeated to pad length.
_SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?]+")

# A blob is treated as degenerate keyboard-mash filler once a repeating unit
# of at most this many characters accounts for this fraction of the
# alphanumeric-only content -- e.g. "asdfasdfasdf..." (unit "asdf", period 4)
# covers 100% of itself. Kept conservative (short unit, high coverage, >=3
# repeats) so real prose is never caught by accidental short repeats.
_MAX_DEGENERATE_UNIT_LENGTH = 16
_MIN_DEGENERATE_COMPACT_LENGTH = 12
_MIN_DEGENERATE_COVERAGE_RATIO = 0.9
_MIN_DEGENERATE_REPEATS = 3


def _is_repetitive_padding(stripped: str) -> bool:
    """True if ``stripped`` is content-free padding used to defeat the
    length minimum, rather than genuine substantive text.

    Two independent detectors, because the two adversarial classes look
    nothing alike on the wire:

    1. A single word/phrase repeated with sentence-style separators, e.g.
       ``"Done. Done. Done. Done. Done. Done. Done."`` -- splitting on
       ``.``/``!``/``?`` yields >=3 non-empty segments that all normalize to
       the exact same text. This catches a banned literal (or any other
       single phrase) padded past ``_MIN_SUBSTANTIVE_LENGTH`` by repetition,
       which the whole-string exact-literal match above cannot see because
       the padded string as a whole is never equal to the bare literal.
    2. A short unit repeated with NO separators at all, e.g. keyboard-mash
       filler like ``"asdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdf"`` --
       there is nothing to split on, so this checks whether the
       alphanumeric-only content is (almost) entirely a short repeating
       unit.
    """
    segments = [
        seg.strip() for seg in _SENTENCE_SPLIT_PATTERN.split(stripped) if seg.strip()
    ]
    if len(segments) >= _MIN_DEGENERATE_REPEATS:
        normalized_segments = {seg.lower() for seg in segments}
        if len(normalized_segments) == 1:
            return True

    compact = re.sub(r"[^a-z0-9]", "", stripped.lower())
    if len(compact) >= _MIN_DEGENERATE_COMPACT_LENGTH:
        max_period = min(
            _MAX_DEGENERATE_UNIT_LENGTH, len(compact) // _MIN_DEGENERATE_REPEATS
        )
        for period in range(1, max_period + 1):
            unit = compact[:period]
            repeats = len(compact) // period
            if repeats < _MIN_DEGENERATE_REPEATS:
                continue
            covered = unit * repeats
            if compact.startswith(covered) and len(covered) / len(compact) >= (
                _MIN_DEGENERATE_COVERAGE_RATIO
            ):
                return True
    return False


def validate_substantive_report_text(
    value: str, *, field_name: str = "report text"
) -> str:
    """Reject placeholder literals, bare acknowledgements, and short filler.

    Raises ``ValueError`` with a SPECIFIC, distinguishable reason per
    violation class -- callers (pydantic ``field_validator``s on the
    dispatch report models, and any future free-text report field) get one
    shared, tested implementation rather than three ad hoc regexes
    copy-pasted per field.

    Every raise below is ``# error-ok:`` because this is a pydantic
    field_validator helper one call frame removed from the decorated method:
    it must raise ``ValueError`` (the type pydantic wraps as
    ``ValidationError``), not ``OnexError``, which would propagate uncaught.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError(  # error-ok: pydantic field_validator helper -- see docstring above.
            f"{field_name} is empty or whitespace-only"
        )

    normalized = _normalize_for_literal_match(stripped)
    if normalized in _PLACEHOLDER_LITERALS:
        raise ValueError(  # error-ok: pydantic field_validator helper -- see above.
            f"{field_name} is the literal placeholder value {stripped!r} -- "
            "not a substantive report"
        )
    if normalized in _BARE_ACKNOWLEDGEMENT_LITERALS:
        raise ValueError(  # error-ok: pydantic field_validator helper -- see above.
            f"{field_name} is a bare acknowledgement ({stripped!r}) with no typed result content"
        )
    if _is_repetitive_padding(stripped):
        raise ValueError(  # error-ok: pydantic field_validator helper -- see above.
            f"{field_name} is repetitive low-content padding ({stripped!r}) -- a short "
            "literal or unit repeated to defeat the length minimum, not a substantive report"
        )
    if len(stripped) < _MIN_SUBSTANTIVE_LENGTH:
        raise ValueError(  # error-ok: pydantic field_validator helper -- see above.
            f"{field_name} is only {len(stripped)} chars (minimum {_MIN_SUBSTANTIVE_LENGTH}) -- "
            "too short to be a substantive report"
        )
    return stripped
