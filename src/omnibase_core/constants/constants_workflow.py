# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared constants for workflow validation and execution.

This module consolidates constants used by both workflow_validator.py
and workflow_executor.py to avoid duplication and ensure consistency.

These constants define normative constraints per ONEX v1.0.x specification.

Constants Map - ONEX Constants Architecture
-------------------------------------------

The ONEX framework organizes constants across multiple files based on their
domain and usage patterns. Understanding this architecture is critical for
maintainability and avoiding duplication.

**omnibase_core/constants/constants_field_limits.py** (Canonical Source):
    Centralized field length and algorithm iteration limits. This is the
    SINGLE SOURCE OF TRUTH (SSOT) for limits that protect against resource
    exhaustion attacks:

    - MAX_DFS_ITERATIONS (10,000): Protects cycle detection from DoS attacks
    - MAX_BFS_ITERATIONS (10,000): Protects BFS traversal operations
    - MAX_TIMEOUT_MS (86,400,000): Maximum timeout (24 hours) to prevent DoS
    - MAX_IDENTIFIER_LENGTH, MAX_NAME_LENGTH, etc.: Field length limits

    When to use: Import from here for general-purpose limits, especially
    when writing new validators or algorithms that need iteration bounds.

    Example: ``from omnibase_core.constants import MAX_DFS_ITERATIONS``

**omnibase_core/constants/constants_workflow.py** (This Module):
    Workflow-specific limits and configuration. Re-exports MAX_DFS_ITERATIONS
    from constants_field_limits.py for workflow module convenience.

    - MAX_WORKFLOW_STEPS: Maximum steps per workflow (env-configurable)
    - MAX_STEP_PAYLOAD_SIZE_BYTES: Per-step payload limit (env-configurable)
    - MAX_TOTAL_PAYLOAD_SIZE_BYTES: Total payload limit (env-configurable)
    - MIN_TIMEOUT_MS (100ms): Minimum timeout per ONEX v1.0.3 schema
    - MAX_TIMEOUT_MS (24h): Maximum timeout to prevent resource exhaustion
    - VALID_STEP_TYPES: Allowed step types per ONEX v1.0.4
    - RESERVED_STEP_TYPES: Reserved for future versions (e.g., "conditional")

    When to use: Import from here when working with workflow validation,
    execution, or orchestration code.

    Example: ``from omnibase_core.constants.constants_workflow import MAX_WORKFLOW_STEPS``

**omnibase_core/constants/constants_timeouts.py**:
    General timeout values for I/O operations across the framework:

    - TIMEOUT_DEFAULT_MS (30,000ms): Standard I/O timeout
    - TIMEOUT_LONG_MS (300,000ms): Extended timeout for complex operations
    - TIMEOUT_MIN_MS (1,000ms): Minimum realistic timeout
    - TIMEOUT_MAX_MS (600,000ms): Maximum timeout (10 minutes)

    When to use: Import from here for effect operations, HTTP/DB/Kafka I/O,
    and general timeout configuration.

    Example: ``from omnibase_core.constants import TIMEOUT_DEFAULT_MS``

**Why Multiple Timeout Constants?**:
    - constants_field_limits.MAX_TIMEOUT_MS (24h): Absolute maximum for any timeout
    - constants_timeouts.TIMEOUT_MAX_MS (10min): Practical maximum for I/O operations
    - constants_workflow.MAX_TIMEOUT_MS (24h): Workflow-specific re-export for validation

    The 24-hour limit protects against DoS via extremely long timeouts.
    The 10-minute limit is a practical bound for most I/O operations.

Security Rationale
------------------

All iteration and size limits exist to prevent denial-of-service attacks:

1. **Iteration Limits (MAX_DFS_ITERATIONS, MAX_BFS_ITERATIONS)**:
   Prevent infinite loops from maliciously crafted cyclic graphs or pathological
   inputs. An attacker could submit workflows designed to exhaust CPU by triggering
   worst-case graph traversal behavior.

2. **Timeout Bounds (MIN_TIMEOUT_MS, MAX_TIMEOUT_MS)**:
   Prevent resource exhaustion from extremely long timeouts that could tie up
   worker threads indefinitely. The minimum prevents ineffective sub-100ms timeouts.

3. **Payload Size Limits (MAX_STEP_PAYLOAD_SIZE_BYTES, MAX_TOTAL_PAYLOAD_SIZE_BYTES)**:
   Prevent memory exhaustion from oversized payloads. Validated on deserialized
   data to protect against compression bomb attacks (see workflow_executor.py).

4. **Fixed Core ceilings**:
   The workflow execution limits below are immutable Core constants. Nothing —
   no environment variable, no contract, no per-workflow field — can raise or
   lower them at runtime. That is deliberate: these limits are the DoS
   protection itself, so a configuration surface for them would be a surface
   for turning the protection off (OMN-17554).

Workflow Execution Limits (OMN-670: Security hardening):
    These limits prevent memory exhaustion and DoS attacks:
    - MAX_WORKFLOW_STEPS: Maximum number of steps in a workflow
    - MAX_STEP_PAYLOAD_SIZE_BYTES: Maximum size of individual step payload
    - MAX_TOTAL_PAYLOAD_SIZE_BYTES: Maximum accumulated payload size

    They are module-level constants with no configuration path. Workflow
    contracts do not configure or override them.

Thread Safety:
    Every value in this module is an immutable module-level constant read at
    import time. There is no cache, no lazy initialisation and no mutable
    module state, so concurrent readers need no synchronization.
"""

# --- Workflow Execution Limits (OMN-670: Security hardening) ---
#
# These three limits are fixed, immutable Core ceilings. They are not
# configurable: not by environment variable, not by contract, and not per
# workflow (OMN-17554). They exist to bound resource consumption for every
# workflow this build executes, so a per-deployment override would be a way to
# opt out of the DoS protection rather than a way to tune it. Changing a
# ceiling is a Core change with a Core review.
#
# Before OMN-17554 each was read from an ``ONEX_MAX_*`` environment variable
# through a memoizing helper that clamped out-of-range values and logged a
# warning. Nothing consumed that authority except the module's own import-time
# initialisation, and the clamp meant an operator could only ever move a limit
# within a range Core already declared safe.

# Maximum number of steps in a workflow.
MAX_WORKFLOW_STEPS: int = 1000

# Maximum size of an individual step payload, in bytes (64 KB).
MAX_STEP_PAYLOAD_SIZE_BYTES: int = 64 * 1024

# Maximum total payload size across all steps, in bytes (10 MB).
MAX_TOTAL_PAYLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

# --- Reserved Step Types ---

# Reserved step types that are not yet implemented per ONEX v1.0 contract.
# Fix 40 (v1.0.3): step_type="conditional" MUST raise ModelOnexError in v1.0.
# Using frozenset for immutability and O(1) membership testing.
#
# v1.1+ Roadmap: "conditional" will be added to VALID_STEP_TYPES in v1.1 to
# support conditional workflow execution with if/then/else branching.
# See Linear ticket OMN-656 for tracking.
RESERVED_STEP_TYPES: frozenset[str] = frozenset({"conditional"})

# =============================================================================
# Workflow Timeout Constants
# =============================================================================
#
# TIMEOUT HIERARCHY DOCUMENTATION:
# The ONEX framework uses a tiered timeout system to prevent both busy-waiting
# (timeouts too short) and resource exhaustion (timeouts too long).
#
# Tier 1: MIN_TIMEOUT_MS (100ms) - Absolute minimum for any timeout
#   - Prevents busy-waiting and rapid retry loops
#   - Applied to: step timeouts, event timeouts, all timeout fields
#   - Why 100ms: Allows sub-second operations while preventing CPU-burning loops
#
# Tier 2: TIMEOUT_LONG_MS (5 minutes) - Step-level maximum
#   - Individual workflow steps should complete quickly
#   - Longer operations should be async or broken into smaller steps
#   - Defined in: omnibase_core/constants/constants_timeouts.py
#   - Used by: ModelWorkflowStep.timeout_ms (le=TIMEOUT_LONG_MS)
#
# Tier 3: MAX_TIMEOUT_MS (24 hours) - Event-level maximum
#   - Allows long-running event processing (batch jobs, ETL, ML training)
#   - Prevents DoS via extremely long timeouts that could exhaust resources
#   - Used by: ModelEventInputState.timeout_ms (le=MAX_TIMEOUT_MS)
#
# Cross-References:
#   - Step timeout bounds: omnibase_core/models/contracts/model_workflow_step.py
#   - Event timeout bounds: omnibase_core/models/core/model_event_input_state.py
#   - I/O timeout constants: omnibase_core/constants/constants_timeouts.py
# =============================================================================

# Minimum timeout value in milliseconds per v1.0.3 schema.
# Fix 38 (v1.0.3): timeout_ms MUST be >= 100. Any value <100 MUST raise ModelOnexError.
# Rationale: Prevents busy-waiting scenarios where extremely short timeouts would
# cause rapid retry loops consuming excessive CPU resources.
MIN_TIMEOUT_MS: int = 100

# Maximum allowed timeout in milliseconds (24 hours).
# This prevents DoS scenarios where extremely long timeouts could exhaust resources.
# Used for event-level timeouts which may span long-running operations like ETL or ML training.
# For step-level timeouts, see TIMEOUT_LONG_MS (5 min) in constants_timeouts.py.
MAX_TIMEOUT_MS: int = 86400000

# Resource exhaustion protection constant for DFS cycle detection.
# CANONICAL SOURCE: omnibase_core.constants.constants_field_limits
# Re-exported here for workflow-specific convenience.
#
# See constants_field_limits.py for full documentation on security rationale,
# value calibration, and usage locations.
from omnibase_core.constants.constants_field_limits import MAX_DFS_ITERATIONS

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
