# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelStackShapeData -- the allowlist a caller hands the stack-shape checker (OMN-21891)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelStackShapeData:
    """The services a stack may hold, the compose files of each lane and the baseline.

    ``baseline`` holds ``(compose file, service, ticket)`` rows; ``lanes`` maps a lane name to
    its compose file set.
    """

    runtime_services: frozenset[str]
    max_replicas: int
    dependencies: frozenset[str]
    one_shots: frozenset[str]
    lanes: dict[str, tuple[str, ...]]
    baseline: tuple[tuple[str, str, str], ...]
