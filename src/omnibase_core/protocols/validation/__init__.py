# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Core-native validation protocols.

Protocol definitions for validation operations
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
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolContractValidationInvariantChecker": (
        "omnibase_core.protocols.protocol_contract_validation_invariant_checker",
        "ProtocolContractValidationInvariantChecker",
    ),
    "ProtocolArchitectureCompliance": (
        "omnibase_core.protocols.validation.protocol_architecture_compliance",
        "ProtocolArchitectureCompliance",
    ),
    "ProtocolComplianceReport": (
        "omnibase_core.protocols.validation.protocol_compliance_report",
        "ProtocolComplianceReport",
    ),
    "ProtocolComplianceRule": (
        "omnibase_core.protocols.validation.protocol_compliance_rule",
        "ProtocolComplianceRule",
    ),
    "ProtocolComplianceValidator": (
        "omnibase_core.protocols.validation.protocol_compliance_validator",
        "ProtocolComplianceValidator",
    ),
    "ProtocolComplianceViolation": (
        "omnibase_core.protocols.validation.protocol_compliance_violation",
        "ProtocolComplianceViolation",
    ),
    "ProtocolConstraintValidationResult": (
        "omnibase_core.protocols.validation.protocol_constraint_validation_result",
        "ProtocolConstraintValidationResult",
    ),
    "ProtocolConstraintValidator": (
        "omnibase_core.protocols.validation.protocol_constraint_validator",
        "ProtocolConstraintValidator",
    ),
    "ProtocolContractValidationEventEmitter": (
        "omnibase_core.protocols.validation.protocol_contract_validation_event_emitter",
        "ProtocolContractValidationEventEmitter",
    ),
    "ProtocolContractValidationPipeline": (
        "omnibase_core.protocols.validation.protocol_contract_validation_pipeline",
        "ProtocolContractValidationPipeline",
    ),
    "ProtocolEventSink": (
        "omnibase_core.protocols.validation.protocol_event_sink",
        "ProtocolEventSink",
    ),
    "ProtocolONEXStandards": (
        "omnibase_core.protocols.validation.protocol_onex_standards",
        "ProtocolONEXStandards",
    ),
    "ProtocolQualityValidator": (
        "omnibase_core.protocols.validation.protocol_quality_validator",
        "ProtocolQualityValidator",
    ),
    "ProtocolValidationDecorator": (
        "omnibase_core.protocols.validation.protocol_validation_decorator",
        "ProtocolValidationDecorator",
    ),
    "ProtocolValidationError": (
        "omnibase_core.protocols.validation.protocol_validation_error",
        "ProtocolValidationError",
    ),
    "ProtocolValidationResult": (
        "omnibase_core.protocols.validation.protocol_validation_result",
        "ProtocolValidationResult",
    ),
    "ProtocolValidator": (
        "omnibase_core.protocols.validation.protocol_validator",
        "ProtocolValidator",
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
