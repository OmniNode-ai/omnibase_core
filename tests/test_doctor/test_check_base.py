# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


class FakeCheck(DoctorCheckBase):
    check_id = "fake_check"
    check_name = "Fake Check"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY,
            message="OK",
            duration_ms=10,
        )


def test_doctor_check_base_subclass():
    check = FakeCheck()
    result = check.run()
    assert result.status == EnumHealthStatusValue.HEALTHY
    assert result.category == EnumDoctorCategory.SERVICES


def test_doctor_check_base_is_abstract():
    with pytest.raises(TypeError):
        DoctorCheckBase()  # type: ignore[abstract]
