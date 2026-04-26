# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Change-aware test path resolution for omnibase_core CI."""

from __future__ import annotations

from pathlib import Path

from scripts.ci.test_selection_loader import (
    ModelAdjacencyMap,
    load_adjacency_map,
)

SRC_PREFIX = "src/omnibase_core/"
TEST_UNIT_PREFIX = "tests/unit/"
TEST_INTEGRATION_PREFIX = "tests/integration/"


def resolve_test_paths(
    changed_files: list[str],
    adjacency_path: Path,
) -> list[str]:
    """Map changed file paths to deterministic UNIT test directories.

    Behavior:
      - Source changes under src/omnibase_core/<module>: include
        tests/unit/<module>/.
      - Test-only changes under tests/unit/: include the changed unit-test directory.
      - Test-only changes under tests/integration/: ignored (integration runs always).
      - Files outside src/ and tests/unit/: no contribution; caller decides
        whether to escalate to full suite.

    Adjacency expansion is added in Task 5.
    """
    config = load_adjacency_map(adjacency_path)
    return _resolve(changed_files, config)


def _resolve(changed_files: list[str], config: ModelAdjacencyMap) -> list[str]:
    selected: set[str] = set()
    for path in changed_files:
        if path.startswith(SRC_PREFIX):
            module = path[len(SRC_PREFIX) :].split("/", 1)[0]
            if module in config.adjacency:
                selected.add(f"{TEST_UNIT_PREFIX}{module}/")
        elif path.startswith(TEST_UNIT_PREFIX):
            parts = path.split("/")
            if len(parts) >= 3:
                selected.add(f"{TEST_UNIT_PREFIX}{parts[2]}/")
    return sorted(selected)
