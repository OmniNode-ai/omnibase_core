# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The work-event union over every kind (OMN-16177, typed work ledger T3).

``ModelWorkEvent`` is the one type a work-ledger reader validates against.
Pydantic dispatches on ``kind`` to exactly one member, so an unknown kind is a
validation error rather than a silent fallback to some other model.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from omnibase_core.models.events.work.model_work_claim_released import (
    ModelWorkClaimReleased,
)
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_correction_recorded import (
    ModelWorkCorrectionRecorded,
)
from omnibase_core.models.events.work.model_work_friction_recorded import (
    ModelWorkFrictionRecorded,
)
from omnibase_core.models.events.work.model_work_hold_placed import (
    ModelWorkHoldPlaced,
)
from omnibase_core.models.events.work.model_work_hold_released import (
    ModelWorkHoldReleased,
)
from omnibase_core.models.events.work.model_work_ledger_epoch_opened import (
    ModelWorkLedgerEpochOpened,
)
from omnibase_core.models.events.work.model_work_message_acked import (
    ModelWorkMessageAcked,
)
from omnibase_core.models.events.work.model_work_message_sent import (
    ModelWorkMessageSent,
)
from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    ModelWorkOperatorConsentRecorded,
)
from omnibase_core.models.events.work.model_work_result_recorded import (
    ModelWorkResultRecorded,
)
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)
from omnibase_core.models.events.work.model_work_status_recorded import (
    ModelWorkStatusRecorded,
)

__all__ = ["ModelWorkEvent"]

ModelWorkEvent = Annotated[
    ModelWorkClaimRequested
    | ModelWorkClaimReleased
    | ModelWorkResultRecorded
    | ModelWorkRulingRecorded
    | ModelWorkCorrectionRecorded
    | ModelWorkHoldPlaced
    | ModelWorkHoldReleased
    | ModelWorkMessageSent
    | ModelWorkMessageAcked
    | ModelWorkStatusRecorded
    | ModelWorkFrictionRecorded
    | ModelWorkOperatorConsentRecorded
    | ModelWorkLedgerEpochOpened,
    Field(discriminator="kind"),
]
"""One work event of any kind, discriminated on ``kind``.

Every ``EnumWorkEventKind`` member has exactly one model here; the T3 tests
compare the member set to the enum, so a kind added without a model fails.
"""
