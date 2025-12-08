"""
Core-native validation protocols.

This module provides protocol definitions for validation operations
including compliance validation and validation results. These are
Core-native equivalents of the SPI validation protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from omnibase_core.protocols.validation.protocol_architecture_compliance import (
    ProtocolArchitectureCompliance,
)
from omnibase_core.protocols.validation.protocol_compliance_report import (
    ProtocolComplianceReport,
)
from omnibase_core.protocols.validation.protocol_compliance_rule import (
    ProtocolComplianceRule,
)
from omnibase_core.protocols.validation.protocol_compliance_validator import (
    ProtocolComplianceValidator,
)
from omnibase_core.protocols.validation.protocol_compliance_violation import (
    ProtocolComplianceViolation,
)
from omnibase_core.protocols.validation.protocol_onex_standards import (
    ProtocolONEXStandards,
)
from omnibase_core.protocols.validation.protocol_quality_validator import (
    ProtocolQualityValidator,
)
from omnibase_core.protocols.validation.protocol_validation_decorator import (
    ProtocolValidationDecorator,
)
from omnibase_core.protocols.validation.protocol_validation_error import (
    ProtocolValidationError,
)
from omnibase_core.protocols.validation.protocol_validation_result import (
    ProtocolValidationResult,
)
from omnibase_core.protocols.validation.protocol_validator import ProtocolValidator

__all__ = [
    # Core Validation
    "ProtocolValidationError",
    "ProtocolValidationResult",
    "ProtocolValidator",
    "ProtocolValidationDecorator",
    # Compliance
    "ProtocolComplianceRule",
    "ProtocolComplianceViolation",
    "ProtocolONEXStandards",
    "ProtocolArchitectureCompliance",
    "ProtocolComplianceReport",
    "ProtocolComplianceValidator",
    # Quality
    "ProtocolQualityValidator",
]
