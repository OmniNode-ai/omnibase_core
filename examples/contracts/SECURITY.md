# Security Considerations for Example Contracts

**Version**: 1.0.0
**Last Updated**: 2025-12-08

This document provides comprehensive security guidance for developers implementing ONEX contracts based on these examples. The example contracts in this directory are designed for demonstration purposes and contain patterns that require careful security consideration before production use.

---

## Table of Contents

1. [PII Warning](#pii-warning)
2. [Template Security](#template-security)
3. [Example Data Protection](#example-data-protection)
4. [Authentication and Authorization](#authentication-and-authorization)
5. [Logging and Observability](#logging-and-observability)
6. [Best Practices Summary](#best-practices-summary)
7. [Secret Resolution Mechanism](#secret-resolution-mechanism)

---

## PII Warning

### Personally Identifiable Information in Examples

The example contracts in this directory contain fields that represent Personally Identifiable Information (PII) for demonstration purposes only. These include:

| Field | Contract(s) | Risk Level |
|-------|-------------|------------|
| `email` | user_profile_normalizer, http_api_call, db_query, kafka_produce | High |
| `user_id` | All contracts | Medium |
| `display_name` | user_profile_normalizer, http_api_call, db_query | Medium |
| `phone` | user_profile_normalizer | High |
| `ip_address` | kafka_produce, resilient_effect | Medium |
| `user_agent` | kafka_produce, resilient_effect | Low |
| `password_hash` | db_query | Critical |
| `customer_email` | resilient_effect | High |
| `payment_method_token` | resilient_effect | Critical |
| `auth_token` | http_api_call | Critical |

### Production Recommendations

**DO NOT use real PII in example or test data.** When adapting these contracts for production:

1. **Replace example data with anonymized placeholders**:
   ```yaml
   # INSECURE - Example with real-looking data
   email: "john.smith@example.com"

   # SECURE - Use obvious placeholder data
   email: "user_${input.user_id}@placeholder.test"
   ```

2. **Use synthetic data generators** for testing that produce obviously fake data:
   - Use domains like `@example.com`, `@test.invalid`, or `@placeholder.local`
   - Use names like "Test User 001" rather than realistic names
   - Use clearly fake phone numbers (555-xxx-xxxx in US format)

3. **Implement data classification** to identify and protect sensitive fields:
   ```yaml
   # Add metadata to track sensitive fields
   field_classifications:
     email: PII
     phone: PII
     password_hash: SECRET
     auth_token: SECRET
   ```

### Regulatory Compliance

When handling PII, ensure compliance with applicable regulations:

- **GDPR** (EU): Right to access, rectification, erasure; data minimization
- **CCPA** (California): Consumer rights to know, delete, opt-out
- **HIPAA** (US Healthcare): Protected health information requirements
- **PCI-DSS** (Payment): Card data handling requirements

---

## Template Security

### Template Variable Injection Risks

The example contracts use `${input.field_name}` template syntax for variable substitution. This pattern carries security risks if not properly validated.

#### The Risk

Template variables allow arbitrary field access from input data. Without proper validation, malicious input could:

1. **Access unintended nested fields**: Deep nesting could expose internal state
2. **Cause resource exhaustion**: Deeply nested paths consume processing resources
3. **Leak sensitive information**: Arbitrary paths might access protected data

#### Secure Template Patterns

#### 1. Limit Field Extraction Depth

The `_extract_field()` function should enforce a maximum depth limit:

```python
# RECOMMENDED: Maximum depth of 5 levels
MAX_FIELD_DEPTH = 5

def _extract_field(data: dict, path: str) -> Any:
    """Extract field with depth limiting."""
    parts = path.split('.')
    if len(parts) > MAX_FIELD_DEPTH:
        raise ValueError(f"Field path exceeds maximum depth of {MAX_FIELD_DEPTH}")
    # ... extraction logic
```

#### 2. Whitelist Allowed Fields

Define explicit allowed fields in contracts rather than allowing arbitrary access:

```yaml
# INSECURE - Allows any field access
body_template: |
  {
    "data": "${input.arbitrary_field}"
  }

# SECURE - Explicit field whitelist in contract
allowed_input_fields:
  - email
  - display_name
  - role

body_template: |
  {
    "email": "${input.email}",
    "display_name": "${input.display_name}",
    "role": "${input.role}"
  }
```

#### 3. Validate Field Names

Reject field names with suspicious patterns:

```python
import re

SAFE_FIELD_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

def validate_field_name(field_name: str) -> bool:
    """Validate field name contains only safe characters."""
    return bool(SAFE_FIELD_PATTERN.match(field_name))
```

#### 4. Sanitize Template Output

For templates generating JSON, HTML, or SQL, sanitize the substituted values:

```python
# For JSON templates
import json

def safe_json_value(value: Any) -> str:
    """Safely encode value for JSON template."""
    return json.dumps(value)[1:-1]  # Remove surrounding quotes

# For URL templates
from urllib.parse import quote

def safe_url_value(value: str) -> str:
    """Safely encode value for URL template."""
    return quote(str(value), safe='')
```

### JSONPath Expression Security

Several contracts use JSONPath expressions for field extraction:

```yaml
extract_fields:
  user_id: "$.metadata.ids.user_id"
```

#### Security Considerations

1. **Validate JSONPath patterns** before execution
2. **Limit result set size** to prevent memory exhaustion
3. **Timeout JSONPath evaluation** for complex expressions
4. **Reject recursive descent** (`..`) operators in untrusted input

```python
# SECURE: Validate JSONPath before execution
DISALLOWED_PATTERNS = ['..', '[*]', '?(']

def validate_jsonpath(path: str) -> bool:
    """Validate JSONPath is safe to execute."""
    return not any(pattern in path for pattern in DISALLOWED_PATTERNS)
```

---

## Example Data Protection

### Handling Sensitive Data in Examples

When creating or modifying example contracts, follow these guidelines:

#### JWT Tokens and API Keys

```yaml
# INSECURE - Hardcoded token (even if it looks fake, don't do this)
auth_token: "EXAMPLE_TOKEN_DO_NOT_USE_IN_PRODUCTION"

# SECURE - Obviously placeholder token
auth_token: "${input.auth_token}"  # Retrieved from secure storage

# SECURE - Example with placeholder notation
# Example: auth_token: "<YOUR_API_TOKEN_HERE>"
```

#### Password and Secret Storage

```yaml
# INSECURE - Showing hash format
password_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4..."

# SECURE - Reference secure storage
password_hash: "${secrets.password_hash}"  # From secure vault
```

#### Database Connection Strings

Never include real connection strings in examples:

```yaml
# INSECURE
connection_name: "postgres://user:pass@prod-db.internal:5432/users"

# SECURE
connection_name: "user_db_pool"  # Resolved from connection configuration
```

### Recommended Placeholder Patterns

| Data Type | Placeholder Pattern | Example |
|-----------|---------------------|---------|
| Email | `user_${id}@placeholder.test` | `user_123@placeholder.test` |
| Phone | `+1-555-000-${id}` | `+1-555-000-0001` |
| UUID | `00000000-0000-0000-0000-${id}` | `00000000-0000-0000-0000-000000000001` |
| IP Address | `192.0.2.${id}` (TEST-NET-1) | `192.0.2.1` |
| API Token | `<TOKEN_FROM_ENV>` | N/A |
| Credit Card | `4111111111111111` (Test card) | N/A |

---

## Authentication and Authorization

### Token Handling in Contracts

The example contracts show authentication patterns that require secure implementation:

```yaml
headers:
  Authorization: "Bearer ${input.auth_token}"
```

#### Production Requirements

1. **Never log authentication tokens**:
   ```yaml
   observability:
     log_requests: true
     log_response_body: false  # May contain tokens
     # Explicitly mask sensitive headers
     masked_headers:
       - Authorization
       - X-API-Key
   ```

2. **Use short-lived tokens** with automatic refresh
3. **Validate token scope** before operation execution
4. **Implement token revocation** checking

### Idempotency Key Security

Several contracts use idempotency keys:

```yaml
headers:
  X-Idempotency-Key: "${input.idempotency_key}"
```

#### Security Considerations

1. **Generate cryptographically secure keys**:
   ```python
   import secrets
   idempotency_key = secrets.token_urlsafe(32)
   ```

2. **Bind keys to user/session** to prevent replay across contexts
3. **Expire idempotency keys** after reasonable time (24-72 hours)
4. **Store key usage** to prevent reuse attacks

---

## Logging and Observability

### Never Log Sensitive Data

The example contracts include observability configuration. In production:

```yaml
observability:
  log_requests: true
  log_responses: true
  log_response_body: false  # CRITICAL: May contain sensitive data
  log_parameters: false     # CRITICAL: May contain PII or secrets
```

### Sensitive Field Masking

Implement automatic masking for sensitive fields in logs:

```python
SENSITIVE_FIELDS = {
    'password', 'password_hash', 'secret', 'token',
    'auth_token', 'api_key', 'credit_card', 'ssn',
    'email', 'phone', 'ip_address'
}

def mask_sensitive_fields(data: dict) -> dict:
    """Mask sensitive fields in data for logging."""
    masked = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
            masked[key] = '***MASKED***'
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_fields(value)
        else:
            masked[key] = value
    return masked
```

### Correlation ID Security

The examples use correlation IDs for tracing:

```yaml
headers:
  X-Correlation-ID: "${input.correlation_id}"
```

#### Security Considerations

1. **Generate correlation IDs server-side** - don't trust client-provided IDs
2. **Validate correlation ID format** to prevent injection
3. **Don't include sensitive data** in correlation IDs

---

## Best Practices Summary

### Input Validation Requirements

1. **Validate all input data** before template substitution
2. **Enforce type constraints** on input fields
3. **Limit string lengths** to prevent buffer issues
4. **Sanitize special characters** for target format (JSON, SQL, URL)

### Output Sanitization

1. **Escape output** appropriately for target system
2. **Validate response schemas** before processing
3. **Limit response sizes** to prevent memory exhaustion
4. **Timeout external calls** to prevent hanging

### Secure vs Insecure Patterns

| Pattern | Insecure | Secure |
|---------|----------|--------|
| Field access | Arbitrary path traversal | Whitelisted fields only |
| Template depth | Unlimited nesting | Max 5 levels |
| Token logging | Log full requests | Mask Authorization header |
| Example data | Realistic PII | Obvious placeholders |
| Secrets | Inline in YAML | Environment/vault reference |
| Connection strings | Full URL in config | Named connection pool |

### Security Checklist

Before deploying contracts to production:

- [ ] All PII fields use anonymized placeholder data
- [ ] Authentication tokens reference secure storage (not inline)
- [ ] Template variables use whitelisted field access
- [ ] Logging configuration masks sensitive fields
- [ ] JSONPath expressions are validated and depth-limited
- [ ] Idempotency keys are cryptographically generated
- [ ] Connection strings use named pools (not inline credentials)
- [ ] Timeout values are configured for all external calls
- [ ] Response validation is enabled for external APIs
- [ ] Circuit breakers are configured for fault tolerance

---

## Secret Resolution Mechanism

### Overview

ONEX contracts support a **secret resolution mechanism** that allows sensitive values (API keys, tokens, credentials) to be referenced in YAML contracts without hardcoding them. This mechanism ensures secrets are resolved at runtime from secure storage backends.

### Secret Reference Syntax

Secrets are referenced using the `${secrets.<key>}` template syntax:

```yaml
# Reference a secret by key
headers:
  Authorization: "Bearer ${secrets.api_token}"
  X-API-Key: "${secrets.external_api_key}"

# Database credentials
io_config:
  handler_type: db
  connection_name: "user_db"
  credentials:
    username: "${secrets.db_username}"
    password: "${secrets.db_password}"
```

### Resolution Flow

The secret resolution follows this flow:

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  YAML Contract  │────▶│  Template Engine │────▶│  Secret Backend │
│  ${secrets.key} │     │  _resolve_secret │     │  (Vault/Env/KMS)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Resolved Value  │
                        │  (in memory only)│
                        └──────────────────┘
```

1. **Parse**: Template engine identifies `${secrets.*}` patterns
2. **Resolve**: Secret backend is queried for the value
3. **Inject**: Value is substituted in memory (never persisted)
4. **Clear**: Value is cleared from memory after use

### Supported Secret Backends

#### 1. Environment Variables (Default)

The simplest backend, suitable for development and containerized deployments:

```python
# Resolution: ${secrets.api_key} → os.environ.get("ONEX_SECRET_API_KEY")
# Prefix: ONEX_SECRET_ is prepended to the key name (uppercase)
```

Configuration:
```yaml
secret_backend:
  type: environment
  prefix: "ONEX_SECRET_"  # Optional, default: "ONEX_SECRET_"
```

#### 2. HashiCorp Vault (Production)

For production deployments with centralized secret management:

```yaml
secret_backend:
  type: vault
  address: "https://vault.internal:8200"
  auth_method: kubernetes  # or token, approle, aws
  mount_path: "secret"
  secret_path: "onex/effects"
  # Token/credentials resolved from environment or mounted files
```

Resolution: `${secrets.api_key}` → `vault.read("secret/onex/effects").data["api_key"]`

#### 3. AWS Secrets Manager

For AWS-native deployments:

```yaml
secret_backend:
  type: aws_secrets_manager
  region: "us-east-1"
  secret_name: "onex/effect-secrets"
  # AWS credentials from instance profile, environment, or config
```

#### 4. Kubernetes Secrets

For Kubernetes deployments using mounted secrets:

```yaml
secret_backend:
  type: kubernetes
  secret_mount_path: "/var/run/secrets/onex"
  # Secrets mounted as files: /var/run/secrets/onex/<key>
```

### Implementation Pattern

To implement secret resolution in an effect handler:

```python
from omnibase_core.protocols.protocol_secret_resolver import ProtocolSecretResolver

class MyEffectHandler:
    def __init__(self, secret_resolver: ProtocolSecretResolver):
        self._secret_resolver = secret_resolver

    async def execute(self, operation_data: dict) -> dict:
        # Resolve secrets before use
        api_key = await self._secret_resolver.resolve("api_key")

        # Use the secret
        response = await self._call_api(api_key=api_key)

        # Secret is not stored, logged, or returned
        return {"status": "success", "data": response}
```

### Security Requirements

#### 1. Never Log Secrets

```python
# INSECURE - logs the resolved secret
logger.info(f"Using API key: {api_key}")

# SECURE - log only that resolution occurred
logger.debug("Resolved secret: api_key (length=%d)", len(api_key))
```

#### 2. Never Return Secrets in Responses

```python
# INSECURE - secret in response
return {"api_key": api_key, "result": data}

# SECURE - only return operation results
return {"result": data}
```

#### 3. Clear Secrets After Use

**Important Security Note**: Python's memory management (string interning, garbage collection) makes reliable secret clearing extremely difficult. The example below is provided for awareness but **should NOT be relied upon** in production. For truly sensitive secrets, consider:

- Using `bytearray` instead of `str` (mutable, can be zeroed)
- Dedicated secret handling libraries (e.g., `SecretStr` from Pydantic)
- Short-lived process isolation for secret operations
- Hardware security modules (HSMs) for critical secrets

```python
# WARNING: This technique is NOT reliable in Python due to string interning
# and memory management. Use bytearray or dedicated secret handling instead.
from typing import Union

def secure_clear_bytearray(secret: bytearray) -> None:
    """Clear a bytearray secret (more reliable than str)."""
    for i in range(len(secret)):
        secret[i] = 0

# Better approach: Use Pydantic's SecretStr
from pydantic import SecretStr

class SecureConfig:
    api_key: SecretStr  # Automatically masked in logs/repr
```

#### 4. Validate Secret Names

```python
import re

SAFE_SECRET_NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')

def validate_secret_name(name: str) -> bool:
    """Validate secret name follows safe pattern."""
    return bool(SAFE_SECRET_NAME.match(name))
```

### Error Handling

Secret resolution errors should be handled gracefully without exposing details:

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums import EnumCoreErrorCode

try:
    secret = await resolver.resolve("api_key")
except SecretNotFoundError:
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
        message="Required secret not configured",
        # DO NOT include secret name in user-facing error
        context={"hint": "Check secret backend configuration"}
    )
except SecretAccessDeniedError:
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.AUTHORIZATION_ERROR,
        message="Secret access denied",
        context={"hint": "Check secret backend permissions"}
    )
```

### Audit and Compliance

Secret access should be auditable:

```yaml
secret_backend:
  type: vault
  audit:
    enabled: true
    log_access: true      # Log when secrets are accessed
    log_resolution: false  # Don't log resolved values
    include_requester: true  # Include node_id in audit log
```

Audit log format:
```json
{
  "timestamp": "2025-12-09T17:00:00Z",
  "event": "secret_access",
  "secret_name": "api_key",
  "node_id": "effect-user-api-123",
  "correlation_id": "abc-123",
  "result": "success"
}
```

### Migration from Inline Secrets

To migrate from inline secrets to the resolution mechanism:

```yaml
# BEFORE (insecure - inline secret)
# NOTE: This is an obviously fake example token - NEVER use real tokens in code!
headers:
  Authorization: "Bearer EXAMPLE_TOKEN_DO_NOT_USE_IN_PRODUCTION"

# AFTER (secure - secret reference)
headers:
  Authorization: "Bearer ${secrets.stripe_api_key}"
```

Migration steps:
1. Identify all inline secrets in contracts
2. Add secrets to your backend (Vault, AWS, etc.)
3. Replace inline values with `${secrets.<key>}` references
4. Test resolution in staging environment
5. Deploy updated contracts

---

## Reporting Security Issues

If you discover a security vulnerability in these examples or the ONEX framework:

1. **Do not** open a public issue
2. Contact the security team at [security@onex.ai](mailto:security@onex.ai)
3. Include detailed reproduction steps
4. Allow 90 days for remediation before disclosure

---

## References

- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [CWE-94: Code Injection](https://cwe.mitre.org/data/definitions/94.html)
- [PCI-DSS Requirements](https://www.pcisecuritystandards.org/)
- [GDPR Compliance](https://gdpr.eu/)
