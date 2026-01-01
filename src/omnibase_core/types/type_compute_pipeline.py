"""
Compute pipeline type definitions.

This module provides type definitions for compute pipeline operations,
including type aliases for pipeline data flows and transformations.

These types replace the use of `Any` with more specific type annotations
that better document the expected data shapes while maintaining the
necessary flexibility for polymorphic data handling.

Type Aliases:
    PipelineData: Type for data flowing through compute pipelines
    TransformInput: Type for transformation function inputs
    TransformOutput: Type for transformation function outputs

Design Principles:
    - Use `object` for truly polymorphic data (JSON-like values)
    - Use union types for known type variants
    - Use TypeVar for type-preserving operations (like identity)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from pydantic import BaseModel

__all__ = [
    "PipelineData",
    "PipelineDataDict",
    "TransformInputT",
    "PathResolvedValue",
    "StepResultMapping",
]


# Type alias for data flowing through compute pipelines.
# Pipeline data can be:
# - A dictionary with string keys and arbitrary values
# - A Pydantic BaseModel instance
#
# Note: The `| object` was intentionally removed as it would cause
# the union to collapse to just `object` (all types inherit from object),
# defeating type narrowing. If truly arbitrary objects are needed,
# use `object` directly or a protocol for duck typing.
PipelineData = dict[str, object] | BaseModel

# Type alias for dictionary-based pipeline data
# Used when the data is known to be a dict structure
PipelineDataDict = dict[str, object]

# TypeVar for type-preserving transformations
# Used for operations like identity where output type matches input type
TransformInputT = TypeVar("TransformInputT")

# Type for values resolved from path expressions
# Path resolution can return any JSON-compatible value or object attribute
PathResolvedValue = object

# Type alias for step results mapping
# Maps step names to their result objects
StepResultMapping = Mapping[str, object]
