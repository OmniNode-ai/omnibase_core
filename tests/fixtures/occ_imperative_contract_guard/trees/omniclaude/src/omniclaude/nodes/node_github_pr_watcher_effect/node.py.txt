# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodeGithubPrWatcherEffect -- effect node for PR status event routing.

Subscribes to ``onex.evt.omniclaude.github-pr-status.v1``, looks up the Valkey watch
registry for interested agents, and routes matching events to per-agent
inbox topics.

Capability: github.pr_watcher

See OMN-2826 Phase 2b for specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes.node_effect import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeGithubPrWatcherEffect(NodeEffect):
    """Effect node for GitHub PR status event routing.

    Capability: github.pr_watcher

    Subscribes to ``onex.evt.omniclaude.github-pr-status.v1`` and routes matching
    events to per-agent inbox topics via Valkey watch registry lookups.

    All behavior defined in contract.yaml.
    Handler resolved via ServiceRegistry by protocol type.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the PR watcher effect node.

        Args:
            container: ONEX container for dependency injection.
        """
        super().__init__(container)


__all__ = ["NodeGithubPrWatcherEffect"]
