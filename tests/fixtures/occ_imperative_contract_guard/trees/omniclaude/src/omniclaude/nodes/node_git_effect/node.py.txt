# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Node Git Effect - 100% contract-driven.

The NodeGitEffect class, a minimal shell
that inherits from NodeEffect. All effect logic is driven by the contract.yaml.

Capability: git.operations

The node exposes git operations:
- admission_check: Check host-local shared-tree, dirty-restore and lane-fetch policy
- branch_create: Create a new git branch
- commit: Stage and commit changes
- push: Push branch to remote
- pr_create: Create a pull request (includes mandatory ticket stamp block)
- pr_update: Update an existing pull request
- pr_close: Close a pull request
- pr_merge: Merge a pull request (direct or via merge queue)
- pr_list: List pull requests with structured JSON output
- pr_view: View a single pull request with structured JSON output
- tag_create: Create and push a git tag
- label_add: Add labels to a pull request

Handler resolution is performed via ServiceRegistry by protocol type
(ProtocolGitOperations). The actual git backend implements this protocol.

INVARIANT: No subprocess 'git' or 'gh' calls outside this effect node.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes.node_effect import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeGitEffect(NodeEffect):
    """Effect node for git operations.

    Capability: git.operations

    All behavior defined in contract.yaml.
    Handler resolved via ServiceRegistry by protocol type.

    INVARIANT: This node is the only place subprocess git/gh calls are permitted.
    All PRs created via this node include a mandatory ticket stamp block.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the git effect node.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)


__all__ = ["NodeGitEffect"]
