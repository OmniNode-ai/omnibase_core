# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node-role vocabulary for the Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

The IR is a *platform-neutral* intermediate distinct from the runtime
``EnumNodeType`` (which names runtime archetypes/categories). A role classifies
what kind of contract surface a node in the IR represents. ``RENDERER`` is
mandatory per the plan: a renderer is a first-class IR node role so UI component
contracts and the renderers that draw them share one graph.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper

__all__ = ("EnumContractGraphNodeRole",)


@unique
class EnumContractGraphNodeRole(UtilStrValueHelper, str, Enum):
    """Role a node plays in the Contract Graph IR.

    Distinct from runtime ``EnumNodeType``: these roles classify imported
    contract surfaces (backend node contracts and UI component contracts) within
    one canonical intermediate, not runtime dispatch archetypes.

    Attributes:
        EFFECT: A backend EFFECT node contract (side-effecting boundary).
        COMPUTE: A backend COMPUTE node contract (pure, returns a result).
        REDUCER: A backend REDUCER node contract (pure state delta).
        ORCHESTRATOR: A backend ORCHESTRATOR node contract (emits, never returns).
        COMPONENT: A UI component contract (what a component shows/binds/emits).
        RENDERER: A renderer that draws component contracts (mandatory IR role).
        PROTOCOL: A protocol/interface reference typing a node's boundary.
    """

    EFFECT = "effect"
    COMPUTE = "compute"
    REDUCER = "reducer"
    ORCHESTRATOR = "orchestrator"
    COMPONENT = "component"
    RENDERER = "renderer"
    PROTOCOL = "protocol"
