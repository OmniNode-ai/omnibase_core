# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json

from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult
from omnibase_core.models.doctor.model_doctor_report import ModelDoctorReport


def _make_results() -> list[ModelDoctorCheckResult]:
    return [
        ModelDoctorCheckResult(
            name="Docker",
            category=EnumDoctorCategory.SERVICES,
            status=EnumHealthStatusValue.HEALTHY,
            message="running",
            duration_ms=100,
        ),
        ModelDoctorCheckResult(
            name="Linear API",
            category=EnumDoctorCategory.SERVICES,
            status=EnumHealthStatusValue.UNHEALTHY,
            message="401 unauthorized",
            duration_ms=500,
        ),
        ModelDoctorCheckResult(
            name="Python version",
            category=EnumDoctorCategory.ENVIRONMENT,
            status=EnumHealthStatusValue.HEALTHY,
            message="3.12.0",
            duration_ms=5,
        ),
    ]


def test_report_from_results():
    report = ModelDoctorReport.from_results(_make_results())
    assert report.total == 3
    assert report.passed == 2
    assert report.failed == 1


def test_report_grouped():
    report = ModelDoctorReport.from_results(_make_results())
    grouped = report.grouped()
    assert EnumDoctorCategory.SERVICES in grouped
    assert EnumDoctorCategory.ENVIRONMENT in grouped
    assert len(grouped[EnumDoctorCategory.SERVICES]) == 2


def test_report_render_human(capsys):
    report = ModelDoctorReport.from_results(_make_results())
    report.render_human()
    captured = capsys.readouterr()
    assert "Docker" in captured.out
    assert "Linear API" in captured.out
    assert "2/3" in captured.out or "passed" in captured.out.lower()


def test_report_render_json():
    report = ModelDoctorReport.from_results(_make_results())
    output = report.render_json()
    parsed = json.loads(output)
    assert parsed["total"] == 3
    assert parsed["passed"] == 2
