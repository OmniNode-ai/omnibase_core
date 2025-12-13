"""
Output Mapping Container Model.

Container for strongly-typed output references between graph nodes.
Follows ONEX canonical patterns with strict typing - no Any types allowed.

This module provides the ``ModelOutputMapping`` class for managing
collections of typed output references in the ONEX execution graph.
It replaces untyped ``dict[str, str]`` patterns with strongly-typed containers.

Example:
    >>> from omnibase_core.models.common.model_output_mapping import (
    ...     ModelOutputMapping,
    ... )
    >>> mapping = ModelOutputMapping.from_dict({
    ...     "input_data": "preprocessing_node.cleaned_data",
    ...     "config": "config_node.settings",
    ... })
    >>> mapping.get_source_reference("input_data")
    'preprocessing_node.cleaned_data'

See Also:
    - :class:`ModelOutputReference`: Individual output reference model.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_output_reference import ModelOutputReference


class ModelOutputMapping(BaseModel):
    """
    Container for output references with strong typing.

    Provides type-safe management of data flow between graph nodes,
    replacing dict[str, str] patterns with properly typed references.

    This model supports:
    - Structured output references with validation
    - Source node and output name extraction
    - Conversion to/from dictionary format for interoperability

    Example:
        >>> mapping = ModelOutputMapping.from_dict({
        ...     "input_data": "preprocessing_node.cleaned_data",
        ...     "config": "config_node.settings",
        ... })
        >>> mapping.get_source_reference("input_data")
        'preprocessing_node.cleaned_data'
        >>> mapping.get_reference("input_data").source_node_id
        'preprocessing_node'
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    references: list[ModelOutputReference] = Field(
        default_factory=list,
        description="List of typed output references",
    )

    def get_mapping_dict(self) -> dict[str, str]:
        """
        Convert to dictionary format (local_name -> source_reference).

        Returns:
            dict[str, str]: Dictionary mapping local names to source references
        """
        return {ref.local_name: ref.source_reference for ref in self.references}

    def get_source_reference(self, local_name: str) -> str | None:
        """
        Get the source reference for a local name.

        Args:
            local_name: Local name to look up

        Returns:
            The source reference string if found, None otherwise
        """
        for ref in self.references:
            if ref.local_name == local_name:
                return ref.source_reference
        return None

    def get_reference(self, local_name: str) -> ModelOutputReference | None:
        """
        Get the full reference object for a local name.

        Args:
            local_name: Local name to look up

        Returns:
            The ModelOutputReference if found, None otherwise
        """
        for ref in self.references:
            if ref.local_name == local_name:
                return ref
        return None

    def has_reference(self, local_name: str) -> bool:
        """
        Check if a reference exists for the given local name.

        Args:
            local_name: Local name to check

        Returns:
            True if reference exists, False otherwise
        """
        return any(ref.local_name == local_name for ref in self.references)

    def get_source_nodes(self) -> set[str]:
        """
        Get all unique source node IDs referenced in this mapping.

        Returns:
            Set of source node IDs
        """
        return {ref.source_node_id for ref in self.references}

    @classmethod
    def from_dict(
        cls,
        mapping_dict: dict[str, str],
    ) -> "ModelOutputMapping":
        """
        Create from dictionary format (local_name -> source_reference).

        Args:
            mapping_dict: Dictionary mapping local names to source references

        Returns:
            ModelOutputMapping instance with typed references
        """
        references: list[ModelOutputReference] = []
        for local_name, source_reference in mapping_dict.items():
            references.append(
                ModelOutputReference(
                    source_reference=source_reference,
                    local_name=local_name,
                ),
            )

        return cls(references=references)


__all__ = ["ModelOutputMapping"]
