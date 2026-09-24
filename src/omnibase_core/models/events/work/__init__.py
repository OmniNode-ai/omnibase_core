# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-event models (OMN-16177).

Schema for the work-event kinds that make the rolling work ledger a
materialized projection over the ordinary hook-captured event stream rather
than a hand-appended markdown file.

Placed in ``omnibase_core`` because work events are emitted from two repos —
omniclaude hooks (session actors) and omnimarket nodes (node actors) — and
core is the layer both depend on. ``omnibase_compat`` cannot host these:
omniclaude declares no compat dependency, so half the emitters could not
import them.
"""

from omnibase_core.models.events.work.model_actor import ModelActor
from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
from omnibase_core.models.events.work.model_node_actor import ModelNodeActor
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_pr_ref import ModelPrRef
from omnibase_core.models.events.work.model_quant_claim import ModelQuantClaim
from omnibase_core.models.events.work.model_recipients import ModelRecipients
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
from omnibase_core.models.events.work.model_work_event_union import ModelWorkEvent
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
from omnibase_core.models.events.work.model_work_ledger_line import (
    WORK_LEDGER_EVENTS_PATH_ENV,
    dump_work_ledger_line,
    events_path_from_env,
    parse_work_ledger_line,
)
from omnibase_core.models.events.work.model_work_ledger_record import (
    WORK_LEDGER_SCHEMA,
    ModelWorkLedgerRecord,
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

__all__ = [
    "SUMMARY_MAX_LENGTH",
    "WORK_EVENT_PARTITION_KEY_FIELDS",
    "WORK_LEDGER_EVENTS_PATH_ENV",
    "WORK_LEDGER_SCHEMA",
    "ModelActor",
    "ModelHoldScope",
    "ModelNodeActor",
    "ModelPrKey",
    "ModelPrRef",
    "ModelQuantClaim",
    "ModelRecipients",
    "ModelSessionActor",
    "ModelWorkClaimReleased",
    "ModelWorkClaimRequested",
    "ModelWorkCorrectionRecorded",
    "ModelWorkEvent",
    "ModelWorkEventBase",
    "ModelWorkFrictionRecorded",
    "ModelWorkHoldPlaced",
    "ModelWorkHoldReleased",
    "ModelWorkLedgerEpochOpened",
    "ModelWorkLedgerRecord",
    "ModelWorkMessageAcked",
    "ModelWorkMessageSent",
    "ModelWorkOperatorConsentRecorded",
    "ModelWorkResultRecorded",
    "ModelWorkRulingRecorded",
    "ModelWorkStatusRecorded",
    "dump_work_ledger_line",
    "events_path_from_env",
    "parse_work_ledger_line",
]
