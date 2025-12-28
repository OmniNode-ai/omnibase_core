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

# Resource exhaustion protection constant for DFS cycle detection.
# This constant is CRITICAL for security - it prevents denial-of-service attacks
# from maliciously crafted workflow graphs that could cause infinite loops or
# excessive CPU consumption during cycle detection.
#
# Value of 10,000 iterations is calibrated to support legitimate workflows with
# up to ~5,000 steps (worst case: each step visited twice during DFS traversal)
# while providing protection against resource exhaustion attacks.
#
# If cycle detection exceeds MAX_DFS_ITERATIONS, a ModelOnexError is raised
# with detailed context including step_count, max_iterations, and last_node
# for debugging and audit logging.
#
# Used by:
# - workflow_validator.py: WorkflowValidator.detect_cycles()
# - workflow_executor.py: _has_dependency_cycles()
# - model_dependency_graph.py: ModelDependencyGraph.has_cycles()
MAX_DFS_ITERATIONS: int = 10_000

# v1.0.4 Normative: Valid step types per CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
# Fix 41: step_type MUST be one of these values. "conditional" is NOT valid in v1.0.
# Using frozenset for immutability and O(1) membership testing.
VALID_STEP_TYPES: frozenset[str] = frozenset(
    {"compute", "effect", "reducer", "orchestrator", "custom", "parallel"}
)

__all__ = [
    "MAX_DFS_ITERATIONS",
    "MAX_TIMEOUT_MS",
    "MIN_TIMEOUT_MS",
    "RESERVED_STEP_TYPES",
    "VALID_STEP_TYPES",
]
