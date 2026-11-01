# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kinds of contract-chain coverage obligations."""

from enum import StrEnum


class EnumContractChainObligationKind(StrEnum):
    """Structural entities that require a committed chain binding."""

    TRANSITION = "transition"
    GRAPH_EDGE = "graph_edge"
    GUARD_BRANCH = "guard_branch"
    LOOP_EXIT = "loop_exit"
