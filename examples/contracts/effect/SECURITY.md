# Security Considerations for Effect Contracts

This document outlines security considerations when using effect contracts in the ONEX framework.

## Table of Contents

1. [Template Resolution Security](#template-resolution-security)
2. [PII and Sensitive Data](#pii-and-sensitive-data)
3. [SQL Injection Prevention](#sql-injection-prevention)
4. [Observability Security](#observability-security)
5. [Production Checklist](#production-checklist)

---

## Template Resolution Security

Effect contracts use template placeholders (`${...}`) for dynamic value substitution at runtime.

### Supported Template Patterns

- **`${input.field}`** - Extract from `operation_data` dictionary
  - Example: `${input.email}`, `${input.user_id}`
  - Source: User input or API request data

- **`${env.VAR}`** - Extract from environment variables
  - Example: `${env.DATABASE_URL}`, `${env.API_VERSION}`
  - Source: System environment variables

- **`${secret.KEY}`** - Extract from secret management service
  - Example: `${secret.API_TOKEN}`, `${secret.DATABASE_PASSWORD}`
  - Source: Secrets vault (e.g., HashiCorp Vault, AWS Secrets Manager)

- **`${previous.operation.field}`** - Extract from previous operation results
  - Example: `${previous.create_user.user_id}`
  - Source: Result data from earlier operations in the same workflow

### Security Considerations

#### 1. Input Validation

**Risk**: Template values come from `input_data.operation_data` which may contain untrusted user input.

**Best Practice**:
- Validate and sanitize all input data at API boundaries before passing to effect operations
- Use Pydantic models for input validation with strict type checking
- Implement allow-lists for string fields (e.g., valid roles, statuses)
- Reject input containing suspicious patterns (e.g., SQL keywords, script tags)

**Example**:
```python
from pydantic import BaseModel, EmailStr, Field

class UserInput(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(admin|developer|viewer)$")

# Validate BEFORE passing to effect operations
validated_input = UserInput(**user_data)
```

#### 2. Nested Access Depth

**Risk**: The current implementation allows arbitrary nested access (e.g., `${input.user.address.city.street.number}`). Deep nesting could potentially be used for traversal attacks or to extract unintended data.

**Current Mitigation**: Input data should be flattened or sanitized at API boundaries to prevent nested object injection.

**Future Enhancement**: Consider implementing a maximum nesting depth limit (e.g., 3 levels) in template resolution.

**Best Practice**:
- Keep input data structures flat when possible
- Avoid passing complex nested objects through templates
- Use explicit field extraction at API boundaries

#### 3. Environment Variables

**Risk**: `${env.VAR}` patterns expose environment variables which may contain sensitive configuration.

**Best Practice**:
- **NEVER** use `${env.VAR}` for secrets like passwords, API tokens, or encryption keys
- **ONLY** use `${env.VAR}` for non-sensitive configuration (e.g., API versions, feature flags, region names)
- **ALWAYS** use `${secret.KEY}` for sensitive credentials
- Implement environment variable allow-lists to restrict which variables can be accessed

**Example**:
```yaml
# ✅ SAFE - Non-sensitive configuration
headers:
  X-API-Version: "${env.API_VERSION}"
  X-Region: "${env.AWS_REGION}"

# ❌ UNSAFE - Sensitive credentials
headers:
  Authorization: "Bearer ${env.API_SECRET_TOKEN}"  # Use ${secret.API_TOKEN} instead!
```

#### 4. Secret Management

**Best Practice**:
- Use `${secret.KEY}` for all sensitive credentials
- Integrate with enterprise secret management systems (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- Rotate secrets regularly
- Audit secret access through observability systems
- Never hardcode secrets in YAML contracts

---

## PII and Sensitive Data

### Data Protection Requirements

The example contracts include realistic field names that demonstrate proper handling of Personally Identifiable Information (PII). When implementing production systems, you **MUST** comply with applicable regulations.

### Regulatory Compliance

| Regulation | Scope | Key Requirements |
|------------|-------|------------------|
| **GDPR** | EU residents | Right to access, erasure, portability; data minimization; consent management |
| **CCPA** | California residents | Right to know, delete, opt-out; notice requirements |
| **PCI-DSS** | Payment card data | Encryption, tokenization, access controls, audit logging |
| **HIPAA** | Healthcare data (US) | Encryption, access controls, audit trails, breach notification |

### Example PII Fields in Contracts

The example contracts demonstrate handling of various PII types:

**User Identity** (`db_query.yaml`, `http_api_call.yaml`):
- `email` - Email addresses (personal identifier)
- `display_name` - User display names (personal information)
- `password_hash` - Password hashes (authentication credential)

**Authentication & Authorization** (`http_api_call.yaml`, `resilient_effect.yaml`):
- `auth_token` - Authentication tokens (authorization credential)
- `idempotency_key` - Deduplication keys (may correlate to users)

**Payment Information** (`resilient_effect.yaml`):
- `payment_method_token` - Tokenized payment methods (PCI-DSS sensitive)
- `customer_email` - Customer contact information (PII)
- `transaction_id` - Payment transaction identifiers (financial data)

**Activity & Tracking** (`kafka_produce.yaml`):
- `ip_address` - Client IP addresses (GDPR personal data)
- `user_agent` - Browser fingerprints (tracking data)
- `session_id` - Session identifiers (tracking data)

### PII Handling Best Practices

#### 1. Data Minimization
Collect and process only the minimum PII necessary for your use case.

```yaml
# ❌ Over-collection
query_params:
  - "${input.email}"
  - "${input.phone}"
  - "${input.address}"
  - "${input.social_security_number}"  # Excessive!

# ✅ Minimal collection
query_params:
  - "${input.email}"  # Only what's needed
```

#### 2. Logging Restrictions

**NEVER** log PII fields in observability outputs.

```yaml
observability:
  log_parameters: false      # ✅ Prevents logging query parameters
  log_response_body: false   # ✅ Prevents logging response data
  log_message_body: false    # ✅ Prevents logging Kafka message bodies
```

#### 3. Encryption Requirements

- **In Transit**: Always use TLS/SSL for external connections
  ```yaml
  io_config:
    verify_ssl: true  # ✅ Enforce SSL/TLS verification
  ```

- **At Rest**: Encrypt databases and message queues containing PII
  - Database: Enable transparent data encryption (TDE)
  - Kafka: Enable broker-side encryption
  - Storage: Use encrypted volumes (e.g., LUKS, AWS EBS encryption)

#### 4. Access Controls

Implement strict access controls for PII:
- Use role-based access control (RBAC) for database connections
- Restrict Kafka topic access with ACLs
- Implement audit logging for all PII access
- Use least-privilege principle for service accounts

#### 5. Data Retention

Define and enforce retention policies:

```yaml
# Example Kafka topic retention configuration (not part of effect contract)
# Configure at topic level:
# - retention.ms: 2592000000  # 30 days for activity logs
# - retention.ms: 315360000000  # 10 years for audit logs
```

---

## SQL Injection Prevention

### Parameterized Queries (Required)

**ALWAYS** use parameterized queries with positional placeholders (`$1`, `$2`, ...) for SQL operations.

### Safe Pattern (Parameterized)

```yaml
io_config:
  query_template: |
    SELECT * FROM users
    WHERE email = $1
      AND status = $2

  query_params:
    - "${input.email}"      # ✅ Safe - bound to $1
    - "${input.status}"     # ✅ Safe - bound to $2
```

### Unsafe Pattern (String Interpolation)

```yaml
# ❌ NEVER DO THIS - SQL Injection vulnerability!
io_config:
  query_template: |
    SELECT * FROM users
    WHERE email = '${input.email}'
      AND status = '${input.status}'
```

**Why This is Dangerous**:
If `input.email = "' OR '1'='1"`, the query becomes:
```sql
SELECT * FROM users WHERE email = '' OR '1'='1' AND status = 'active'
```
This would return ALL users, bypassing authentication!

### Validation in ModelDbIOConfig

The framework validates database contracts to prevent SQL injection:

```python
# src/omnibase_core/models/io/model_db_io_config.py
@model_validator(mode="after")
def validate_no_sql_injection_risk(self) -> "ModelDbIOConfig":
    """Prevent SQL injection by ensuring query_template uses $N placeholders."""
    if "${input." in self.query_template:
        raise ValueError(
            "SQL injection risk: query_template contains ${input.*} placeholder. "
            "Use parameterized queries with $1, $2, ... instead."
        )
    return self
```

### Best Practices

1. **Always use parameterized queries** for user input
2. **Never concatenate** user input into SQL strings
3. **Validate input types** before passing to database
4. **Use ORM libraries** when possible (e.g., SQLAlchemy) for additional safety
5. **Audit all SQL queries** during code review

---

## Observability Security

### Logging Configuration

Each example contract configures observability settings to prevent sensitive data leakage.

#### Safe Logging Patterns

```yaml
observability:
  # ✅ Log operation metadata (safe)
  log_queries: true
  log_requests: true
  log_messages: true

  # ❌ DO NOT log sensitive data
  log_parameters: false       # Query parameters may contain PII
  log_response_body: false    # Response may contain sensitive data
  log_message_body: false     # Kafka messages may contain PII

  # ✅ Emit metrics with generic labels
  emit_metrics: true
  metric_labels:
    operation: "create_user"    # ✅ Generic operation name
    table: "users"              # ✅ Table name (not sensitive)
    # ❌ NEVER: user_id: "${input.user_id}"  # Would expose PII in metrics!
```

#### Metrics Labels Security

**DO**:
- Use generic operation names (`create_user`, `update_status`)
- Use resource types (`table: users`, `topic: events`)
- Use HTTP status codes (`status_code: 200`)

**DO NOT**:
- Include user identifiers (`user_id`, `customer_id`)
- Include email addresses or names
- Include transaction IDs or correlation IDs (unless anonymized)
- Include any PII or sensitive values

#### Tracing and Correlation

**Safe Correlation IDs**:
```yaml
headers:
  X-Correlation-ID: "${input.correlation_id}"  # ✅ If correlation_id is non-PII UUID
```

**Best Practice**:
- Generate correlation IDs server-side (UUIDs)
- Do NOT use user IDs or emails as correlation IDs
- Implement correlation ID rotation for long-running sessions

### Security Monitoring Events

Example contracts include security-relevant event emissions:

```yaml
observability:
  events:
    on_failure:
      enabled: true
      event_type: "payment.processing.failed"  # ✅ Security monitoring
```

**Best Practice**:
- Emit events for authentication failures
- Emit events for authorization failures
- Emit events for rate limit violations
- Emit events for circuit breaker state changes
- Store security events in tamper-proof audit logs

---

## Production Checklist

Before deploying effect contracts to production, complete this security checklist:

### Input Validation
- [ ] All input data validated with Pydantic models at API boundaries
- [ ] String fields use allow-lists or regex patterns for validation
- [ ] Numeric fields have min/max bounds
- [ ] Input data structures are flattened to prevent nested injection

### Template Security
- [ ] All SQL queries use parameterized queries (`$1`, `$2`, ...)
- [ ] No `${input.*}` placeholders in SQL `query_template` fields
- [ ] Environment variables (`${env.VAR}`) used only for non-sensitive config
- [ ] Secrets use `${secret.KEY}` with proper secret management integration
- [ ] Template placeholders validated against allow-list

### PII & Compliance
- [ ] PII fields identified and documented
- [ ] Data retention policies defined and configured
- [ ] Encryption enabled for data in transit (TLS/SSL)
- [ ] Encryption enabled for data at rest (database TDE, encrypted volumes)
- [ ] GDPR/CCPA/HIPAA compliance requirements reviewed
- [ ] PCI-DSS requirements met for payment data (if applicable)

### Observability Security
- [ ] `log_parameters: false` for operations with sensitive query parameters
- [ ] `log_response_body: false` for operations returning sensitive data
- [ ] `log_message_body: false` for Kafka operations with PII
- [ ] Metric labels do NOT include PII (user IDs, emails, names)
- [ ] Security events configured for monitoring and alerting

### Connection Security
- [ ] All external connections use SSL/TLS (`verify_ssl: true`)
- [ ] Database connections use encrypted transport
- [ ] Kafka connections use SSL/SASL authentication
- [ ] HTTP APIs use HTTPS (not HTTP)

### Resilience & DDoS Protection
- [ ] Circuit breakers configured for external dependencies
- [ ] Rate limiting configured to prevent abuse
- [ ] Timeouts configured at operation and handler levels
- [ ] Retry policies use exponential backoff with jitter
- [ ] Maximum retry attempts limited (e.g., 3-6 attempts)

### Access Controls
- [ ] Database connections use least-privilege service accounts
- [ ] Kafka topics have ACLs restricting producer/consumer access
- [ ] API tokens rotated regularly
- [ ] Secret rotation policies implemented

### Audit & Compliance
- [ ] Audit logging enabled for all PII access
- [ ] Audit logs stored in tamper-proof storage (append-only)
- [ ] Retention policies comply with regulatory requirements
- [ ] Breach notification procedures documented
- [ ] Data processing agreements (DPAs) in place with third parties

### Code Review
- [ ] Security review completed by security team
- [ ] SQL queries audited for injection vulnerabilities
- [ ] Template placeholders reviewed for injection risks
- [ ] Third-party dependencies scanned for vulnerabilities
- [ ] SAST/DAST tools run against codebase

---

## Additional Resources

### ONEX Framework Documentation
- [Effect Node Guide](https://docs.onex.ai/nodes/effect)
- [Contract Schema Reference](https://docs.onex.ai/contracts/schema)
- [Security Best Practices](https://docs.onex.ai/security/best-practices)

### Regulatory Compliance
- [GDPR Official Text](https://gdpr-info.eu/)
- [CCPA Overview](https://oag.ca.gov/privacy/ccpa)
- [PCI-DSS Requirements](https://www.pcisecuritystandards.org/)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/)

### Security Standards
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated**: 2025-12-08
**Document Version**: 1.0.0
**Correlation ID**: `d3c7b1a2-8f45-4e29-a6d9-5e2c9b3f1d8a`
