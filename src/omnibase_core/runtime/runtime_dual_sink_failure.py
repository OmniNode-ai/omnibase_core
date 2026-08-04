# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``DualPublishFailureError`` — neither dual sink became durable (OMN-15666).

Raising this is THE signal that the source offset must not be committed.

Why it lives in ``runtime`` and not ``omnibase_core.errors``
------------------------------------------------------------
``errors`` is a FOUNDATION-layer package that must never import
``omnibase_core.models.*`` (import-linter ``core-foundation-no-upward``,
OMN-14335/OMN-3210). Linear comment ``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on
OMN-15666 requires this error to expose ``primary_failure`` and
``quarantine_failure`` as ``ModelDeliveryFailureEvidence`` instances — precisely
that forbidden edge. It therefore lives beside the primitive that raises it.
``scripts/validation/validate-file-locations.py`` explicitly exempts ``*Error``
classes from directory placement ("Exception classes (can be anywhere)"), so
this is a sanctioned placement, not a worked-around gate.
"""

from __future__ import annotations

from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)

__all__ = ["DualPublishFailureError"]


class DualPublishFailureError(ModelOnexError):
    """Neither the primary DLQ nor the canonical quarantine sink became durable.

    Exposes the two failures DISTINCTLY (never one collapsed message) so a caller
    can tell "the primary was unreachable but quarantine caught it" apart from
    "both sinks are down" without parsing free text.
    """

    def __init__(
        self,
        *,
        primary_failure: ModelDeliveryFailureEvidence,
        quarantine_failure: ModelDeliveryFailureEvidence,
        source_envelope_id: UUID,
        source_topic: str,
        source_partition: int,
        source_offset: int,
    ) -> None:
        self.primary_failure = primary_failure
        self.quarantine_failure = quarantine_failure
        super().__init__(
            message=(
                "Dual-sink terminal disposition FAILED for source record "
                f"topic={source_topic!r} partition={source_partition} "
                f"offset={source_offset} envelope_id={source_envelope_id} — "
                f"primary DLQ: [{primary_failure.error_type}] "
                f"{primary_failure.error_message}; quarantine: "
                f"[{quarantine_failure.error_type}] "
                f"{quarantine_failure.error_message}. The source offset is NOT "
                "committed; the record will be reprocessed on replay."
            ),
            error_code=EnumCoreErrorCode.INVALID_STATE,
        )
