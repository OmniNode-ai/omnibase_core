# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract walker enums (OMN-19553, golden-chain validation layer plan r4 Phase 3)."""

from __future__ import annotations

from enum import StrEnum


class EnumContractWalkRole(StrEnum):
    """Role a machine-declaring contract plays in a walked workflow."""

    ORCHESTRATOR = "orchestrator"
    REDUCER = "reducer"
    OTHER = "other"


class EnumContractWalkPathKind(StrEnum):
    """How a selected path through a workflow's product graph ends.

    GOLDEN ends in a terminal state that is not a declared error state. ERROR
    ends in a declared error state. OPEN ends where no terminal state is
    reachable: the machine is perpetual (declares no terminal state) or the
    path runs into a dead state.
    """

    GOLDEN = "golden"
    ERROR = "error"
    OPEN = "open"


class EnumContractWalkLinkEvidence(StrEnum):
    """Contract-declared evidence that links a reducer to an orchestrator."""

    TOPIC = "topic"
    MODULE_REFERENCE = "module_reference"
