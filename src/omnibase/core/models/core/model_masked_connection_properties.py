"""
MaskedConnectionProperties model.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelMaskedConnectionProperties(BaseModel):
    """
    Masked connection properties with typed fields.
    Replaces Dict[str, Any] for get_masked_connection_properties() returns.
    """

    connection_string: Optional[str] = Field(
        None, description="Masked connection string"
    )
    driver: Optional[str] = Field(None, description="Driver name")
    protocol: Optional[str] = Field(None, description="Connection protocol")
    host: Optional[str] = Field(None, description="Server host")
    port: Optional[int] = Field(None, description="Server port")
    database: Optional[str] = Field(None, description="Database name")
    username: Optional[str] = Field(None, description="Username (may be masked)")
    password: str = Field("***MASKED***", description="Always masked")
    auth_mechanism: Optional[str] = Field(None, description="Authentication mechanism")
    pool_size: Optional[int] = Field(None, description="Connection pool size")
    use_ssl: Optional[bool] = Field(None, description="Use SSL/TLS")
    masked_fields: List[str] = Field(
        default_factory=list, description="List of masked field names"
    )
    masking_algorithm: str = Field("sha256", description="Masking algorithm used")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)
