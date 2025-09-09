"""
MaskedConnectionProperties model.
"""

from typing import Any

from pydantic import BaseModel, Field

class ModelMaskedConnectionProperties(BaseModel):
    """
    Masked connection properties with typed fields.
    Replaces Dict[str, Any] for get_masked_connection_properties() returns.
    """

    connection_string: str | None = Field(
        None,
        description="Masked connection string",
    )
    driver: str | None = Field(None, description="Driver name")
    protocol: str | None = Field(None, description="Connection protocol")
    host: str | None = Field(None, description="Server host")
    port: int | None = Field(None, description="Server port")
    database: str | None = Field(None, description="Database name")
    username: str | None = Field(None, description="Username (may be masked)")
    password: str = Field("***MASKED***", description="Always masked")
    auth_mechanism: str | None = Field(None, description="Authentication mechanism")
    pool_size: int | None = Field(None, description="Connection pool size")
    use_ssl: bool | None = Field(None, description="Use SSL/TLS")
    masked_fields: list[str] = Field(
        default_factory=list,
        description="List of masked field names",
    )
    masking_algorithm: str = Field("sha256", description="Masking algorithm used")
