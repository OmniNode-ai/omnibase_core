# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue


class ModelDoctorCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(description="Human-readable check name")
    category: EnumDoctorCategory = Field(description="Check category for grouping")
    status: EnumHealthStatusValue = Field(description="Check result status")
    message: str = Field(default="", description="Human-readable detail")
    duration_ms: int = Field(default=0, description="Check duration in milliseconds", ge=0)

    def is_passed(self) -> bool:
        return self.status in (EnumHealthStatusValue.HEALTHY,)

    def is_skipped(self) -> bool:
        return self.status == EnumHealthStatusValue.UNKNOWN
