"""Input model for Consul Adapter operations."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModelConsulKvData(BaseModel):
    """Strongly typed model for Consul KV operation data."""

    key: str = Field(..., description="Consul key")
    value: str = Field(..., description="Consul value")
    flags: Optional[int] = Field(None, description="Consul flags")
    session: Optional[str] = Field(None, description="Session ID")


class ModelConsulServiceConfig(BaseModel):
    """Strongly typed model for Consul service configuration."""

    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Service name")
    address: str = Field(..., description="Service address")
    port: int = Field(..., description="Service port")
    tags: Optional[List[str]] = Field(None, description="Service tags")
    check_http: Optional[str] = Field(None, description="HTTP health check URL")
    check_interval: Optional[str] = Field(None, description="Health check interval")
    check_timeout: Optional[str] = Field(None, description="Health check timeout")


class ModelConsulAdapterInput(BaseModel):
    """Input model for Consul Adapter operations."""

    action: Literal[
        "consul_kv_get",
        "consul_kv_put",
        "consul_kv_delete",
        "consul_service_register",
        "consul_service_deregister",
        "health_check",
    ] = Field(..., description="Consul operation to perform")
    operation_type: str = Field(..., description="Type of consul operation")
    key_path: Optional[str] = Field(None, description="Consul key-value path")
    kv_data: Optional[ModelConsulKvData] = Field(
        None, description="Structured KV data for put operations"
    )
    service_config: Optional[ModelConsulServiceConfig] = Field(
        None, description="Service registration/deregistration configuration"
    )
    recurse: Optional[bool] = Field(
        False, description="For KV delete operations, delete recursively"
    )
