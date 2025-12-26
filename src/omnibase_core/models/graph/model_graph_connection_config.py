"""
Graph Connection Config Model

Type-safe model for graph database connection configuration.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelGraphConnectionConfig(BaseModel):
    """
    Represents connection configuration for a graph database.

    Contains URI, authentication credentials, database selection,
    and connection pool settings.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.

    Security:
        Authentication credentials are stored using SecretStr to
        prevent accidental exposure in logs or error messages.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    uri: str = Field(
        default=...,
        description="Connection URI (e.g., 'bolt://localhost:7687', 'neo4j://host:7687')",
    )
    username: str | None = Field(
        default=None,
        description="Username for authentication",
    )
    password: SecretStr | None = Field(
        default=None,
        description="Password for authentication (secured)",
    )
    database: str | None = Field(
        default=None,
        description="Target database name (default database if not specified)",
    )
    pool_size: int = Field(
        default=50,
        description="Maximum number of connections in the pool",
        ge=1,
        le=1000,
    )

    def get_masked_uri(self) -> str:
        """Get URI with password masked for logging purposes.

        Returns:
            URI string with password replaced by asterisks.
        """
        if self.password is not None:
            # Simple masking - full implementation would parse URI
            return self.uri.replace(self.password.get_secret_value(), "***")
        return self.uri
