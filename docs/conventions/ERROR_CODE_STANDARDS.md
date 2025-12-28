# ONEX Error Code Standards

This document defines the naming conventions and format requirements for error codes used throughout the ONEX system.

---

## Table of Contents

1. [Error Code Format](#error-code-format)
2. [Format Specification](#format-specification)
3. [Valid Examples](#valid-examples)
4. [Invalid Examples](#invalid-examples)
5. [Standard Categories](#standard-categories)
6. [Implementation Reference](#implementation-reference)
7. [Best Practices](#best-practices)

---

## Error Code Format

All ONEX error codes **MUST** follow the `CATEGORY_NNN` format pattern.

### Pattern Overview

```text
CATEGORY_NNN
```

**Components:**
- `CATEGORY` - Uppercase identifier describing the error domain
- `_` - Single underscore separator
- `NNN` - Numeric identifier (1-4 digits)

### Examples

```text
AUTH_001          # Authentication error
VALIDATION_123    # Validation error
SYSTEM_01         # System error
CONFIG_PARSE_0001 # Configuration parsing error
```

---

## Format Specification

### Regex Pattern

The error code format is enforced by the following regex pattern:

```regex
^[A-Z][A-Z0-9_]*_\d{1,4}$
```

### Pattern Breakdown

| Component | Pattern | Description |
|-----------|---------|-------------|
| **Start** | `^` | Beginning of string |
| **First character** | `[A-Z]` | Must start with uppercase letter |
| **Category body** | `[A-Z0-9_]*` | Uppercase letters, digits, underscores |
| **Separator** | `_` | Underscore between category and number |
| **Number** | `\d{1,4}` | 1 to 4 digits |
| **End** | `$` | End of string |

### Rules

1. **Category must start with uppercase letter**: The first character must be A-Z
2. **Category allows uppercase, digits, underscores**: After the first character, the category can contain uppercase letters, digits (0-9), and underscores
3. **Underscore separator required**: A single underscore separates the category from the numeric identifier
4. **Numeric suffix (1-4 digits)**: The error number must be 1 to 4 digits (0-9999)
5. **No lowercase letters**: The entire code must be uppercase (except digits)
6. **No leading zeros required**: Numbers can be `1`, `01`, `001`, or `0001`

---

## Valid Examples

| Error Code | Category | Number | Use Case |
|------------|----------|--------|----------|
| `AUTH_001` | `AUTH` | `001` | Authentication failure |
| `AUTH_1` | `AUTH` | `1` | Short form (valid but 3-digit preferred) |
| `VALIDATION_123` | `VALIDATION` | `123` | Input validation error |
| `SYSTEM_01` | `SYSTEM` | `01` | System-level error |
| `CONFIG_PARSE_0001` | `CONFIG_PARSE` | `0001` | Configuration parsing error |
| `DB_CONNECTION_42` | `DB_CONNECTION` | `42` | Database connection error |
| `HTTP2_500` | `HTTP2` | `500` | HTTP/2 server error |
| `ONEX_001` | `ONEX` | `001` | ONEX framework error |
| `FSM_TRANSITION_99` | `FSM_TRANSITION` | `99` | FSM state transition error |
| `IO_1234` | `IO` | `1234` | I/O operation error |

---

## Invalid Examples

| Invalid Code | Issue | Corrected |
|--------------|-------|-----------|
| `auth_001` | Lowercase not allowed | `AUTH_001` |
| `Auth_001` | Mixed case not allowed | `AUTH_001` |
| `AUTH-001` | Hyphen not allowed (use underscore) | `AUTH_001` |
| `AUTH001` | Missing underscore separator | `AUTH_001` |
| `AUTH_12345` | Number exceeds 4 digits | `AUTH_1234` |
| `_AUTH_001` | Cannot start with underscore | `AUTH_001` |
| `123_001` | Cannot start with digit | `ERR_123_001` |
| `AUTH_` | Missing numeric suffix | `AUTH_001` |
| `AUTH_-1` | Negative numbers not allowed | `AUTH_001` |
| `AUTH_1.0` | Decimal not allowed | `AUTH_010` |
| `` (empty) | Empty string not allowed | `UNKNOWN_001` |

---

## Standard Categories

### Recommended Category Prefixes

| Category | Purpose | Example Codes |
|----------|---------|---------------|
| `AUTH` | Authentication and authorization | `AUTH_001`, `AUTH_002` |
| `VALIDATION` | Input/data validation | `VALIDATION_001`, `VALIDATION_100` |
| `SYSTEM` | System-level errors | `SYSTEM_001`, `SYSTEM_500` |
| `NETWORK` | Network and connectivity | `NETWORK_001`, `NETWORK_408` |
| `CONFIG` | Configuration errors | `CONFIG_001`, `CONFIG_PARSE_001` |
| `CONTRACT` | Contract validation | `CONTRACT_001`, `CONTRACT_SCHEMA_001` |
| `NODE` | Node operation errors | `NODE_001`, `NODE_COMPUTE_001` |
| `FSM` | Finite state machine errors | `FSM_001`, `FSM_TRANSITION_001` |
| `ROUTING` | Routing and dispatch | `ROUTING_001`, `ROUTING_404` |
| `CACHE` | Caching errors | `CACHE_001`, `CACHE_MISS_001` |
| `DB` | Database operations | `DB_001`, `DB_CONNECTION_001` |
| `IO` | I/O operations | `IO_001`, `IO_READ_001` |
| `TIMEOUT` | Timeout errors | `TIMEOUT_001`, `TIMEOUT_408` |
| `INTERNAL` | Internal/unexpected errors | `INTERNAL_001`, `INTERNAL_500` |

### Compound Categories

Compound categories use underscores to create hierarchical namespaces:

```text
CONFIG_PARSE_001      # Configuration parsing subcategory
DB_CONNECTION_001     # Database connection subcategory
FSM_TRANSITION_001    # FSM transition subcategory
NODE_COMPUTE_001      # Node compute subcategory
```

---

## Implementation Reference

### ModelErrorMetadata Validation

The `CATEGORY_NNN` pattern is enforced by `ModelErrorMetadata` in the ONEX framework.

**Location**: `src/omnibase_core/models/context/model_error_metadata.py`

**Pattern Definition**:
```python
# Pattern for error codes: CATEGORY_NNN (e.g., AUTH_001, VALIDATION_123)
ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_\d{1,4}$")
```

**Validation**:
```python
@field_validator("error_code", mode="before")
@classmethod
def validate_error_code_format(cls, value: str | None) -> str | None:
    """Validate error_code follows CATEGORY_NNN pattern if provided."""
    if value is None:
        return None
    if not ERROR_CODE_PATTERN.match(value):
        raise ValueError(
            f"Invalid error_code format '{value}': expected CATEGORY_NNN "
            f"pattern (e.g., AUTH_001, VALIDATION_123)"
        )
    return value
```

### Usage Example

```python
from omnibase_core.models.context import ModelErrorMetadata

# Valid error context
error_ctx = ModelErrorMetadata(
    error_code="AUTH_001",
    error_category="auth",
    correlation_id="req_abc123",
    retry_count=0,
    is_retryable=True,
)

# Invalid - will raise ValueError
try:
    invalid_ctx = ModelErrorMetadata(
        error_code="auth_001",  # Lowercase not allowed
    )
except ValueError as e:
    print(e)  # "Invalid error_code format 'auth_001': expected CATEGORY_NNN..."
```

---

## Best Practices

### 1. Use Consistent Numbering

Prefer zero-padded 3-digit numbers for readability:

```python
# Preferred
"AUTH_001", "AUTH_002", "AUTH_010", "AUTH_100"

# Acceptable but less readable
"AUTH_1", "AUTH_2", "AUTH_10", "AUTH_100"
```

### 2. Group Related Errors

Use number ranges to group related errors:

```text
AUTH_001 - AUTH_099    # Authentication errors
AUTH_100 - AUTH_199    # Authorization errors
AUTH_200 - AUTH_299    # Token errors
```

### 3. Document Error Codes

Maintain a registry of error codes with descriptions:

```python
ERROR_REGISTRY = {
    "AUTH_001": "Invalid credentials provided",
    "AUTH_002": "Account locked due to failed attempts",
    "AUTH_100": "Insufficient permissions for operation",
    "VALIDATION_001": "Required field missing",
    "VALIDATION_002": "Invalid field format",
}
```

### 4. Use Meaningful Categories

Choose category names that clearly identify the error domain:

```python
# Good - specific and meaningful
"DB_CONNECTION_001"  # Database connection error
"CONFIG_PARSE_001"   # Configuration parsing error

# Avoid - too generic
"ERROR_001"          # What kind of error?
"FAIL_001"           # Not descriptive
```

### 5. Reserve Number Ranges

Reserve specific numbers for standard error types:

| Range | Meaning |
|-------|---------|
| `001-099` | Initialization/setup errors |
| `100-199` | Input/validation errors |
| `200-299` | Processing errors |
| `300-399` | External service errors |
| `400-499` | Client errors (HTTP-like) |
| `500-599` | Server/internal errors |

---

## Related Documentation

- **Error Handling Best Practices**: `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`
- **ModelOnexError**: Error base class and structured error context
- **Naming Conventions**: `docs/conventions/NAMING_CONVENTIONS.md`
- **Pydantic Best Practices**: `docs/conventions/PYDANTIC_BEST_PRACTICES.md`

---

**Last Updated**: 2025-12-26
**Project**: omnibase_core v0.4.0
