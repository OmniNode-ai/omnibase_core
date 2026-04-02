# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


def test_doctor_category_has_expected_members():
    assert EnumDoctorCategory.SERVICES == "services"
    assert EnumDoctorCategory.REPOS == "repos"
    assert EnumDoctorCategory.ENVIRONMENT == "environment"


def test_doctor_check_result_pass():
    result = ModelDoctorCheckResult(
        name="Docker running",
        category=EnumDoctorCategory.SERVICES,
        status=EnumHealthStatusValue.HEALTHY,
        message="Docker daemon is running",
        duration_ms=200,
    )
    assert result.name == "Docker running"
    assert result.is_passed()


def test_doctor_check_result_fail():
    result = ModelDoctorCheckResult(
        name="Linear API",
        category=EnumDoctorCategory.SERVICES,
        status=EnumHealthStatusValue.UNHEALTHY,
        message="401 unauthorized",
        duration_ms=500,
    )
    assert not result.is_passed()


def test_doctor_check_result_skip():
    result = ModelDoctorCheckResult(
        name="Redis",
        category=EnumDoctorCategory.SERVICES,
        status=EnumHealthStatusValue.UNKNOWN,
        message="Skipped: not configured",
        duration_ms=0,
    )
    assert result.is_skipped()
