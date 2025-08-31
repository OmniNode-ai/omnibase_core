"""Input model for Consul Adapter operations."""

from typing import Literal

from pydantic import BaseModel, Field


class ModelConsulKvData(BaseModel):
    """Strongly typed model for Consul KV operation data."""

    key: str = Field(..., description="Consul key")
    value: str = Field(..., description="Consul value")
    flags: int | None = Field(None, description="Consul flags")
    session: str | None = Field(None, description="Session ID")


class ModelConsulServiceConfig(BaseModel):
    """Strongly typed model for Consul service configuration."""

    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Service name")
    address: str = Field(..., description="Service address")
    port: int = Field(..., description="Service port")
    tags: list[str] | None = Field(None, description="Service tags")
    check_http: str | None = Field(None, description="HTTP health check URL")
    check_interval: str | None = Field(None, description="Health check interval")
    check_timeout: str | None = Field(None, description="Health check timeout")


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
    key_path: str | None = Field(None, description="Consul key-value path")
    kv_data: ModelConsulKvData | None = Field(
        None,
        description="Structured KV data for put operations",
    )
    service_config: ModelConsulServiceConfig | None = Field(
        None,
        description="Service registration/deregistration configuration",
    )
    recurse: bool | None = Field(
        False,
        description="For KV delete operations, delete recursively",
    )
