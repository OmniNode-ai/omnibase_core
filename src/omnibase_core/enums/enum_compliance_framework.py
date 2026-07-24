# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance framework identifiers for regulatory requirements."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumComplianceFramework(UtilStrValueHelper, str, Enum):
    """Supported compliance frameworks."""

    SOX = "SOX"  # Sarbanes-Oxley Act
    HIPAA = "HIPAA"  # Health Insurance Portability Act
    GDPR = "GDPR"  # General Data Protection Regulation
    PCI_DSS = "PCI_DSS"  # Payment Card Industry Data Security
    FISMA = "FISMA"  # Federal Information Security Management
    ISO27001 = "ISO27001"  # Information Security Management
    NIST = "NIST"  # NIST Cybersecurity Framework


__all__ = ["EnumComplianceFramework"]
