"""Response models for Consul Adapter operations."""

from pydantic import BaseModel, Field


class ModelConsulHealthStatus(BaseModel):
    """Strongly typed model for consul adapter health status."""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    consul_connected: bool = Field(..., description="Consul connection status")
    event_bus_connected: bool = Field(..., description="Event bus connection status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")


class ModelConsulKvResponse(BaseModel):
    """Strongly typed model for Consul KV operation responses."""

    key: str = Field(..., description="Consul key")
    value: str | None = Field(None, description="Consul value")
    flags: int | None = Field(None, description="Consul flags")
    session: str | None = Field(None, description="Session ID")
    create_index: int | None = Field(None, description="Create index")
    modify_index: int | None = Field(None, description="Modify index")
    lock_index: int | None = Field(None, description="Lock index")


class ModelConsulServiceResponse(BaseModel):
    """Strongly typed model for Consul service operation responses."""

    service_id: str = Field(..., description="Service ID")
    service_name: str = Field(..., description="Service name")
    address: str = Field(..., description="Service address")
    port: int = Field(..., description="Service port")
    tags: list[str] | None = Field(None, description="Service tags")
    registered: bool = Field(..., description="Registration status")


class ModelConsulOperationResponse(BaseModel):
    """Strongly typed model for consul operation responses."""

    operation: str = Field(..., description="Operation performed")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    kv_response: ModelConsulKvResponse | None = Field(
        None,
        description="KV operation response",
    )
    service_response: ModelConsulServiceResponse | None = Field(
        None,
        description="Service operation response",
    )
    error_code: str | None = Field(
        None,
        description="Error code if operation failed",
    )
