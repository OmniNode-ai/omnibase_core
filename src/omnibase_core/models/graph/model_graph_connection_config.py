"""Graph Connection Config Model.

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
        """Get URI with credentials masked for safe logging.

        Returns:
            URI string safe for logging (credentials masked if present in URI).
        """
        # The password is stored separately via SecretStr, not embedded in URI.
        # For URIs with embedded credentials (e.g., neo4j://user:pass@host),
        # parse and mask the credentials portion.
        if "://" in self.uri and "@" in self.uri:
            # URI format: scheme://[user:pass@]host:port
            scheme_end = self.uri.index("://") + 3
            scheme = self.uri[:scheme_end]
            rest = self.uri[scheme_end:]
            if "@" in rest:
                # Credentials present in URI
                at_pos = rest.index("@")
                host_part = rest[at_pos + 1 :]
                return f"{scheme}***:***@{host_part}"
        return self.uri


__all__ = ["ModelGraphConnectionConfig"]
