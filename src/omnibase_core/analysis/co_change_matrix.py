# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
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
