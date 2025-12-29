"""
Constants for effect execution.

Single source of truth for effect-related constants to avoid magic numbers
and ensure consistent defaults across the codebase.

VERSION: 1.0.0

Author: ONEX Framework Team
"""

import os
import re

from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

# ==============================================================================
# Debug Mode Configuration
# ==============================================================================

# Debug mode for thread safety validation.
# Enable via ONEX_DEBUG_THREAD_SAFETY=1 environment variable.
# When enabled, runtime checks validate that NodeEffect and MixinEffectExecution
# instances are accessed from the same thread that created them.
# Has zero overhead when disabled (just a None check).
DEBUG_THREAD_SAFETY: bool = os.environ.get("ONEX_DEBUG_THREAD_SAFETY", "0") == "1"

# ==============================================================================
# Timeout Constants
# ==============================================================================

# Default operation timeout in milliseconds (30 seconds).
# Used as the final fallback when no timeout is specified in:
#   - ModelEffectInput.operation_timeout_ms
#   - ModelEffectOperation.operation_timeout_ms
#   - Individual IO config timeout_ms
#
# This matches the resolved context timeout defaults for consistency.
# For production use, always set explicit timeouts in operation definitions.
# Alias to centralized TIMEOUT_DEFAULT_MS (canonical source: constants_timeouts.py).
DEFAULT_OPERATION_TIMEOUT_MS: int = TIMEOUT_DEFAULT_MS

# ==============================================================================
# Field Extraction Constants
# ==============================================================================

# Maximum depth for nested field extraction to prevent denial-of-service
# attacks via deeply nested or maliciously crafted field paths.
# Default of 10 is sufficient for typical use cases while preventing abuse.
DEFAULT_MAX_FIELD_EXTRACTION_DEPTH: int = 10

# Field path validation pattern - only allow safe characters.
# Prevents injection attacks via malicious paths like __import__, eval(), etc.
# Allowed characters:
#   - a-z, A-Z: Alphanumeric field names
#   - 0-9: Numeric field names or array indices in path segments
#   - _: Underscore for snake_case field names
#   - .: Dot separator for nested field access
#
# Disallowed patterns (examples):
#   - __import__  (rejected: double underscore)
#   - eval()      (rejected: parentheses)
#   - foo;bar     (rejected: semicolon)
#   - path/../etc (rejected: double dot is allowed but ../ path traversal is not)
#   - a[0]        (rejected: brackets)
#   - ${var}      (rejected: special characters)
SAFE_FIELD_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_.]+$")

# ==============================================================================
# Security: Denied Built-ins for Template Injection Protection
# ==============================================================================

# Python built-ins and special attributes that should NEVER be accessible
# via template field paths. This provides defense-in-depth against template
# injection attacks, complementing SAFE_FIELD_PATTERN character validation.
#
# While SAFE_FIELD_PATTERN blocks special characters (parentheses, brackets, etc.),
# this deny-list explicitly blocks dangerous Python identifiers that only contain
# allowed characters (alphanumeric + underscore).
#
# Categories of denied items:
#   1. Code execution: __import__, eval, exec, compile
#   2. Introspection: globals, locals, vars, dir
#   3. Attribute manipulation: getattr, setattr, delattr, hasattr
#   4. Class/type introspection: __class__, __bases__, __mro__, __subclasses__
#   5. Special attributes: __builtins__, __dict__, __globals__, __code__
#   6. Module access: __loader__, __spec__, __file__, __name__
#   7. Callable access: __call__, __init__, __new__
#
# Security Note: This deny-list is intentionally comprehensive. Some items
# (like __init__) may seem harmless in isolation, but can be chained in
# sophisticated attacks (e.g., accessing __class__.__bases__[0].__subclasses__()).
DENIED_BUILTINS: frozenset[str] = frozenset(
    {
        # Code execution functions
        "import",
        "__import__",
        "eval",
        "exec",
        "compile",
        "execfile",  # Python 2 compatibility (defense in depth)
        # Introspection functions
        "globals",
        "locals",
        "vars",
        "dir",
        # Attribute manipulation
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        # Special attributes - class/type introspection
        "__builtins__",
        "__class__",
        "__bases__",
        "__mro__",
        "__subclasses__",
        # Special attributes - object internals
        "__dict__",
        "__globals__",
        "__code__",
        "__func__",
        "__self__",
        "__closure__",
        "__annotations__",
        "__kwdefaults__",
        "__defaults__",
        # Module-level special attributes
        "__loader__",
        "__spec__",
        "__file__",
        "__name__",
        "__package__",
        "__path__",
        "__cached__",
        "__doc__",
        # Callable special methods
        "__call__",
        "__init__",
        "__new__",
        "__del__",
        # Descriptor protocol
        "__get__",
        "__set__",
        "__delete__",
        # Context managers
        "__enter__",
        "__exit__",
        # Attribute access protocol
        "__getattr__",
        "__setattr__",
        "__delattr__",
        "__getattribute__",
        # String conversion (potential for code injection in some contexts)
        "__repr__",
        "__str__",
        "__format__",
        # Iteration protocol
        "__iter__",
        "__next__",
        # Container protocol
        "__getitem__",
        "__setitem__",
        "__delitem__",
        "__contains__",
        # Rich comparison
        "__eq__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        # Numeric operations (can be exploited in some template engines)
        "__add__",
        "__sub__",
        "__mul__",
        "__truediv__",
        "__floordiv__",
        "__mod__",
        "__pow__",
        # Other potentially dangerous builtins
        "open",
        "input",
        "breakpoint",
        "help",
        "license",
        "credits",
        "copyright",
        "quit",
        "exit",
    }
)


def contains_denied_builtin(field_path: str) -> str | None:
    """
    Check if a field path contains any denied Python built-in or special attribute.

    This function provides defense-in-depth security by checking each segment
    of a dotted field path against the DENIED_BUILTINS set. It complements
    SAFE_FIELD_PATTERN which validates character sets.

    Security Design:
        - Checks EACH segment individually (not just exact match on full path)
        - Handles nested paths like "user.__class__.name" by checking each part
        - Case-sensitive matching (Python identifiers are case-sensitive)
        - Returns the first denied item found for clear error messaging

    Args:
        field_path: The dotted field path to validate (e.g., "user.profile.name").
            Expected to already pass SAFE_FIELD_PATTERN validation.

    Returns:
        The first denied built-in found, or None if the path is safe.

    Examples:
        >>> contains_denied_builtin("user.profile.name")
        None
        >>> contains_denied_builtin("user.__class__")
        "__class__"
        >>> contains_denied_builtin("__import__")
        "__import__"
        >>> contains_denied_builtin("data.eval")
        "eval"
    """
    # Split path into segments and check each one
    segments = field_path.split(".")
    for segment in segments:
        if segment in DENIED_BUILTINS:
            return segment
    return None


# ==============================================================================
# Retry Constants
# ==============================================================================

# Default maximum retry attempts for idempotent operations.
# Can be overridden in ModelEffectRetryConfig.max_attempts.
DEFAULT_MAX_RETRY_ATTEMPTS: int = 3

# Default base delay between retries in milliseconds.
# Exponential backoff is applied: delay = base_delay * 2^attempt
DEFAULT_RETRY_BASE_DELAY_MS: int = 1000

# Jitter factor for retry delays (0.1 = 10% jitter).
# Jitter prevents retry storms when multiple clients retry simultaneously.
DEFAULT_RETRY_JITTER_FACTOR: float = 0.1

# ==============================================================================
# Circuit Breaker Constants
# ==============================================================================

# Default number of consecutive failures before opening circuit.
DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5

# Default number of consecutive successes in HALF_OPEN to close circuit.
DEFAULT_CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = 2

# Default time to wait in OPEN state before entering HALF_OPEN (60 seconds).
DEFAULT_CIRCUIT_BREAKER_TIMEOUT_MS: int = 60000

# ==============================================================================
# Version Validation Constants
# ==============================================================================

# Supported major versions of the effect subcontract schema.
# Used for validating contract compatibility at load time.
SUPPORTED_EFFECT_SUBCONTRACT_MAJOR_VERSIONS: frozenset[int] = frozenset({1})

# Minimum minor version required for the current major version.
# Contracts with lower minor versions may be missing required features.
MIN_EFFECT_SUBCONTRACT_MINOR_VERSION: int = 0
