"""
Configuration model for Memgraph knowledge graph storage.

ONEX-compliant configuration model following security best practices
for database connection parameters and credentials management.
"""

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelMemgraphKnowledgeConfig(BaseModel):
    """Configuration for Memgraph knowledge graph storage."""

    host: str = Field(
        default_factory=lambda: os.getenv("MEMGRAPH_HOST", "localhost"),
        description="Memgraph host (env: MEMGRAPH_HOST)",
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("MEMGRAPH_PORT", "7687")),
        description="Memgraph port (env: MEMGRAPH_PORT)",
    )
    username: Optional[str] = Field(
        default_factory=lambda: os.getenv("MEMGRAPH_USERNAME"),
        description="Database username (env: MEMGRAPH_USERNAME)",
    )
    password: Optional[SecretStr] = Field(
        default_factory=lambda: (
            SecretStr(os.getenv("MEMGRAPH_PASSWORD"))
            if os.getenv("MEMGRAPH_PASSWORD")
            else None
        ),
        description="Database password (env: MEMGRAPH_PASSWORD, securely stored)",
    )
    database: str = Field(
        default_factory=lambda: os.getenv("MEMGRAPH_DATABASE", "memgraph"),
        description="Database name (env: MEMGRAPH_DATABASE)",
    )
    pool_size: int = Field(
        default_factory=lambda: int(os.getenv("MEMGRAPH_POOL_SIZE", "10")),
        description="Connection pool size (env: MEMGRAPH_POOL_SIZE)",
    )
    timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("MEMGRAPH_TIMEOUT_SECONDS", "30")),
        description="Connection timeout (env: MEMGRAPH_TIMEOUT_SECONDS)",
    )

    model_config = ConfigDict(frozen=False, validate_assignment=True)

    def get_auth_tuple(self) -> Optional[tuple]:
        """Get auth tuple with password revealed only when needed."""
        if self.username and self.password:
            return (self.username, self.password.get_secret_value())
        return None
