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

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
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
    - O(1) lookup by local_name via internal cache

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

    # Private cache for O(1) lookup by local_name
    _by_local_name: dict[str, ModelOutputReference] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _build_lookup_cache(self) -> Self:
        """Build the lookup cache after model initialization.

        Raises:
            ModelOnexError: If duplicate local_name values are found in references.
        """
        seen: set[str] = set()
        for ref in self.references:
            if ref.local_name in seen:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Duplicate local_name in references: {ref.local_name}",
                    duplicate_local_name=ref.local_name,
                )
            seen.add(ref.local_name)
        self._by_local_name = {ref.local_name: ref for ref in self.references}
        return self

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

        O(1) lookup using internal cache.

        Args:
            local_name: Local name to look up

        Returns:
            The source reference string if found, None otherwise
        """
        ref = self._by_local_name.get(local_name)
        return ref.source_reference if ref is not None else None

    def get_reference(self, local_name: str) -> ModelOutputReference | None:
        """
        Get the full reference object for a local name.

        O(1) lookup using internal cache.

        Args:
            local_name: Local name to look up

        Returns:
            The ModelOutputReference if found, None otherwise
        """
        return self._by_local_name.get(local_name)

    def has_reference(self, local_name: str) -> bool:
        """
        Check if a reference exists for the given local name.

        O(1) lookup using internal cache.

        Args:
            local_name: Local name to check

        Returns:
            True if reference exists, False otherwise
        """
        return local_name in self._by_local_name

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
    ) -> Self:
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
