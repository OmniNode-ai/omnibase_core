# ONEX Scripts Reference

**Version**: 0.4.0
**Scope**: Development scripts for contract management, validation, and code quality

---

## Table of Contents

1. [Overview](#overview)
2. [Contract Fingerprint Management](#contract-fingerprint-management)
3. [Contract Linting](#contract-linting)
4. [Validation Scripts](#validation-scripts)
5. [Utility Scripts](#utility-scripts)
6. [v1.1.0 Contract Field Reference](#v110-contract-field-reference)
7. [Security Considerations](#security-considerations)

---

## Overview

This directory contains development and CI/CD scripts for the ONEX framework:

| Script | Purpose | Usage |
|--------|---------|-------|
| `compute_contract_fingerprint.py` | Compute/validate contract fingerprints | `poetry run python scripts/compute_contract_fingerprint.py <contract.yaml>` |
| `lint_contract.py` | Lint YAML contracts for correctness | `poetry run python scripts/lint_contract.py <contract.yaml>` |
| `cleanup.py` | Clean temporary files and caches | `poetry run python scripts/cleanup.py --tmp-only` |
| `check_node_purity.py` | Verify node implementation purity | `poetry run python scripts/check_node_purity.py` |
| `check_protocol_exports.py` | Validate protocol exports | `poetry run python scripts/check_protocol_exports.py` |
| `check_transport_imports.py` | Check transport layer imports | `poetry run python scripts/check_transport_imports.py` |
| `fix_dict_any_violations.py` | Fix dict[str, Any] anti-patterns | `poetry run python scripts/fix_dict_any_violations.py` |

---

## Contract Fingerprint Management

### Overview

Contract fingerprints enable drift detection between YAML contracts and their generated code.
The fingerprint is a combination of the contract version and a truncated SHA256 hash.

**Format**: `v<semver>:<12-hex-chars>`
**Example**: `v1.1.0:8fa1e2b4c9d1`

### Compute a Fingerprint

```bash
# Compute fingerprint for a single contract
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/runtime_orchestrator.yaml

# Compute with verbose output (includes full hash)
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/runtime_orchestrator.yaml --verbose

# Output as JSON (for CI/CD pipelines)
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/runtime_orchestrator.yaml --json

# Process multiple contracts
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/*.yaml
```

### Validate Existing Fingerprints

```bash
# Validate fingerprint in contract matches computed value
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/runtime_orchestrator.yaml --validate

# Returns exit code 0 if valid, 1 if mismatch, 2 on error
```

### Regenerating Fingerprints

When you modify a contract's content, you **MUST** regenerate its fingerprint:

#### Step 1: Compute the New Fingerprint

```bash
poetry run python scripts/compute_contract_fingerprint.py path/to/your_contract.yaml
```

This outputs something like:
```
File: path/to/your_contract.yaml
Fingerprint: v1.1.0:a1b2c3d4e5f6
```

#### Step 2: Update the Contract

Edit the contract YAML and update the `fingerprint` field:

```yaml
# Before
fingerprint: "v1.1.0:oldvalue12ab"

# After
fingerprint: "v1.1.0:a1b2c3d4e5f6"
```

#### Step 3: Validate the Update

```bash
# Confirm fingerprint is now valid
poetry run python scripts/compute_contract_fingerprint.py path/to/your_contract.yaml --validate
```

### Batch Fingerprint Regeneration

For multiple contracts (e.g., after a major refactor):

```bash
# Regenerate all runtime contracts
for f in contracts/runtime/*.yaml; do
    echo "Processing $f"
    poetry run python scripts/compute_contract_fingerprint.py "$f"
done

# Or use --json for scripted updates
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/*.yaml --json > fingerprints.json
```

### CI/CD Integration

```yaml
# Example GitHub Actions workflow step
- name: Validate Contract Fingerprints
  run: |
    for contract in contracts/**/*.yaml; do
      poetry run python scripts/compute_contract_fingerprint.py "$contract" --validate
    done
```

---

## Contract Linting

The contract linter validates YAML contracts against the ONEX schema.

```bash
# Lint a single contract
poetry run python scripts/lint_contract.py contracts/runtime/runtime_orchestrator.yaml

# Lint all contracts in a directory
poetry run python scripts/lint_contract.py contracts/

# Strict mode (treat warnings as errors)
poetry run python scripts/lint_contract.py contracts/ --strict
```

---

## Validation Scripts

Located in `scripts/validation/`, these scripts enforce ONEX conventions:

| Script | Purpose |
|--------|---------|
| `validate-contracts.py` | Validate all contract YAML files |
| `validate-pydantic-patterns.py` | Check Pydantic model patterns |
| `validate-imports.py` | Verify import patterns |
| `validate-typing-syntax.py` | Check typing syntax consistency |
| `validate-onex-error-compliance.py` | Ensure proper error handling |
| `validate-no-dict-methods.py` | Prevent dict method anti-patterns |

Run all validations:

```bash
# Individual validation
poetry run python scripts/validation/validate-contracts.py

# Run all validations via pre-commit
pre-commit run --all-files
```

---

## Utility Scripts

### cleanup.py

Clean temporary files while preserving caches:

```bash
# Clean tmp/ directory only (recommended for regular use)
poetry run python scripts/cleanup.py --tmp-only

# Full cleanup (deletes ALL caches - slow rebuild!)
poetry run python scripts/cleanup.py

# Preview what would be cleaned
poetry run python scripts/cleanup.py --dry-run

# Remove tracked tmp files from git index
poetry run python scripts/cleanup.py --remove-from-git --tmp-only
```

---

## v1.1.0 Contract Field Reference

The v1.1.0 contract specification introduces several new fields for enhanced
contract management and runtime behavior.

### fingerprint

**Purpose**: Drift detection between contract definition and implementation.

**Format**: `"v<major>.<minor>.<patch>:<12-hex-sha256>"`

**Example**:
```yaml
fingerprint: "v1.1.0:8fa1e2b4c9d1"
```

**Regeneration**: Required when any contract content changes.
See [Regenerating Fingerprints](#regenerating-fingerprints).

**Security Note**: The 12-character hash prefix provides 48 bits of entropy.
For collision probability analysis, see [Security Considerations](#security-considerations).

---

### handlers

**Purpose**: Declare handler dependencies for node execution.

**Structure**:
```yaml
handlers:
  required:
    - type: <handler_type>
      version: "<semver_constraint>"
  optional:
    - type: <handler_type>
      version: "<semver_constraint>"
```

**When to Use Required vs Optional Handlers**:

| Handler Category | Use `required` | Use `optional` |
|-----------------|----------------|----------------|
| Core I/O (filesystem, database) | Yes - node cannot function | No |
| Logging/Metrics | No | Yes - graceful degradation |
| External APIs | Depends on criticality | Yes for optional features |
| Caching | No | Yes - performance enhancement |

**Examples**:

```yaml
# EFFECT node with filesystem operations (required handler)
handlers:
  required:
    - type: filesystem
      version: ">=1.0.0"
  optional: []

# ORCHESTRATOR node (may not need direct handlers)
handlers:
  required: []  # Orchestrators coordinate, may not need direct handlers
  optional:
    - type: local
      version: ">=1.0.0"

# COMPUTE node with optional caching
handlers:
  required: []  # Pure compute, no I/O handlers needed
  optional:
    - type: cache
      version: ">=1.0.0"
```

---

### profile_tags

**Purpose**: Categorization tags for contract discovery and filtering.

**Structure**: List of lowercase, hyphen-separated strings.

**Naming Conventions**:

| Tag Category | Pattern | Examples |
|--------------|---------|----------|
| Node role | `<role>` | `runtime`, `kernel`, `compute` |
| Feature area | `<feature>` | `filesystem`, `contracts`, `events` |
| Lifecycle | `<phase>` | `loader`, `wiring`, `discovery` |
| Capability | `<capability>` | `self-hosted`, `hot-reload` |

**Examples**:
```yaml
# Runtime orchestrator tags
profile_tags:
  - runtime
  - kernel
  - self-hosted
  - lifecycle-management

# Contract loader effect tags
profile_tags:
  - filesystem
  - contracts
  - discovery
  - runtime
  - loader
```

**Validation Rules**:
- Tags must be non-empty strings
- No duplicates within a contract
- Runtime contracts MUST include `runtime` tag
- Tags should be lowercase and hyphen-separated

---

### subscriptions

**Purpose**: Kafka topic subscriptions for event-driven contracts.

**Structure**:
```yaml
subscriptions:
  topics:
    - <topic_name>
  # OR list format for detailed subscriptions
subscriptions:
  - topic: <topic_name>
    description: <description>
```

**Topic Naming Conventions**:

All topics MUST follow the pattern: `<namespace>.<domain>.<action>`

| Component | Description | Examples |
|-----------|-------------|----------|
| Namespace | Service or module name | `runtime`, `contracts`, `nodes` |
| Domain | Subject area | `startup`, `contracts`, `events` |
| Action | What happened | `reload`, `ready`, `error` |

**Reserved Prefixes**:
- `runtime.*` - Runtime lifecycle events (e.g., `runtime.startup`, `runtime.shutdown`)
- `contracts.*` - Contract-related events (e.g., `contracts.loaded`, `contracts.validated`)
- `nodes.*` - Node lifecycle events (e.g., `nodes.registered`, `nodes.disposed`)

**Examples**:
```yaml
# Orchestrator subscriptions
subscriptions:
  - topic: runtime.startup
    description: Trigger runtime startup sequence
  - topic: runtime.shutdown
    description: Trigger graceful shutdown sequence
  - topic: runtime.contracts.reload
    description: Trigger contract reload without full restart

# Effect with no subscriptions (uses dict format)
subscriptions:
  topics: []
```

---

## Security Considerations

### Fingerprint Hash Truncation

The fingerprint uses a **12-character (48-bit) truncated SHA256 hash**.

**Collision Probability Analysis**:

| Contracts | Collision Probability | Risk Level |
|-----------|----------------------|------------|
| 1,000 | 0.00000018% | Negligible |
| 10,000 | 0.000018% | Negligible |
| 100,000 | 0.0018% | Very Low |
| 1,000,000 | 0.18% | Low |
| 17,000,000 | 50% | Birthday paradox threshold |

**Mitigation Factors**:
1. **Version prefix**: Collisions only matter within the same semver version
2. **Practical limits**: Most deployments have <100,000 contracts
3. **Drift detection**: Fingerprints are for detecting unintended changes, not cryptographic security
4. **Full hash available**: `--verbose` flag shows complete 64-character hash for verification

**When Full Hash Verification is Recommended**:
- Cross-repository contract synchronization
- Long-term archival and auditing
- High-security environments with strict compliance requirements

**Not Recommended For**:
- Cryptographic signatures (use proper signing instead)
- Authentication or authorization decisions
- Tamper-proof verification (fingerprints can be updated)

### File Size Limits

The fingerprint tool enforces a **10MB file size limit** to prevent DoS attacks
from processing maliciously large files.

### Path Security

Contract loading enforces:
- No path traversal (`..` sequences blocked)
- Restricted to allowed base paths
- Symlink escape prevention
- Absolute path injection blocked

See `io_config.security` in effect contracts for detailed configuration.

---

## References

- [CONTRACT_STABILITY_SPEC.md](../docs/architecture/CONTRACT_STABILITY_SPEC.md) - Fingerprint specification
- [ONEX Four-Node Architecture](../docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node types
- [Contract System](../docs/architecture/CONTRACT_SYSTEM.md) - Contract architecture

---

**Last Updated**: 2025-12-12
**Maintainer**: ONEX Framework Team
