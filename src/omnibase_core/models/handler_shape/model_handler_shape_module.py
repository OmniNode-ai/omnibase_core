# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One parsed module, the input of the handler-shape check (OMN-21536)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.handler_shape.model_handler_shape_class import (
    ModelHandlerShapeClass,
)
from omnibase_core.models.handler_shape.model_handler_shape_function import (
    ModelHandlerShapeFunction,
)

__all__ = ["ModelHandlerShapeModule"]


class ModelHandlerShapeModule(BaseModel):
    """The classes, module-level functions and referenced names of one module."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    classes: tuple[ModelHandlerShapeClass, ...] = ()
    functions: tuple[ModelHandlerShapeFunction, ...] = ()
    referenced_names: frozenset[str] = frozenset()
