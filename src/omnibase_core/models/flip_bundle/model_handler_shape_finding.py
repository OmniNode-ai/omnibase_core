# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolved contract binding and its handler-shape verdict."""

from pydantic import BaseModel, ConfigDict


class ModelHandlerShapeFinding(BaseModel):
    """A single node's handler-shape classification result."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    node_id: str
    category: str
    is_canonical: bool
    handler_module: str | None = None
    detail: str | None = None
