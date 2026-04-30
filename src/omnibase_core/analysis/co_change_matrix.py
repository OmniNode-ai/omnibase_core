# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import math
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class CoChangeMatrix:
    pair_count: dict[tuple[str, str], int]
    file_count: dict[str, int]
    total_commits: int


def build_cochange_matrix(commits: list[list[str]]) -> CoChangeMatrix:
    pair_count: Counter[tuple[str, str]] = Counter()
    file_count: Counter[str] = Counter()
    for files in commits:
        unique = sorted(set(files))
        for f in unique:
            file_count[f] += 1
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair_count[(unique[i], unique[j])] += 1
    return CoChangeMatrix(dict(pair_count), dict(file_count), len(commits))


def compute_npmi(p_a: float, p_b: float, p_ab: float) -> float:
    if p_ab <= 0:
        return -1.0
    pmi = math.log(p_ab) - math.log(p_a * p_b)
    npmi = pmi / -math.log(p_ab)
    return max(-1.0, min(1.0, npmi))


def compute_lift(p_a: float, p_b: float, p_ab: float) -> float:
    if p_a == 0 or p_b == 0:
        return 0.0
    return p_ab / (p_a * p_b)
