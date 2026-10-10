# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Handler for agent learning retrieval.

Performs layered similarity search against two Qdrant collections:
1. agent_learnings_error — high-precision error signature matching (cosine > 0.85)
2. agent_learnings_context — broad task context matching (cosine > 0.70)

Results are ranked by combined_score = similarity * freshness_score and merged.
"""

from __future__ import annotations

import math
from datetime import datetime


def compute_freshness_score(created_at: datetime, now: datetime) -> float:
    """Exponential decay: 0.900 at 1 week, 0.657 at 4 weeks, 0.600 at ~34 days.

    The four-week figure previously read "~60%" here (OMN-16765). It is 0.657 —
    ``exp(-0.015 * 28)``. 0.600 is a 34-day value, not a 28-day one. The
    constant is unchanged; only its description was wrong.

    Exact values are pinned in ``TestComputeFreshnessScore`` so this docstring
    cannot drift from the maths again.
    """
    delta = now - created_at
    days_old = max(0.0, delta.total_seconds() / 86400)
    return math.exp(-0.015 * days_old)


def build_error_query_text(error_text: str) -> str:
    """Build the text to embed for error signature matching."""
    return f"Error: {error_text[:2000]}"


def build_context_query_text(
    repo: str,
    file_paths: tuple[str, ...],
    task_type: str | None,
) -> str:
    """Build the text to embed for task context matching."""
    parts = [f"Repository: {repo}"]
    if file_paths:
        parts.append(f"Files: {', '.join(file_paths[:20])}")
    if task_type:
        parts.append(f"Task type: {task_type}")
    return "\n".join(parts)


def rank_and_merge(
    matches: list[dict[str, object]],
    max_results: int,
) -> list[dict[str, object]]:
    """Rank matches by combined_score descending and limit to max_results."""
    sorted_matches = sorted(
        matches,
        key=lambda m: float(m.get("combined_score", 0)),  # type: ignore[arg-type]  # Why: dict[str, object].get returns object; float() accepts int/float/str at runtime
        reverse=True,
    )
    return sorted_matches[:max_results]
