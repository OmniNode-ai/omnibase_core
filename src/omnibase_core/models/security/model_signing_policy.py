"""
ModelSigningPolicy: Signing policy configuration for signature chains.

This model defines the policy requirements for cryptographic signatures
in the envelope routing chain with strongly typed configurations.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelSigningPolicy(BaseModel):
    """Signing policy configuration.

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(from_attributes=True)

    minimum_signatures: int = Field(
        default=1,
        description="Minimum signatures required",
    )
    minimum_trusted_signatures: int = Field(
        default=0,
        description="Minimum trusted signatures required",
    )
    required_operations: list[str] = Field(
        default_factory=list,
        description="Required operation types",
    )
    trusted_nodes: list[str] = Field(
        default_factory=list,
        description="List of trusted node IDs",
    )
    required_algorithms: list[str] = Field(
        default_factory=list,
        description="Required signature algorithms",
    )
    max_hop_count: int | None = Field(
        default=None, description="Maximum allowed hop count"
    )
    require_sequential_timestamps: bool = Field(
        default=True,
        description="Require sequential timestamps",
    )
