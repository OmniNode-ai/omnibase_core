from pydantic import BaseModel, Field


class ModelTrustedNodesInfo(BaseModel):
    """Information about trusted nodes configuration."""

    total_trusted_nodes: int = Field(
        default=0,
        description="Total number of trusted nodes",
    )
    high_trust_nodes: int = Field(default=0, description="Number of high trust nodes")
    trusted_node_ids: list[str] = Field(
        default_factory=list,
        description="List of trusted node identifiers",
    )
    high_trust_node_ids: list[str] = Field(
        default_factory=list,
        description="List of high trust node identifiers",
    )
