from pydantic import BaseModel, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS


class ModelTimeoutConfig(BaseModel):
    """Timeout configuration model."""

    default_timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS, description="Default timeout in milliseconds"
    )
    gateway_timeout_ms: int = Field(
        default=10000, description="Gateway routing timeout"
    )
    health_check_timeout_ms: int = Field(
        default=5000, description="Health check timeout"
    )
    api_call_timeout_ms: int = Field(
        default=10000, description="External API call timeout"
    )
    workflow_step_timeout_ms: int = Field(
        default=60000, description="Workflow step timeout"
    )
