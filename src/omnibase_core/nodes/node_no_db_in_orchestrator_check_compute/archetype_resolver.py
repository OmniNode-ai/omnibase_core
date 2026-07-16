# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Archetype resolution for the no_db_in_orchestrator_check COMPUTE node.

This is the *seam* the whole rule keys on: a node's design-time archetype is
declared in its ``contract.yaml`` (top-level ``node_type`` and
``descriptor.node_archetype``, both :class:`EnumNodeArchetype` values). The
rule is archetype-specific — unlike the universal OMN-14659 lints that scan
every file blindly, this check only cares about ``.py`` modules that sit in an
ORCHESTRATOR node package.

Split out of ``handler.py`` (single-class-per-file convention, OMN-14656) so
the COMPUTE handler module contains exactly one class.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Final

import yaml

from omnibase_core.enums.enum_node_archetype import EnumNodeArchetype

__all__ = [
    "CONTRACT_FILENAME",
    "contract_declares_orchestrator",
    "node_dir_of",
]

CONTRACT_FILENAME: Final[str] = "contract.yaml"

# The archetype value that arms this rule. Sourced from the canonical enum so a
# rename of the archetype vocabulary breaks loudly here rather than silently
# disarming the gate.
_ORCHESTRATOR_VALUE: Final[str] = EnumNodeArchetype.ORCHESTRATOR.value


def node_dir_of(path: str) -> str:
    """Return the POSIX parent directory of ``path`` — its node-package dir.

    Windows-style separators are normalised so the grouping key is stable
    across platforms (the finding ``location`` still reflects the input path).
    """
    return PurePosixPath(path.replace("\\", "/")).parent.as_posix()


def contract_declares_orchestrator(source: str) -> bool:
    """Return True when a ``contract.yaml`` declares the ORCHESTRATOR archetype.

    Reads BOTH seam fields — top-level ``node_type`` and
    ``descriptor.node_archetype`` — and returns True if *either* equals
    ``orchestrator`` (case-insensitive). Checking both mirrors how the
    contracts in this repo carry the archetype redundantly, so a contract that
    only sets one of the two is still classified correctly.

    Raises:
        yaml.YAMLError: when ``source`` is not parseable YAML. The caller
            surfaces this as an ERROR finding rather than silently treating an
            unparseable contract as non-orchestrator (fail loud, not
            green-on-absence).
    """
    data = yaml.safe_load(source)
    if not isinstance(data, dict):
        return False

    candidates: list[object] = [data.get("node_type")]
    descriptor = data.get("descriptor")
    if isinstance(descriptor, dict):
        candidates.append(descriptor.get("node_archetype"))

    return any(
        isinstance(value, str) and value.strip().lower() == _ORCHESTRATOR_VALUE
        for value in candidates
    )
