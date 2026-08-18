# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-event models (OMN-16177).

Schema for the five work-event kinds that make the rolling work ledger a
materialized projection over the ordinary hook-captured event stream rather
than a hand-appended markdown file.

Placed in ``omnibase_core`` because work events are emitted from two repos —
omniclaude hooks (session actors) and omnimarket nodes (node actors) — and
core is the layer both depend on. ``omnibase_compat`` cannot host these:
omniclaude declares no compat dependency, so half the emitters could not
import them.
"""

from omnibase_core.models.events.work.model_actor import ModelActor
from omnibase_core.models.events.work.model_node_actor import ModelNodeActor
from omnibase_core.models.events.work.model_pr_ref import ModelPrRef
from omnibase_core.models.events.work.model_quant_claim import ModelQuantClaim
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor
from omnibase_core.models.events.work.model_work_claim_released import (
    ModelWorkClaimReleased,
)
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_correction_recorded import (
    ModelWorkCorrectionRecorded,
)
from omnibase_core.models.events.work.model_work_event_base import (
    SUMMARY_MAX_LENGTH,
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelWorkEventBase,
)
from omnibase_core.models.events.work.model_work_result_recorded import (
    ModelWorkResultRecorded,
)
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)

__all__ = [
    "SUMMARY_MAX_LENGTH",
    "WORK_EVENT_PARTITION_KEY_FIELDS",
    "ModelActor",
    "ModelNodeActor",
    "ModelPrRef",
    "ModelQuantClaim",
    "ModelSessionActor",
    "ModelWorkClaimReleased",
    "ModelWorkClaimRequested",
    "ModelWorkCorrectionRecorded",
    "ModelWorkEventBase",
    "ModelWorkResultRecorded",
    "ModelWorkRulingRecorded",
]
