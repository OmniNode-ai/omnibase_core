# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ROLE_TO_MODEL / DispatchReport (OMN-15161).

Ported from steel_onslaught PR #213's ``ROLE_TO_MODEL`` dispatch dict.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_dispatch_report_role import EnumDispatchReportRole
from omnibase_core.models.dispatch.report.model_dispatch_report_implementer import (
    ModelDispatchReportImplementer,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_lander import (
    ModelDispatchReportLander,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_registry import (
    ROLE_TO_MODEL,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_scout import (
    ModelDispatchReportScout,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_verifier import (
    ModelDispatchReportVerifier,
)

pytestmark = pytest.mark.unit


def test_role_to_model_covers_all_four_roles() -> None:
    assert set(ROLE_TO_MODEL) == set(EnumDispatchReportRole)


def test_role_to_model_maps_to_the_correct_class() -> None:
    assert (
        ROLE_TO_MODEL[EnumDispatchReportRole.IMPLEMENTER]
        is ModelDispatchReportImplementer
    )
    assert ROLE_TO_MODEL[EnumDispatchReportRole.VERIFIER] is ModelDispatchReportVerifier
    assert ROLE_TO_MODEL[EnumDispatchReportRole.LANDER] is ModelDispatchReportLander
    assert ROLE_TO_MODEL[EnumDispatchReportRole.SCOUT] is ModelDispatchReportScout
