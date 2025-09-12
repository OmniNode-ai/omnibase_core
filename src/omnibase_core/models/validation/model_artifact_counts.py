"""
ArtifactCounts model.
"""

from pydantic import BaseModel


class ModelArtifactCounts(BaseModel):
    """
    Canonical model for artifact counts in the ONEX tree generator.
    Replaces Dict[str, int] for artifact counting.
    """

    nodes: int = 0
    cli_tools: int = 0
    runtimes: int = 0
    adapters: int = 0
    contracts: int = 0
    packages: int = 0
