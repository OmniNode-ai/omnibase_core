# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Archetype resolution for the no_io_outside_effects_check COMPUTE node.

This is the *seam* the whole rule keys on. The canonical 4-archetype model
(:class:`EnumNodeArchetype`) makes **EFFECT the only I/O-permitted archetype**
("External I/O operations: API calls, database ops, file system access");
COMPUTE, REDUCER and ORCHESTRATOR are pure ("Reducers are pure",
"Orchestrators emit, never return" — omnibase_core CLAUDE.md Repo Invariants).

The archetype is declared in each node's ``contract.yaml`` (top-level
``node_type`` and ``descriptor.node_archetype``, both :class:`EnumNodeArchetype`
values). The rule is archetype-keyed: every ``.py`` module co-located with a
**non-EFFECT** contract must be pure, so this resolver classifies each contract
and the handler scans only the non-EFFECT node packages. EFFECT packages are
where I/O legitimately lives and are never scanned.

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
    "EFFECT_VALUE",
    "node_dir_of",
    "resolve_archetype",
]

CONTRACT_FILENAME: Final[str] = "contract.yaml"

# The single I/O-permitted archetype value. Sourced from the canonical enum so a
# rename of the archetype vocabulary breaks loudly here rather than silently
# disarming (or over-arming) the gate.
EFFECT_VALUE: Final[str] = EnumNodeArchetype.EFFECT.value

# Reverse lookup from the raw contract string to the canonical enum. Built from
# the enum itself so it stays in lock-step with the vocabulary.
_VALUE_TO_ARCHETYPE: Final[dict[str, EnumNodeArchetype]] = {
    member.value: member for member in EnumNodeArchetype
}


def node_dir_of(path: str) -> str:
    """Return the POSIX parent directory of ``path`` — its node-package dir.

    Windows-style separators are normalised so the grouping key is stable
    across platforms (the finding ``location`` still reflects the input path).
    """
    return PurePosixPath(path.replace("\\", "/")).parent.as_posix()


def resolve_archetype(source: str) -> EnumNodeArchetype | None:
    """Resolve the node archetype declared in a ``contract.yaml`` string.

    Reads BOTH seam fields — top-level ``node_type`` and
    ``descriptor.node_archetype`` — and returns the first that maps to a
    canonical :class:`EnumNodeArchetype`. Checking both mirrors how the
    contracts in this repo carry the archetype redundantly, so a contract that
    only sets one of the two is still classified correctly. Returns ``None``
    when neither field names a recognised archetype (the caller treats an
    unresolved archetype as *non-EFFECT* — fail-closed, I/O is scanned unless a
    contract positively proves the package is EFFECT).

    Raises:
        yaml.YAMLError: when ``source`` is not parseable YAML. The caller
            surfaces this as an ERROR finding rather than silently treating an
            unparseable contract as pure/non-scanned (fail loud, not
            green-on-absence).
    """
    data = yaml.safe_load(source)
    if not isinstance(data, dict):
        return None

    candidates: list[object] = [data.get("node_type")]
    descriptor = data.get("descriptor")
    if isinstance(descriptor, dict):
        candidates.append(descriptor.get("node_archetype"))

    for value in candidates:
        if isinstance(value, str):
            archetype = _VALUE_TO_ARCHETYPE.get(value.strip().lower())
            if archetype is not None:
                return archetype
    return None
