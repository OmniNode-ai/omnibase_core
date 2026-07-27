# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ROLE_TO_MODEL / DispatchReport (OMN-15161).

Ported from steel_onslaught PR #213's ``ROLE_TO_MODEL`` dispatch dict.
"""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from omnibase_core.enums.enum_dispatch_report_role import EnumDispatchReportRole
from omnibase_core.models.dispatch.report.model_dispatch_report_implementer import (
    ModelDispatchReportImplementer,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_lander import (
    ModelDispatchReportLander,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_registry import (
    ROLE_TO_MODEL,
    DispatchReport,
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


def test_dispatch_report_union_dispatches_on_role_discriminator() -> None:
    """``DispatchReport`` is ``Field(discriminator="role")`` -- pydantic must
    route straight to the matching role's model via the ``role`` field rather
    than trying each union branch in sequence."""
    adapter: TypeAdapter[DispatchReport] = TypeAdapter(DispatchReport)

    scout_payload = {
        "role": "scout",
        "verdict": "found",
        "findings_paths": ["a.txt"],
        "summary": (
            "Located the existing structural-incentive model this ticket should mirror "
            "for style: one BaseModel per concept, frozen+extra=forbid+strict config."
        ),
    }
    result = adapter.validate_json(json.dumps(scout_payload))
    assert isinstance(result, ModelDispatchReportScout)


def test_dispatch_report_union_rejects_unknown_role_discriminator() -> None:
    adapter: TypeAdapter[DispatchReport] = TypeAdapter(DispatchReport)
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps({"role": "not-a-real-role"}))
