# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Role-to-model dispatch registry for dispatch report contracts (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``ROLE_TO_MODEL`` +
``DispatchReport`` union (originally
``steel_onslaught.contracts.dispatch_report``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from omnibase_core.enums.enum_dispatch_report_role import EnumDispatchReportRole
from omnibase_core.models.dispatch.report.model_dispatch_report_implementer import (
    ModelDispatchReportImplementer,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_lander import (
    ModelDispatchReportLander,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_scout import (
    ModelDispatchReportScout,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_verifier import (
    ModelDispatchReportVerifier,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["ROLE_TO_MODEL", "DispatchReport"]

# Discriminated on "role" (mirrors ModelDirectivePayload's "kind" discriminator,
# omnibase_core.models.runtime.payloads.model_directive_payload_union) so pydantic
# dispatches directly to the matching role's model instead of trying every union
# branch in sequence.
DispatchReport = Annotated[
    ModelDispatchReportImplementer
    | ModelDispatchReportVerifier
    | ModelDispatchReportLander
    | ModelDispatchReportScout,
    Field(discriminator="role"),
]

ROLE_TO_MODEL: dict[EnumDispatchReportRole, type[BaseModel]] = {
    EnumDispatchReportRole.IMPLEMENTER: ModelDispatchReportImplementer,
    EnumDispatchReportRole.VERIFIER: ModelDispatchReportVerifier,
    EnumDispatchReportRole.LANDER: ModelDispatchReportLander,
    EnumDispatchReportRole.SCOUT: ModelDispatchReportScout,
}
