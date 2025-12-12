"""
TypedDict definition for signature optional parameters.

This module provides a TypedDict for optional parameters used in signature
factory methods, following ONEX TypedDict naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm
    from omnibase_core.models.security.model_operation_details import (
        ModelOperationDetails,
    )
    from omnibase_core.models.security.model_signature_metadata import (
        ModelSignatureMetadata,
    )


class TypedDictSignatureOptionalParams(TypedDict, total=False):
    """Optional parameters for signature factory methods."""

    node_name: str | None
    timestamp: datetime
    signature_algorithm: EnumSignatureAlgorithm
    certificate_thumbprint: str | None
    operation_details: ModelOperationDetails | None
    previous_signature_hash: str | None
    security_clearance: str | None
    processing_time_ms: int | None
    signature_time_ms: int | None
    error_message: str | None
    warning_messages: list[str]
    signature_metadata: ModelSignatureMetadata | None


__all__ = ["TypedDictSignatureOptionalParams"]
