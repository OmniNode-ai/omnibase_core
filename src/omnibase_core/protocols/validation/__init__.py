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

# Contract Validation Invariant Checker (OMN-1146)
# Import at package level to avoid long import paths
from omnibase_core.protocols.protocol_contract_validation_invariant_checker import (
    ProtocolContractValidationInvariantChecker,
)
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
from omnibase_core.protocols.validation.protocol_constraint_validation_result import (
    ProtocolConstraintValidationResult,
)
from omnibase_core.protocols.validation.protocol_constraint_validator import (
    ProtocolConstraintValidator,
)
from omnibase_core.protocols.validation.protocol_contract_validation_event_emitter import (
    ProtocolContractValidationEventEmitter,
)
from omnibase_core.protocols.validation.protocol_contract_validation_pipeline import (
    ProtocolContractValidationPipeline,
)
from omnibase_core.protocols.validation.protocol_event_sink import ProtocolEventSink
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
    # Contract Validation Invariant Checker (OMN-1146)
    "ProtocolContractValidationInvariantChecker",
    # Compliance
    "ProtocolComplianceRule",
    "ProtocolComplianceViolation",
    "ProtocolONEXStandards",
    "ProtocolArchitectureCompliance",
    "ProtocolComplianceReport",
    "ProtocolComplianceValidator",
    # Quality
    "ProtocolQualityValidator",
    # Contract Validation Pipeline (OMN-1128)
    "ProtocolContractValidationPipeline",
    # Contract Validation Event Emitter (OMN-1151)
    "ProtocolContractValidationEventEmitter",
    # Event Sink Protocol (OMN-1151)
    "ProtocolEventSink",
    # Constraint Validator (OMN-1128 SPI Seam)
    "ProtocolConstraintValidator",
    "ProtocolConstraintValidationResult",
]
