# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase

pytestmark = pytest.mark.unit
from omnibase_core.doctor.doctor_registry import DoctorRegistry
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


class StubCheck(DoctorCheckBase):
    check_id = "stub"
    check_name = "Stub"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY,
            message="OK",
        )


def test_register_and_list():
    registry = DoctorRegistry()
    registry.register(StubCheck)
    checks = registry.list_all()
    assert len(checks) == 1
    assert checks[0].check_id == "stub"


def test_register_duplicate_raises():
    registry = DoctorRegistry()
    registry.register(StubCheck)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubCheck)


def test_discover_loads_entry_points():
    """Entry point discovery instantiates check classes."""
    mock_ep = MagicMock()
    mock_ep.name = "stub"
    mock_ep.load.return_value = StubCheck

    with patch(
        "omnibase_core.doctor.doctor_registry.entry_points", return_value=[mock_ep]
    ):
        registry = DoctorRegistry()
        registry.discover()
        assert len(registry.list_all()) == 1


def test_run_all_returns_results():
    registry = DoctorRegistry()
    registry.register(StubCheck)
    results = registry.run_all()
    assert len(results) == 1
    assert results[0].status == EnumHealthStatusValue.HEALTHY
