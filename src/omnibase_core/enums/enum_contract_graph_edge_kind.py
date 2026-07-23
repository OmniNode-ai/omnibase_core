# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Edge-kind vocabulary for the Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

An edge kind names the typed relationship between two IR nodes. The plan
requires the three UI-platform edge kinds (``component_renders`` /
``action_emits`` / ``data_binds``) in addition to the backend topology edges
(publish/subscribe/protocol-implements) so a single IR spans backend node
contracts and UI component contracts.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ("EnumContractGraphEdgeKind",)


@unique
class EnumContractGraphEdgeKind(UtilStrValueHelper, str, Enum):
    """Typed relationship between two Contract Graph IR nodes.

    Attributes:
        PUBLISHES: A node publishes onto a topic (source node -> topic node).
        SUBSCRIBES: A node subscribes to a topic (source node -> topic node).
        IMPLEMENTS_PROTOCOL: A node implements a protocol/interface reference.
        COMPONENT_RENDERS: A renderer renders a UI component contract.
        ACTION_EMITS: A component action emits a command onto a topic.
        DATA_BINDS: A component binds to a projection topic for its truth.
    """

    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"
    IMPLEMENTS_PROTOCOL = "implements_protocol"
    COMPONENT_RENDERS = "component_renders"
    ACTION_EMITS = "action_emits"
    DATA_BINDS = "data_binds"
