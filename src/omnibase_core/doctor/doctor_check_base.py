# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import ClassVar

from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


class DoctorCheckBase(ABC):
    """Abstract base class for doctor checks.

    Subclasses must set check_id, check_name, category as ClassVars
    and implement run().
    """

    check_id: ClassVar[str]
    check_name: ClassVar[str]
    category: ClassVar[EnumDoctorCategory]

    @abstractmethod
    def run(self) -> ModelDoctorCheckResult:
        """Execute this check and return a result."""
        ...
