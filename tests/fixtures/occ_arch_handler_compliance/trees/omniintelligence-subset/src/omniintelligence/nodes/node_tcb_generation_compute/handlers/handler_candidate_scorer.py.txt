# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Candidate scoring for TCB entrypoints and related items."""

from __future__ import annotations

import math


def score_candidate(
    candidate_path: str,
    intent_modules: list[str],
    intent_repos: list[str],
    days_since_last_commit: int,
    commit_frequency_30d: int = 0,
) -> float:
    """Score a candidate file path for inclusion in a TCB.

    Scoring formula (weighted sum, normalized to [0, 1]):
        path_proximity:  0.40 -- does path contain an intent module keyword?
        repo_proximity:  0.20 -- is the repo in intent_repos?
        recency:         0.25 -- 1.0 for today, 0.0 for 90+ days ago
        volatility:      0.15 -- higher commit frequency = higher risk (worth noting)

    Args:
        candidate_path: Repo-relative file path (e.g., "src/omnibase_core/models/routing/foo.py")
        intent_modules: Module keywords from normalized intent
        intent_repos: Repo names from normalized intent
        days_since_last_commit: Age of the most recent commit touching this file
        commit_frequency_30d: Number of commits to this file in last 30 days

    Returns:
        float in [0.0, 1.0]
    """
    path_lower = candidate_path.lower()

    # Path proximity (0.40 weight)
    path_score = 0.0
    for module in intent_modules:
        if module.lower() in path_lower:
            path_score = 1.0
            break
    # Partial match: any path segment matches
    if path_score == 0.0:
        path_parts = set(path_lower.replace("/", " ").replace("_", " ").split())
        for module in intent_modules:
            if module.lower() in path_parts:
                path_score = 0.5
                break

    # Repo proximity (0.20 weight)
    repo_score = 0.0
    for repo in intent_repos:
        if repo.lower() in path_lower:
            repo_score = 1.0
            break

    # Recency (0.25 weight): decay from 1.0 at 0 days to 0.0 at 90 days
    recency_score = max(0.0, 1.0 - (days_since_last_commit / 90.0))

    # Volatility (0.15 weight): log scale, 10+ commits/month = 1.0
    volatility_score = min(1.0, math.log1p(commit_frequency_30d) / math.log1p(10))

    return (
        0.40 * path_score
        + 0.20 * repo_score
        + 0.25 * recency_score
        + 0.15 * volatility_score
    )
