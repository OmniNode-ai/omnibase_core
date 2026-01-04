"""
Type aliases for schema-related types in ONEX.

This module provides centralized type aliases for schema values and dictionaries,
replacing scattered inline type annotations throughout the codebase.

These type aliases follow ONEX patterns by:
1. Reducing inline type duplication (anti-pattern: "primitive soup")
2. Providing semantic naming for common schema-related types
3. Centralizing type definitions for easier maintenance and refactoring
4. Using ModelSchemaValue for type-safe schema representation

Type Hierarchy:
    SchemaDict: A dictionary mapping string keys to ModelSchemaValue instances
    StepOutputs: A dictionary mapping step identifiers to their SchemaDict outputs

Design Decisions:
    - Uses ModelSchemaValue instead of Any for type safety
    - SchemaDict replaces dict[str, Any] in schema contexts
    - StepOutputs replaces dict[str, dict[str, Any]] in workflow contexts
    - Type aliases provide semantic meaning beyond raw dict types
    - Uses TYPE_CHECKING to avoid circular imports with models

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module uses TYPE_CHECKING and forward references to avoid circular imports.
The types module is imported by models which themselves may import ModelSchemaValue.

Import Chain to Avoid:
types.__init__ -> type_schema_aliases -> models.common -> ... -> types.__init__

Solution: Use TYPE_CHECKING guard and string forward references.

Usage:
    >>> from omnibase_core.types import SchemaDict, StepOutputs
    >>> from omnibase_core.models.common import ModelSchemaValue
    >>>
    >>> # Use SchemaDict for metadata, parameters, or variable storage
    >>> metadata: SchemaDict = {
    ...     "version": ModelSchemaValue.create_string("1.0.0"),
    ...     "count": ModelSchemaValue.create_number(42),
    ... }
    >>>
    >>> # Use StepOutputs for workflow step result tracking
    >>> outputs: StepOutputs = {
    ...     "step_1": {"result": ModelSchemaValue.create_string("success")},
    ...     "step_2": {"count": ModelSchemaValue.create_number(10)},
    ... }

Migration:
    Replace these patterns with the new type aliases:
    - dict[str, Any] (in schema contexts) -> SchemaDict
    - dict[str, dict[str, Any]] (in workflow contexts) -> StepOutputs
    - dict[str, ModelSchemaValue] -> SchemaDict
    - dict[str, dict[str, ModelSchemaValue]] -> StepOutputs

See Also:
    - omnibase_core.models.common.model_schema_value: The ModelSchemaValue class
    - omnibase_core.models.core.model_schema_dict: Structured schema representation
    - omnibase_core.types.type_json: JSON-compatible type aliases
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md: Node architecture patterns
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

__all__ = [
    "SchemaDict",
    "StepOutputs",
]

# ==============================================================================
# Schema Dictionary Type Alias
# ==============================================================================

# Type alias for schema dictionaries with type-safe values.
# Replaces dict[str, Any] in schema-related contexts with proper type safety.
#
# A SchemaDict maps string keys to ModelSchemaValue instances, which can
# represent any valid JSON Schema value type (string, number, boolean,
# null, array, or object) without resorting to Any.
#
# Use cases:
# - Metadata fields in models
# - Configuration parameters
# - Variable storage in workflows
# - Command/operation parameters
# - State changes in events
#
# Replaces inline types like:
#     dict[str, Any]
#     dict[str, object]
#     dict[str, ModelSchemaValue]
#
# Example:
#     >>> metadata: SchemaDict = {
#     ...     "name": ModelSchemaValue.create_string("my_node"),
#     ...     "version": ModelSchemaValue.create_string("1.0.0"),
#     ...     "enabled": ModelSchemaValue.create_boolean(True),
#     ... }
type SchemaDict = dict[str, "ModelSchemaValue"]


# ==============================================================================
# Step Outputs Type Alias
# ==============================================================================

# Type alias for workflow step outputs.
# Maps step identifiers to their output schema dictionaries.
#
# Used in orchestrator and workflow contexts where each step produces
# a dictionary of named outputs. The outer dict key is typically a step
# name or UUID string, and the inner SchemaDict contains the step's outputs.
#
# Use cases:
# - Orchestrator step_outputs fields
# - Workflow execution result tracking
# - Multi-step computation aggregation
# - Pipeline stage outputs
#
# Replaces inline types like:
#     dict[str, dict[str, Any]]
#     dict[str, dict[str, object]]
#     dict[str, dict[str, ModelSchemaValue]]
#
# Example:
#     >>> step_outputs: StepOutputs = {
#     ...     "extract": {
#     ...         "data": ModelSchemaValue.create_object({"key": "value"}),
#     ...         "count": ModelSchemaValue.create_number(100),
#     ...     },
#     ...     "transform": {
#     ...         "result": ModelSchemaValue.create_array(["a", "b", "c"]),
#     ...     },
#     ... }
type StepOutputs = dict[str, dict[str, "ModelSchemaValue"]]
