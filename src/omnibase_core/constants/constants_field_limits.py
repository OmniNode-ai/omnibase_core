"""
Centralized field length limits for ONEX models.

This module provides standardized field length limits used across all Pydantic
models in the omnibase_core package. Using these constants ensures consistency
and makes it easy to adjust limits globally.

SINGLE SOURCE OF TRUTH (SSOT)
=============================

This module is the CANONICAL SOURCE for:
- MAX_DFS_ITERATIONS: Algorithm iteration limit for DFS cycle detection
- MAX_BFS_ITERATIONS: Algorithm iteration limit for BFS traversal
- MAX_TIMEOUT_MS: Maximum timeout value (24 hours)
- Field length limits (MAX_IDENTIFIER_LENGTH, MAX_NAME_LENGTH, etc.)

Other modules (validator_workflow_constants.py, constants/__init__.py) re-export these
constants for convenience but DO NOT define them. All definitions are here.

Security Architecture
---------------------

All iteration limits in this module exist to prevent denial-of-service (DoS)
attacks. Without these limits, malicious inputs could cause:

1. **Infinite Loops**: Cyclic graphs or pathological inputs causing unbounded
   iteration in DFS/BFS algorithms
2. **CPU Exhaustion**: Worst-case algorithm complexity consuming all CPU time
3. **Memory Exhaustion**: Extremely long strings or collections causing OOM

Each limit is calibrated to support legitimate workloads while providing
effective protection:

- MAX_DFS_ITERATIONS (10,000): Supports ~5,000 node graphs (worst case: 2x visits)
- MAX_BFS_ITERATIONS (10,000): Same rationale as DFS
- MAX_TIMEOUT_MS (24 hours): Absolute maximum, prevents indefinite waits

These constants are used by:
- Model fields requiring max_length validation
- Identifier and name fields across all ONEX models
- Path and URL fields in configuration models
- Content fields such as descriptions, messages, reasons, errors, and logs
- Collection fields with size constraints
- Cycle detection in workflow_validator.py, workflow_executor.py, model_dependency_graph.py

See Also:
    - validator_workflow_constants.py: Constants Map documentation explaining the relationship
      between constants files
    - workflow_executor.py: Compression bomb mitigation documentation
"""

# =============================================================================
# Identifier Limits
# =============================================================================

# Maximum length for short identifiers (used for IDs, keys, short names)
MAX_IDENTIFIER_LENGTH: int = 100

# Maximum length for display names and titles
MAX_NAME_LENGTH: int = 255

# Maximum length for dictionary/map keys
MAX_KEY_LENGTH: int = 100

# =============================================================================
# Path Limits
# =============================================================================

# Maximum length for file system paths
MAX_PATH_LENGTH: int = 255

# Maximum length for URLs (per RFC 2616 practical limit)
MAX_URL_LENGTH: int = 2048

# =============================================================================
# Content Limits
# =============================================================================

# Maximum length for reason/rationale fields (short explanations)
MAX_REASON_LENGTH: int = 500

# Maximum length for description fields
MAX_DESCRIPTION_LENGTH: int = 1000

# Maximum length for general message fields
MAX_MESSAGE_LENGTH: int = 1500

# Maximum length for error messages
MAX_ERROR_MESSAGE_LENGTH: int = 2000

# Maximum length for log messages
MAX_LOG_MESSAGE_LENGTH: int = 4000

# =============================================================================
# Collection Limits
# =============================================================================

# Maximum number of tags per entity
MAX_TAGS_COUNT: int = 50

# Maximum number of labels per entity
MAX_LABELS_COUNT: int = 100

# Maximum length for individual label strings
MAX_LABEL_LENGTH: int = 100

# =============================================================================
# Algorithm Iteration Limits
# =============================================================================

# Maximum iterations for DFS cycle detection in workflow validation.
# SINGLE SOURCE OF TRUTH (SSOT) for this constant.
#
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
#
# NOTE: validator_workflow_constants.py re-imports this constant for workflow-specific
# exports. Both import paths are valid:
# - from omnibase_core.constants import MAX_DFS_ITERATIONS (recommended)
# - from omnibase_core.validation.validator_workflow_constants import MAX_DFS_ITERATIONS
MAX_DFS_ITERATIONS: int = 10_000

# Maximum iterations for BFS traversal in workflow linting.
# Prevents infinite loops in graph traversal operations.
MAX_BFS_ITERATIONS: int = 10_000

# Maximum timeout in milliseconds (24 hours) to prevent DoS attacks.
# Ensures extremely long timeouts cannot tie up resources indefinitely.
MAX_TIMEOUT_MS: int = 86_400_000

__all__ = [
    # Identifier limits
    "MAX_IDENTIFIER_LENGTH",
    "MAX_NAME_LENGTH",
    "MAX_KEY_LENGTH",
    # Path limits
    "MAX_PATH_LENGTH",
    "MAX_URL_LENGTH",
    # Content limits
    "MAX_REASON_LENGTH",
    "MAX_DESCRIPTION_LENGTH",
    "MAX_MESSAGE_LENGTH",
    "MAX_ERROR_MESSAGE_LENGTH",
    "MAX_LOG_MESSAGE_LENGTH",
    # Collection limits
    "MAX_TAGS_COUNT",
    "MAX_LABELS_COUNT",
    "MAX_LABEL_LENGTH",
    # Algorithm iteration limits
    "MAX_DFS_ITERATIONS",
    "MAX_BFS_ITERATIONS",
    "MAX_TIMEOUT_MS",
]
