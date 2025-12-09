"""
Node Reference Model

Provides minimal node reference for RuntimeHost contracts.
MVP implementation with slug-only identification for referencing
nodes within contract definitions.

This model enables RuntimeHost contracts to reference managed nodes
without requiring full node metadata at contract definition time.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeRef(BaseModel):
    """
    Node reference for RuntimeHost contract.

    MVP implementation with slug only.
    References nodes in the contract by their slug identifier.

    The slug is used to uniquely identify nodes within a RuntimeHost
    contract without requiring the full node definition at reference time.

    Attributes:
        slug: Node slug identifier for referencing nodes in contracts

    Example:
        >>> ref = ModelNodeRef(slug="node-compute-transformer")
        >>> ref.slug
        'node-compute-transformer'
    """

    slug: str = Field(
        ...,
        description="Node slug identifier for referencing nodes in contracts",
        min_length=1,
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )
