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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.events.work.model_actor import ModelActor
    from omnibase_core.models.events.work.model_evidence_refs import ModelEvidenceRefs
    from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
    from omnibase_core.models.events.work.model_ledger_row_ref import ModelLedgerRowRef
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
    from omnibase_core.models.events.work.model_work_goal_revised import (
        ModelWorkGoalRevised,
    )
    from omnibase_core.models.events.work.model_work_goal_revision_resolution import (
        ModelWorkGoalRevisionResolution,
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
    from omnibase_core.models.events.work.model_work_question_asked import (
        ModelWorkQuestionAsked,
    )
    from omnibase_core.models.events.work.model_work_question_withdrawn import (
        ModelWorkQuestionWithdrawn,
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
    "ModelEvidenceRefs",
    "ModelHoldScope",
    "ModelLedgerRowRef",
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
    "ModelWorkGoalRevised",
    "ModelWorkGoalRevisionResolution",
    "ModelWorkHoldPlaced",
    "ModelWorkHoldReleased",
    "ModelWorkLedgerEpochOpened",
    "ModelWorkLedgerRecord",
    "ModelWorkMessageAcked",
    "ModelWorkMessageSent",
    "ModelWorkOperatorConsentRecorded",
    "ModelWorkQuestionAsked",
    "ModelWorkQuestionWithdrawn",
    "ModelWorkResultRecorded",
    "ModelWorkRulingRecorded",
    "ModelWorkStatusRecorded",
    "dump_work_ledger_line",
    "events_path_from_env",
    "parse_work_ledger_line",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelActor": ("omnibase_core.models.events.work.model_actor", "ModelActor"),
    "ModelEvidenceRefs": (
        "omnibase_core.models.events.work.model_evidence_refs",
        "ModelEvidenceRefs",
    ),
    "ModelHoldScope": (
        "omnibase_core.models.events.work.model_hold_scope",
        "ModelHoldScope",
    ),
    "ModelLedgerRowRef": (
        "omnibase_core.models.events.work.model_ledger_row_ref",
        "ModelLedgerRowRef",
    ),
    "ModelNodeActor": (
        "omnibase_core.models.events.work.model_node_actor",
        "ModelNodeActor",
    ),
    "ModelPrKey": ("omnibase_core.models.events.work.model_pr_key", "ModelPrKey"),
    "ModelPrRef": ("omnibase_core.models.events.work.model_pr_ref", "ModelPrRef"),
    "ModelQuantClaim": (
        "omnibase_core.models.events.work.model_quant_claim",
        "ModelQuantClaim",
    ),
    "ModelRecipients": (
        "omnibase_core.models.events.work.model_recipients",
        "ModelRecipients",
    ),
    "ModelSessionActor": (
        "omnibase_core.models.events.work.model_session_actor",
        "ModelSessionActor",
    ),
    "ModelWorkClaimReleased": (
        "omnibase_core.models.events.work.model_work_claim_released",
        "ModelWorkClaimReleased",
    ),
    "ModelWorkClaimRequested": (
        "omnibase_core.models.events.work.model_work_claim_requested",
        "ModelWorkClaimRequested",
    ),
    "ModelWorkCorrectionRecorded": (
        "omnibase_core.models.events.work.model_work_correction_recorded",
        "ModelWorkCorrectionRecorded",
    ),
    "SUMMARY_MAX_LENGTH": (
        "omnibase_core.models.events.work.model_work_event_base",
        "SUMMARY_MAX_LENGTH",
    ),
    "WORK_EVENT_PARTITION_KEY_FIELDS": (
        "omnibase_core.models.events.work.model_work_event_base",
        "WORK_EVENT_PARTITION_KEY_FIELDS",
    ),
    "ModelWorkEventBase": (
        "omnibase_core.models.events.work.model_work_event_base",
        "ModelWorkEventBase",
    ),
    "ModelWorkEvent": (
        "omnibase_core.models.events.work.model_work_event_union",
        "ModelWorkEvent",
    ),
    "ModelWorkFrictionRecorded": (
        "omnibase_core.models.events.work.model_work_friction_recorded",
        "ModelWorkFrictionRecorded",
    ),
    "ModelWorkGoalRevised": (
        "omnibase_core.models.events.work.model_work_goal_revised",
        "ModelWorkGoalRevised",
    ),
    "ModelWorkGoalRevisionResolution": (
        "omnibase_core.models.events.work.model_work_goal_revision_resolution",
        "ModelWorkGoalRevisionResolution",
    ),
    "ModelWorkHoldPlaced": (
        "omnibase_core.models.events.work.model_work_hold_placed",
        "ModelWorkHoldPlaced",
    ),
    "ModelWorkHoldReleased": (
        "omnibase_core.models.events.work.model_work_hold_released",
        "ModelWorkHoldReleased",
    ),
    "ModelWorkLedgerEpochOpened": (
        "omnibase_core.models.events.work.model_work_ledger_epoch_opened",
        "ModelWorkLedgerEpochOpened",
    ),
    "WORK_LEDGER_EVENTS_PATH_ENV": (
        "omnibase_core.models.events.work.model_work_ledger_line",
        "WORK_LEDGER_EVENTS_PATH_ENV",
    ),
    "dump_work_ledger_line": (
        "omnibase_core.models.events.work.model_work_ledger_line",
        "dump_work_ledger_line",
    ),
    "events_path_from_env": (
        "omnibase_core.models.events.work.model_work_ledger_line",
        "events_path_from_env",
    ),
    "parse_work_ledger_line": (
        "omnibase_core.models.events.work.model_work_ledger_line",
        "parse_work_ledger_line",
    ),
    "WORK_LEDGER_SCHEMA": (
        "omnibase_core.models.events.work.model_work_ledger_record",
        "WORK_LEDGER_SCHEMA",
    ),
    "ModelWorkLedgerRecord": (
        "omnibase_core.models.events.work.model_work_ledger_record",
        "ModelWorkLedgerRecord",
    ),
    "ModelWorkMessageAcked": (
        "omnibase_core.models.events.work.model_work_message_acked",
        "ModelWorkMessageAcked",
    ),
    "ModelWorkMessageSent": (
        "omnibase_core.models.events.work.model_work_message_sent",
        "ModelWorkMessageSent",
    ),
    "ModelWorkOperatorConsentRecorded": (
        "omnibase_core.models.events.work.model_work_operator_consent_recorded",
        "ModelWorkOperatorConsentRecorded",
    ),
    "ModelWorkQuestionAsked": (
        "omnibase_core.models.events.work.model_work_question_asked",
        "ModelWorkQuestionAsked",
    ),
    "ModelWorkQuestionWithdrawn": (
        "omnibase_core.models.events.work.model_work_question_withdrawn",
        "ModelWorkQuestionWithdrawn",
    ),
    "ModelWorkResultRecorded": (
        "omnibase_core.models.events.work.model_work_result_recorded",
        "ModelWorkResultRecorded",
    ),
    "ModelWorkRulingRecorded": (
        "omnibase_core.models.events.work.model_work_ruling_recorded",
        "ModelWorkRulingRecorded",
    ),
    "ModelWorkStatusRecorded": (
        "omnibase_core.models.events.work.model_work_status_recorded",
        "ModelWorkStatusRecorded",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
