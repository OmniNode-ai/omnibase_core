# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumNodeOperation(UtilStrValueHelper, str, Enum):
    """Types of operations a node can perform on an envelope."""

    SOURCE = "source"  # Original envelope creation
    ROUTE = "route"  # Routing decision and forwarding
    TRANSFORM = "transform"  # Data transformation or enrichment
    VALIDATE = "validate"  # Validation or compliance checking
    DESTINATION = "destination"  # Final delivery and processing
    ENCRYPTION = "encryption"  # Payload encryption/decryption
    AUDIT = "audit"  # Audit logging and compliance


__all__ = ["EnumNodeOperation"]
