"""
Node Connection Settings Model.

Network and connection configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_protocol_type import EnumProtocolType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_node_connection_summary_type import (
    TypedDictNodeConnectionSummaryType,
)


class ModelNodeConnectionSettings(BaseModel):
    """
    Node connection configuration settings.

    Contains network connection parameters:
    - Service endpoints and ports
    - Protocol configuration
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Connection details (2 fields + 1 enum)
    endpoint: str | None = Field(default=None, description="Service endpoint")
    port: int | None = Field(
        default=None,
        description="Service port",
        ge=1,
        le=65535,
    )
    protocol: EnumProtocolType | None = Field(
        default=None,
        description="Communication protocol",
    )

    def has_endpoint(self) -> bool:
        """Check if endpoint is configured."""
        return self.endpoint is not None

    def has_port(self) -> bool:
        """Check if port is configured."""
        return self.port is not None

    def has_protocol(self) -> bool:
        """Check if protocol is configured."""
        return self.protocol is not None

    def is_fully_configured(self) -> bool:
        """Check if connection is fully configured."""
        return self.has_endpoint() and self.has_port() and self.has_protocol()

    def is_secure_protocol(self) -> bool:
        """Check if using secure protocol."""
        if self.protocol is None:
            return False
        return self.protocol in [
            EnumProtocolType.HTTPS,
            EnumProtocolType.GRPC,
        ]

    def get_connection_url(self) -> str | None:
        """Get full connection URL if possible."""
        if not self.is_fully_configured():
            return None

        # Safe access to protocol value (already checked in is_fully_configured)
        if self.protocol is None:
            return None
        protocol_prefix = self.protocol.value.lower()
        return f"{protocol_prefix}://{self.endpoint}:{self.port}"

    def get_connection_summary(self) -> TypedDictNodeConnectionSummaryType:
        """Get connection settings summary."""
        return {
            "endpoint": self.endpoint,
            "port": self.port,
            # protocol is optional, use explicit None check
            "protocol": self.protocol.value if self.protocol is not None else None,
            "has_endpoint": self.has_endpoint(),
            "has_port": self.has_port(),
            "has_protocol": self.has_protocol(),
            "is_fully_configured": self.is_fully_configured(),
            "is_secure": self.is_secure_protocol(),
            "connection_url": self.get_connection_url(),
        }

    @classmethod
    def create_http(
        cls,
        endpoint: str,
        port: int = 80,
        secure: bool = False,
    ) -> ModelNodeConnectionSettings:
        """Create HTTP connection settings."""
        protocol = EnumProtocolType.HTTPS if secure else EnumProtocolType.HTTP
        return cls(
            endpoint=endpoint,
            port=port,
            protocol=protocol,
        )

    @classmethod
    def create_grpc(
        cls,
        endpoint: str,
        port: int = 50051,
    ) -> ModelNodeConnectionSettings:
        """Create gRPC connection settings."""
        return cls(
            endpoint=endpoint,
            port=port,
            protocol=EnumProtocolType.GRPC,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """
        Get metadata as dictionary for ProtocolMetadataProvider protocol.

        Returns a TypedDictMetadataDict containing complete connection settings
        information. This model represents network configuration, so it does not
        map to top-level name/version/description keys. All connection details
        are provided in the nested metadata dict via get_connection_summary().

        Returns:
            TypedDictMetadataDict with the following structure:
            - "metadata": Dict containing (from get_connection_summary()):
                - "endpoint": Service endpoint string or None if not configured
                - "port": Port number (1-65535) or None if not configured
                - "protocol": EnumProtocolType value string
                  (e.g., "HTTP", "HTTPS", "GRPC") or None
                - "has_endpoint": Boolean indicating if endpoint is set
                - "has_port": Boolean indicating if port is set
                - "has_protocol": Boolean indicating if protocol is set
                - "is_fully_configured": Boolean, True only if endpoint,
                  port, and protocol are all set
                - "is_secure": Boolean indicating if using secure protocol
                  (HTTPS or GRPC)
                - "connection_url": Full URL string (e.g., "https://api:443")
                  or None if not fully configured

        Example:
            >>> settings = ModelNodeConnectionSettings.create_http(
            ...     endpoint="api.example.com",
            ...     port=443,
            ...     secure=True
            ... )
            >>> metadata = settings.get_metadata()
            >>> metadata["metadata"]["endpoint"]
            'api.example.com'
            >>> metadata["metadata"]["is_secure"]
            True
            >>> metadata["metadata"]["connection_url"]
            'https://api.example.com:443'
        """
        # Delegate to get_connection_summary() to avoid field mapping duplication.
        # Cast TypedDict to SerializableValue dict for TypedDictMetadataDict compatibility
        from typing import cast

        from omnibase_core.types.type_serializable_value import SerializableValue

        return {
            "metadata": cast(
                dict[str, SerializableValue], dict(self.get_connection_summary())
            )
        }

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelNodeConnectionSettings"]
