"""
Output Reference Model.

Strongly-typed model for referencing outputs from other graph nodes.
Follows ONEX canonical patterns with strict typing - no Any types allowed.

This module provides the ``ModelOutputReference`` class for defining
typed data flow references between nodes in the ONEX execution graph.
It replaces untyped ``dict[str, str]`` patterns with validated references.

The source_reference format is "node_id.output_name" which is validated
to ensure proper structure and prevent malformed references at runtime.

Example:
    >>> from omnibase_core.models.common.model_output_reference import (
    ...     ModelOutputReference,
    ... )
    >>> ref = ModelOutputReference(
    ...     source_reference="preprocessing_node.cleaned_data",
    ...     local_name="input_data",
    ... )
    >>> ref.source_node_id
    'preprocessing_node'
    >>> ref.source_output_name
    'cleaned_data'

Security:
    - ``source_reference`` has max_length=512 to prevent memory exhaustion
    - ``local_name`` has max_length=255 to align with identifier limits
    - Format validation prevents injection of malformed references

See Also:
    - :class:`ModelOutputMapping`: Container for multiple output references.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH


class ModelOutputReference(BaseModel):
    """
    Reference to an output from another graph node.

    Represents a mapping from a source node's output to a local input name
    in the current node. This enables typed data flow between graph nodes.

    The source_reference follows the format: "node_id.output_name"
    - node_id: The unique identifier of the source node
    - output_name: The name of the output field from that node

    Example:
        >>> ref = ModelOutputReference(
        ...     source_reference="preprocessing_node.cleaned_data",
        ...     local_name="input_data",
        ...     description="Cleaned data from preprocessing stage",
        ... )
        >>> ref.source_node_id
        'preprocessing_node'
        >>> ref.source_output_name
        'cleaned_data'
    """

    model_config = ConfigDict(
        extra="forbid", from_attributes=True, validate_assignment=True
    )

    source_reference: str = Field(
        default=...,
        description="Reference to source output in format 'node_id.output_name'",
        min_length=3,  # Minimum: "a.b"
        max_length=512,
    )
    local_name: str = Field(
        default=...,
        description="Local name to bind the output value to",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of this reference",
        max_length=1024,
    )
    transform: str | None = Field(
        default=None,
        description="Optional transformation to apply (e.g., 'json_parse', 'to_string')",
        max_length=256,
    )

    @field_validator("source_reference")
    @classmethod
    def validate_source_reference_format(cls, v: str) -> str:
        """Validate that source_reference contains exactly one dot separator."""
        if "." not in v:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                f"source_reference must be in format 'node_id.output_name', got: {v}"
            )
        parts = v.split(".", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                f"source_reference must have non-empty node_id and output_name, got: {v}"
            )
        return v

    @property
    def source_node_id(self) -> str:
        """Extract the source node ID from the reference."""
        return self.source_reference.split(".", 1)[0]

    @property
    def source_output_name(self) -> str:
        """Extract the output name from the reference."""
        return self.source_reference.split(".", 1)[1]


__all__ = ["ModelOutputReference"]
