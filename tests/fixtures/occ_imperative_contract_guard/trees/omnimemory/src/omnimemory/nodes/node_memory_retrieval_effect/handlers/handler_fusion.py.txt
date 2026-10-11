# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Rank fusion for hybrid retrieval (OMN-16765).

Combines the ranked output of the semantic (Qdrant) and full-text (Postgres)
legs into a single ordering, behind the existing retrieval protocol.

Two concerns are kept separate on purpose:

* :func:`fuse_rrf` is **pure rank fusion**. It consumes ranks and nothing else.
  The two legs produce numerically incomparable quantities — cosine similarity
  in ``[0, 1]`` versus an unbounded Postgres ``ts_rank`` whose magnitude depends
  on document length and term-frequency normalisation — so any score-combining
  scheme would first need a mapping onto a shared scale, and that mapping is a
  fitted parameter with no principled value. Reciprocal Rank Fusion sidesteps it
  entirely by discarding magnitudes.

* :func:`select_relevant` decides **whether a leg has anything to contribute**,
  using each leg's own scores against its own floor. This never compares one
  leg's scores to another's, so it does not reintroduce the scale problem RRF
  exists to avoid.

The split matters because RRF alone cannot tell a leg that answered well from a
leg that answered badly: it gives whatever sits at rank 1 the full ``1/(k+1)``
weight either way. On a paraphrase query the lexical leg may match a stray
lexeme and return a document that is merely present rather than relevant, and
unweighted RRF will promote it to the top of the fused list on the strength of
being that leg's best of a bad set. Gating before fusing is what stops a leg
with no signal from displacing a leg that has some.

.. versionadded:: 0.18.0
    Initial implementation for OMN-16765.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

__all__ = [
    "MIN_LEXICAL_TS_RANK",
    "MIN_VECTOR_COSINE",
    "RRF_K_DEFAULT",
    "fuse_rrf",
    "fuse_rrf_scores",
    "select_relevant",
]

RRF_K_DEFAULT = 60
"""Smoothing constant from the original RRF formulation.

Larger values flatten the contribution of top ranks; smaller values sharpen it.
60 is the published default and the value named in the architecture plan. It is
recorded here as a default rather than a tuned result: no evidence in this
repository justifies moving it, and changing it without evidence would be worse
than taking the documented value.
"""

MIN_VECTOR_COSINE = 0.5
"""Cosine similarity below which the semantic leg is treated as not matching.

Cosine is bounded in ``[0, 1]`` and 0.5 is the midpoint. The existing layered
search in ``handler_agent_learning_retrieval`` already treats 0.70 as a broad
context match and 0.85 as a high-precision one, so 0.5 sits deliberately below
both: this floor is meant to exclude noise, not to make a relevance judgement
that belongs to the ranking.
"""

MIN_LEXICAL_TS_RANK = 0.15
"""Postgres ``ts_rank`` below which the lexical leg is treated as not matching.

``ts_rank`` is unbounded, but its low end is interpretable: a value this small
means almost no query lexeme was found in the document. It is the difference
between "this document is about the query" and "this document happens to
contain one of these words".
"""


def select_relevant(
    entries: Iterable[tuple[str, float]],
    min_score: float,
) -> list[str]:
    """Drop a leg's non-matching results, preserving rank order.

    Args:
        entries: ``(document_id, score)`` pairs from a single leg, best first.
        min_score: This leg's relevance floor. Compared only against scores from
            the same leg — never across legs.

    Returns:
        The surviving document ids, still in the leg's original rank order.
    """
    return [doc_id for doc_id, score in entries if score >= min_score]


def fuse_rrf_scores(
    *legs: Sequence[str],
    k: int = RRF_K_DEFAULT,
) -> dict[str, float]:
    """Accumulate Reciprocal Rank Fusion scores per document.

    Each document accumulates ``1 / (k + rank)`` from every leg that returned
    it, with ``rank`` counted from 1. A document returned by both legs therefore
    accumulates both terms, and that accumulation is the entire mechanism by
    which agreement between legs is rewarded.

    Args:
        *legs: One ranked list of document ids per leg, best first.
        k: Smoothing constant. See :data:`RRF_K_DEFAULT`.

    Returns:
        Fused score per document id. Values are small by construction (with
        ``k = 60`` a rank-1 hit contributes ~0.0164) and are meaningful only
        relative to each other within one query — never across queries, and
        never as an absolute relevance.

    Raises:
        ValueError: If ``k`` is negative, which would make the reciprocal
            undefined or negative for low ranks.
    """
    if k < 0:
        raise ValueError(f"RRF k must be non-negative, got {k}")

    scores: dict[str, float] = {}
    for leg in legs:
        for rank, doc_id in enumerate(leg, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def fuse_rrf(
    *legs: Sequence[str],
    k: int = RRF_K_DEFAULT,
) -> list[str]:
    """Fuse ranked document id lists by Reciprocal Rank Fusion.

    Ties are broken by document id, ascending. RRF produces exact ties whenever
    two documents occupy the same rank in their respective legs, which on any
    real input happens constantly, so the tie-break has to be defined rather
    than left to insertion order.

    Args:
        *legs: One ranked list of document ids per leg, best first.
        k: Smoothing constant. See :data:`RRF_K_DEFAULT`.

    Returns:
        Every document id from every leg, deduplicated, in fused order.

    Raises:
        ValueError: If ``k`` is negative.
    """
    scores = fuse_rrf_scores(*legs, k=k)
    return sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))
