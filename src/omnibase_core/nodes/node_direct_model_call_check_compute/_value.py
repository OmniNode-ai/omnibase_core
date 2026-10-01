# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Abstract values: what an expression may evaluate to, as far as the gate needs to know (OMN-20295)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from omnibase_core.nodes.node_direct_model_call_check_compute._constants import (
    _TEXT_CAP,
    _UNKNOWN,
)


@dataclass(frozen=True)
class _Val:
    """What an expression may evaluate to, as far as the gate needs to know.

    ``texts`` are the possible string renderings, with ``{?}`` for an unknown
    piece. ``labels`` carry ``base_url`` (derived from a base-URL source) and
    ``python`` (the running interpreter). ``keys`` are dict keys when the value
    is a mapping. ``seq`` holds the elements of a literal list or tuple.
    ``params`` names the enclosing function's parameters the value derives from.
    """

    texts: frozenset[str] = frozenset()
    labels: frozenset[str] = frozenset()
    keys: frozenset[str] = frozenset()
    seq: tuple[_Val, ...] | None = None
    params: frozenset[str] = frozenset()


_EMPTY: Final[_Val] = _Val()


_OPAQUE: Final[_Val] = _Val(texts=frozenset({_UNKNOWN}))


def _cap(texts: Iterable[str]) -> frozenset[str]:
    ordered = sorted(set(texts))
    return frozenset(ordered[:_TEXT_CAP])


def _join(*vals: _Val) -> _Val:
    present = [v for v in vals if v is not _EMPTY]
    if not present:
        return _EMPTY
    if len(present) == 1:
        return present[0]
    seqs = [v.seq for v in present if v.seq is not None]
    seq: tuple[_Val, ...] | None = None
    if seqs:
        width = max(len(s) for s in seqs)
        seq = tuple(_join(*(s[i] for s in seqs if i < len(s))) for i in range(width))
    return _Val(
        texts=_cap(t for v in present for t in v.texts),
        labels=frozenset(lab for v in present for lab in v.labels),
        keys=frozenset(k for v in present for k in v.keys),
        seq=seq,
        params=frozenset(p for v in present for p in v.params),
    )


def _concat(*vals: _Val) -> _Val:
    texts: set[str] = {""}
    for val in vals:
        pieces = val.texts or frozenset({_UNKNOWN})
        texts = {left + right for left in texts for right in pieces}
        if len(texts) > _TEXT_CAP:
            texts = set(sorted(texts)[:_TEXT_CAP])
    return _Val(
        texts=frozenset(texts),
        labels=frozenset(lab for v in vals for lab in v.labels),
        keys=frozenset(),
        params=frozenset(p for v in vals for p in v.params),
    )


def _flatten(val: _Val) -> _Val:
    """Drop the sequence structure, keeping every element's facts."""
    if val.seq is None:
        return val
    return _Val(
        texts=val.texts,
        labels=val.labels | frozenset(lab for e in val.seq for lab in e.labels),
        keys=val.keys,
        params=val.params | frozenset(p for e in val.seq for p in e.params),
    )


def _substitute(val: _Val, binding: dict[str, _Val]) -> _Val:
    """Replace parameter references in a callee's value by the caller's values."""
    seq = (
        tuple(_substitute(e, binding) for e in val.seq) if val.seq is not None else None
    )
    own = _Val(texts=val.texts, labels=val.labels, keys=val.keys, seq=seq)
    bound = [binding[p] for p in sorted(val.params) if p in binding]
    if not bound:
        return own
    if not val.texts and not val.labels and not val.keys and seq is None:
        return _join(*bound)
    return _join(own, *bound)
