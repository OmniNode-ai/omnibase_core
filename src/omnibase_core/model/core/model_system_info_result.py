"""
System Information Result Model.

Defines the structured result model for system information operations
within the ONEX architecture.
"""

from typing import List, Optional

from pydantic import Field

from omnibase_core.model.core.model_base_result import ModelBaseResult
from omnibase_core.model.core.model_service_status import ModelServiceStatus
from omnibase_core.model.core.model_system_data import ModelSystemData


class ModelSystemInfoResult(ModelBaseResult):
    """
    Structured result model for system information operations.

    Contains the results of retrieving system status, health,
    and configuration information.
    """

    system_data: ModelSystemData = Field(
        default_factory=lambda: ModelSystemData(), description="System information data"
    )
    health_status: str = Field(
        default="unknown", description="Overall system health status"
    )
    services_status: List[ModelServiceStatus] = Field(
        default_factory=list, description="Status of system services"
    )
    response_time_ms: Optional[float] = Field(
        None, description="System info retrieval time in milliseconds"
    )
    format: str = Field(default="dict", description="Format of the system info output")
