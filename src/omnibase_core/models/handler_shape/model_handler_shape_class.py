# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One class of a module, as facts for the handler-shape check (OMN-21536)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.handler_shape.model_handler_shape_method import (
    ModelHandlerShapeMethod,
)

__all__ = ["ModelHandlerShapeClass"]


class ModelHandlerShapeClass(BaseModel):
    """A class name, its line and its methods."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str
    line: int
    methods: tuple[ModelHandlerShapeMethod, ...] = ()
