# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""MCP (Model Context Protocol) models for ONEX integration.

Models for exposing ONEX nodes as MCP tools,
enabling AI agents to discover and invoke platform capabilities.

Models:
    ModelMCPParameterMapping: Maps ONEX fields to MCP parameters.
    ModelMCPToolConfig: Contract `mcp:` block configuration.
    ModelMCPInvocationRequest: Tool call request envelope.
    ModelMCPInvocationResponse: Tool call response wrapper.
    ModelMCPToolDescriptor: Complete tool definition for registration.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.mcp.model_mcp_invocation_request import (
        ModelMCPInvocationRequest,
    )
    from omnibase_core.models.mcp.model_mcp_invocation_response import (
        ModelMCPInvocationResponse,
    )
    from omnibase_core.models.mcp.model_mcp_parameter_mapping import (
        ModelMCPParameterMapping,
    )
    from omnibase_core.models.mcp.model_mcp_tool_config import ModelMCPToolConfig
    from omnibase_core.models.mcp.model_mcp_tool_descriptor import (
        ModelMCPToolDescriptor,
    )

__all__ = [
    "ModelMCPInvocationRequest",
    "ModelMCPInvocationResponse",
    "ModelMCPParameterMapping",
    "ModelMCPToolConfig",
    "ModelMCPToolDescriptor",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelMCPInvocationRequest": (
        "omnibase_core.models.mcp.model_mcp_invocation_request",
        "ModelMCPInvocationRequest",
    ),
    "ModelMCPInvocationResponse": (
        "omnibase_core.models.mcp.model_mcp_invocation_response",
        "ModelMCPInvocationResponse",
    ),
    "ModelMCPParameterMapping": (
        "omnibase_core.models.mcp.model_mcp_parameter_mapping",
        "ModelMCPParameterMapping",
    ),
    "ModelMCPToolConfig": (
        "omnibase_core.models.mcp.model_mcp_tool_config",
        "ModelMCPToolConfig",
    ),
    "ModelMCPToolDescriptor": (
        "omnibase_core.models.mcp.model_mcp_tool_descriptor",
        "ModelMCPToolDescriptor",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
