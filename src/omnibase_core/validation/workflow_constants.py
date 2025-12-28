"""Shared constants for workflow validation and execution.

This module consolidates constants used by both workflow_validator.py
and workflow_executor.py to avoid duplication and ensure consistency.

These constants define normative constraints per ONEX v1.0.x specification.

Workflow Execution Limits (OMN-670: Security hardening):
    These limits prevent memory exhaustion and DoS attacks:
    - MAX_WORKFLOW_STEPS: Maximum number of steps in a workflow
    - MAX_STEP_PAYLOAD_SIZE_BYTES: Maximum size of individual step payload
    - MAX_TOTAL_PAYLOAD_SIZE_BYTES: Maximum accumulated payload size

    Limits are configurable via environment variables for extreme workloads:
    - ONEX_MAX_WORKFLOW_STEPS: Override max workflow steps (bounds: 1-100,000)
    - ONEX_MAX_STEP_PAYLOAD_SIZE_BYTES: Override max step payload size (bounds: 1KB-10MB)
    - ONEX_MAX_TOTAL_PAYLOAD_SIZE_BYTES: Override max total payload size (bounds: 1KB-1GB)

    Bounds are enforced to prevent both DoS attacks (too-small limits causing many
    small workflows) and memory exhaustion (too-large limits).
"""

import logging
import os

# --- Environment Variable Helpers ---

# Module-level cache for environment-based limits to avoid repeated parsing
_cached_limits: dict[str, int] = {}


def _get_limit_from_env(env_var: str, default: int, min_val: int, max_val: int) -> int:
    """Get limit from environment variable with bounds checking and memoization.

    Uses module-level caching to avoid repeated environment variable parsing
    and bounds checking on each access.

    Args:
        env_var: Environment variable name
        default: Default value if env var not set
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated limit value (cached after first computation)
    """
    # Check cache first (memoization for repeated access)
    if env_var in _cached_limits:
        return _cached_limits[env_var]

    value = os.environ.get(env_var)
    if value is None:
        result = default
    else:
        try:
            int_value = int(value)
            result = max(min_val, min(int_value, max_val))
        except ValueError:
            logging.warning(
                f"Invalid value for {env_var}: {value}, using default {default}"
            )
            result = default

    # Cache the result for subsequent accesses
    _cached_limits[env_var] = result
    return result


def _clear_limit_cache() -> None:
    """Clear the cached limits (for testing purposes only)."""
    _cached_limits.clear()


# --- Workflow Execution Limits (OMN-670: Security hardening) ---

# Maximum number of steps in a workflow
# Configurable via ONEX_MAX_WORKFLOW_STEPS (bounds: 1-100,000)
MAX_WORKFLOW_STEPS: int = _get_limit_from_env(
    "ONEX_MAX_WORKFLOW_STEPS", default=1000, min_val=1, max_val=100000
)

# Maximum size of individual step payload in bytes
# Configurable via ONEX_MAX_STEP_PAYLOAD_SIZE_BYTES (bounds: 1KB-10MB)
MAX_STEP_PAYLOAD_SIZE_BYTES: int = _get_limit_from_env(
    "ONEX_MAX_STEP_PAYLOAD_SIZE_BYTES",
    default=64 * 1024,
    min_val=1024,
    max_val=10 * 1024 * 1024,
)

# Maximum total payload size across all steps in bytes
# Configurable via ONEX_MAX_TOTAL_PAYLOAD_SIZE_BYTES (bounds: 1KB-1GB)
MAX_TOTAL_PAYLOAD_SIZE_BYTES: int = _get_limit_from_env(
    "ONEX_MAX_TOTAL_PAYLOAD_SIZE_BYTES",
    default=10 * 1024 * 1024,
    min_val=1024,
    max_val=1024 * 1024 * 1024,
)

# --- Reserved Step Types ---

# Reserved step types that are not yet implemented per ONEX v1.0 contract.
# Fix 40 (v1.0.3): step_type="conditional" MUST raise ModelOnexError in v1.0.
# Using frozenset for immutability and O(1) membership testing.
#
# v1.1+ Roadmap: "conditional" will be added to VALID_STEP_TYPES in v1.1 to
# support conditional workflow execution with if/then/else branching.
# See Linear ticket OMN-656 for tracking.
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
#
# Step type semantics:
#   - compute: Pure data transformation (stateless, no side effects)
#   - effect: External I/O operations (API calls, DB writes, file I/O)
#   - reducer: State aggregation with FSM-driven transitions
#   - orchestrator: Workflow coordination (sub-workflows, fan-out/fan-in)
#   - parallel: Parallel execution group marker
#   - custom: Extension point for user-defined step types
#
# v1.1+ Roadmap: "conditional" will be moved from RESERVED_STEP_TYPES to this
# set to enable if/then/else branching in workflows. See Linear ticket OMN-656.
VALID_STEP_TYPES: frozenset[str] = frozenset(
    {"compute", "effect", "reducer", "orchestrator", "custom", "parallel"}
)

__all__ = [
    # Workflow execution limits (OMN-670: Security hardening)
    "MAX_STEP_PAYLOAD_SIZE_BYTES",
    "MAX_TOTAL_PAYLOAD_SIZE_BYTES",
    "MAX_WORKFLOW_STEPS",
    # Validation constants
    "MAX_DFS_ITERATIONS",
    "MAX_TIMEOUT_MS",
    "MIN_TIMEOUT_MS",
    "RESERVED_STEP_TYPES",
    "VALID_STEP_TYPES",
]
