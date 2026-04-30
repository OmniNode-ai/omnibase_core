# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class CoChangeMatrix:
    """Immutable co-change statistics for a set of commits.

    pair_count: sorted (a, b) file pairs mapped to co-occurrence count.
      Keys are always ordered (a < b) to avoid duplicate pair representations.
    file_count: per-file commit count across all analysed commits.
    total_commits: total number of commits included in the analysis.

    All mapping fields use MappingProxyType to prevent item-level mutation,
    which frozen=True alone does not guard against.
    """

    pair_count: Mapping[tuple[str, str], int]
    file_count: Mapping[str, int]
    total_commits: int


def build_cochange_matrix(commits: list[list[str]]) -> CoChangeMatrix:
    """Build a co-change matrix from a list of per-commit file lists.

    Files within each commit are deduplicated before counting; pairs are stored
    as sorted (a, b) tuples with a < b. Returns a frozen CoChangeMatrix whose
    mapping fields are wrapped in MappingProxyType.
    """
    pair_count: Counter[tuple[str, str]] = Counter()
    file_count: Counter[str] = Counter()
    for files in commits:
        unique = sorted(set(files))
        for f in unique:
            file_count[f] += 1
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair_count[(unique[i], unique[j])] += 1
    return CoChangeMatrix(
        MappingProxyType(dict(pair_count)),
        MappingProxyType(dict(file_count)),
        len(commits),
    )


def compute_npmi(p_a: float, p_b: float, p_ab: float) -> float:
    """Normalised pointwise mutual information in [-1, 1].

    Returns -1.0 when p_ab <= 0 (no co-occurrence signal).
    Returns 0.0 for statistical independence (p_ab == p_a * p_b).
    Returns 1.0 for perfect correlation (p_ab == p_a == p_b).
    Formula: PMI / -log(p_ab), clamped to [-1, 1].
    """
    if p_ab <= 0:
        return -1.0
    pmi = math.log(p_ab) - math.log(p_a * p_b)
    npmi = pmi / -math.log(p_ab)
    return max(-1.0, min(1.0, npmi))


def compute_lift(p_a: float, p_b: float, p_ab: float) -> float:
    """Lift: observed co-occurrence divided by expected under independence.

    Returns 0.0 when p_a == 0 or p_b == 0 (degenerate case).
    Values > 1.0 indicate positive correlation; < 1.0 negative correlation.
    Formula: p_ab / (p_a * p_b).
    """
    if p_a == 0 or p_b == 0:
        return 0.0
    return p_ab / (p_a * p_b)
