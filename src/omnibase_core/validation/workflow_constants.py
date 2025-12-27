"""Shared constants for workflow validation and execution.

This module consolidates constants used by both workflow_validator.py
and workflow_executor.py to avoid duplication and ensure consistency.

These constants define normative constraints per ONEX v1.0.x specification.
"""

# Reserved step types that are not yet implemented per ONEX v1.0 contract.
# Fix 40 (v1.0.3): step_type="conditional" MUST raise ModelOnexError in v1.0.
# Conditional nodes are reserved for v1.1.
# Using frozenset for immutability and O(1) membership testing.
RESERVED_STEP_TYPES: frozenset[str] = frozenset({"conditional"})

# Minimum timeout value in milliseconds per v1.0.3 schema.
# Fix 38 (v1.0.3): timeout_ms MUST be >= 100. Any value <100 MUST raise ModelOnexError.
MIN_TIMEOUT_MS: int = 100

# Maximum allowed timeout in milliseconds (24 hours).
# This prevents DoS scenarios where extremely long timeouts could exhaust resources.
MAX_TIMEOUT_MS: int = 86400000

# v1.0.4 Normative: Valid step types per CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
# Fix 41: step_type MUST be one of these values. "conditional" is NOT valid in v1.0.
# Using frozenset for immutability and O(1) membership testing.
VALID_STEP_TYPES: frozenset[str] = frozenset(
    {"compute", "effect", "reducer", "orchestrator", "custom", "parallel"}
)

__all__ = [
    "RESERVED_STEP_TYPES",
    "MIN_TIMEOUT_MS",
    "MAX_TIMEOUT_MS",
    "VALID_STEP_TYPES",
]
