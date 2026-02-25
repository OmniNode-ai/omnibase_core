# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Envelope validation failure type enumeration for observability metrics."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEnvelopeValidationFailureType(StrValueHelper, str, Enum):
    """Failure type classifications for envelope validation metrics.

    Used to categorise validation failures tracked in
    ``ModelEnvelopeValidationFailureMetrics`` for observability and alerting.

    Members:
        MISSING_CORRELATION_ID: Envelope correlation_id is absent or None.
        INVALID_ENVELOPE_STRUCTURE: Envelope fails Pydantic schema validation.
        EMPTY_PAYLOAD: Envelope payload field is present but contains no data.
        TYPE_MISMATCH: Payload type does not match the declared envelope type.
        MISSING_MESSAGE_ID: Envelope message_id is absent or None.
        MISSING_ENTITY_ID: Envelope entity_id is absent or empty.
        UNKNOWN: Failure does not match any known category.
    """

    MISSING_CORRELATION_ID = "missing_correlation_id"
    """Envelope correlation_id is absent or None."""

    INVALID_ENVELOPE_STRUCTURE = "invalid_envelope_structure"
    """Envelope fails Pydantic schema validation."""

    EMPTY_PAYLOAD = "empty_payload"
    """Envelope payload field is present but contains no data."""

    TYPE_MISMATCH = "type_mismatch"
    """Payload type does not match the declared envelope type."""

    MISSING_MESSAGE_ID = "missing_message_id"
    """Envelope message_id is absent or None."""

    MISSING_ENTITY_ID = "missing_entity_id"
    """Envelope entity_id is absent or empty."""

    UNKNOWN = "unknown"
    """Failure does not match any known category."""


__all__ = ["EnumEnvelopeValidationFailureType"]
