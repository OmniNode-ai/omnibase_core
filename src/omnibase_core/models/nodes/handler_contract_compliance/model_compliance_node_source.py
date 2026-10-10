# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The texts of one node directory supplied to the handler-contract compliance check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

__all__ = ["ModelComplianceNodeSource"]


class ModelComplianceNodeSource(BaseModel):
    """One ``node_*`` directory with a ``handlers/`` directory, read by the caller.

    Content arrives inline so the COMPUTE handler never touches the filesystem.
    ``node_dir`` and each handler ``path`` are the paths exactly as the caller
    walked them (``<repo-root>/src/<package>/nodes/node_x``): the handler derives
    the reported path and the module path from their segments.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_dir: str
    contract_yaml: str | None = Field(
        default=None,
        description="Text of the node's contract.yaml, or None when the file is absent.",
    )
    node_py: str | None = Field(
        default=None,
        description="Text of the node's node.py, or None when the file is absent.",
    )
    handlers: list[ModelSourceFile] = Field(
        default_factory=list,
        description="Handler modules in the order they are audited.",
    )
