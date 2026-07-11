# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict definition for signature optional parameters.

A TypedDict for optional parameters used in signature
factory methods, following ONEX TypedDict naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm


class TypedDictSignatureOptionalParams(TypedDict, total=False):
    """Optional parameters for signature factory methods."""

    node_name: str | None
    timestamp: datetime
    signature_algorithm: EnumSignatureAlgorithm
    certificate_thumbprint: str | None
    # OMN-14337: was the operation-details domain model (immovable).
    operation_details: object | None
    previous_signature_hash: str | None
    security_clearance: str | None
    processing_time_ms: int | None
    signature_time_ms: int | None
    error_message: str | None
    warning_messages: list[str]
    # OMN-14337: was the signature-metadata domain model (immovable).
    signature_metadata: object | None


__all__ = ["TypedDictSignatureOptionalParams"]
