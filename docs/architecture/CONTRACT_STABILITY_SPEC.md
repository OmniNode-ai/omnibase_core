> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Contract Stability Specification

# Contract Stability Specification

**Version**: 1.0.0
**Status**: Draft (v0.4.0)
**Scope**: Cross-repository (omnibase_core, omnibase_spi, omnibase_infra, omniintelligence)

---

## Overview

This document defines the canonical specification for contract versioning, fingerprinting, and normalization. All ONEX repositories MUST conform to this specification.

---

## Contract Version Semantics

### ModelContractVersion

```python
from pydantic import BaseModel

class ModelContractVersion(BaseModel):
    """Typed semver fields for contract versioning."""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
```

### Version Progression Rules

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking change to input/output schema | Major | 0.4.0 -> 1.0.0 |
| New optional field added | Minor | 0.4.0 -> 0.5.0 |
| Bug fix, documentation | Patch | 0.4.0 -> 0.4.1 |

### Downgrade Prevention

- Contracts MUST NOT be downgraded without explicit `ALLOW_DOWNGRADE=true`
- CI check blocks PRs that reduce contract versions
- Downgrades require documented rationale in the changelog

---

## Contract Normalization Pipeline

All contracts MUST be normalized before fingerprint computation:

### Step 1: Resolve Defaults

```python
def resolve_defaults(contract: dict) -> dict:
    """Insert default values for all optional fields."""
    schema = get_contract_schema(contract["type"])
    for field, spec in schema["properties"].items():
        if field not in contract and "default" in spec:
            contract[field] = spec["default"]
    return contract
```

### Step 2: Remove Null Values

```python
def remove_nulls(contract: dict) -> dict:
    """Recursively remove None/null values."""
    return {k: remove_nulls(v) if isinstance(v, dict) else v
            for k, v in contract.items() if v is not None}
```

### Step 3: Canonical Ordering

```python
def canonical_order(contract: dict) -> dict:
    """Alphabetically sort all keys recursively."""
    return {k: canonical_order(v) if isinstance(v, dict) else v
            for k, v in sorted(contract.items())}
```

### Step 4: Stable Serialization

```python
import json

def stable_serialize(contract: dict) -> str:
    """JSON serialize with sorted keys, no whitespace."""
    return json.dumps(contract, sort_keys=True, separators=(",", ":"))
```

### Full Pipeline

```python
def normalize_contract(contract: dict) -> str:
    """Complete normalization pipeline."""
    contract = resolve_defaults(contract)
    contract = remove_nulls(contract)
    contract = canonical_order(contract)
    return stable_serialize(contract)
```

---

## Fingerprint Specification

### Format

```text
<semver>:<sha256-first-12-hex-chars>
```

**Example**: `0.4.0:8fa1e2b4c9d1`

**Format Rationale**: The `semver:hash` format provides both human-readable version context and cryptographic integrity verification in a single compact identifier. The colon separator ensures unambiguous parsing since colons cannot appear in semver or hex strings.

### Computation

```python
import hashlib

def compute_fingerprint(contract: dict) -> str:
    """Compute contract fingerprint after normalization."""
    version = contract.get("version", "0.0.0")
    normalized = normalize_contract(contract)
    hash_bytes = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{version}:{hash_bytes}"
```

### Stability Guarantees

| Guarantee | Scope |
|-----------|-------|
| Same contract -> same fingerprint | Within Python version |
| Same contract -> same fingerprint | Across Python minor versions (3.10, 3.11, 3.12) |
| Same contract -> same fingerprint | Across OS platforms |
| Normalization is idempotent | `normalize(normalize(c)) == normalize(c)` |

### Collision Analysis

The fingerprint uses 12 hexadecimal characters (48 bits) from SHA-256:

- **Unique combinations**: 2^48 = 281,474,976,710,656 (~281 trillion)
- **Birthday paradox threshold**: ~17 million contracts before 50% collision probability
- **Practical safety**: For typical deployments with <100,000 contracts, collision probability is negligible (<0.000002%)
- **Mitigation**: Version prefix ensures collisions only matter within same semver, further reducing practical risk

#### Detailed Collision Probability Table

| Contract Count | Collision Probability | Risk Level |
|----------------|----------------------|------------|
| 1,000 | 0.00000018% | Negligible |
| 10,000 | 0.000018% | Negligible |
| 100,000 | 0.0018% | Very Low |
| 1,000,000 | 0.18% | Low |
| 17,000,000 | 50% | Birthday paradox threshold |

### Security Considerations

#### Hash Truncation Trade-offs

The 12-character (48-bit) hash truncation balances:

1. **Human readability**: Short enough for display in logs and UIs
2. **Collision resistance**: Sufficient for typical deployment sizes
3. **Space efficiency**: Compact for storage in metadata fields

#### When Full Hash is Recommended

For high-security scenarios, use `--verbose` flag to access the complete 64-character SHA256:

```bash
poetry run python scripts/compute_contract_fingerprint.py contract.yaml --verbose
```

**Recommended for**:
- Cross-repository contract synchronization
- Long-term archival and auditing
- Compliance environments requiring cryptographic verification
- Environments with >100,000 contracts

#### What Fingerprints Are NOT Suitable For

Fingerprints are designed for **drift detection**, not cryptographic security:

| Use Case | Fingerprint Suitable? | Alternative |
|----------|----------------------|-------------|
| Drift detection | Yes | - |
| Cache invalidation | Yes | - |
| Debugging contract changes | Yes | - |
| Cryptographic signatures | **No** | Use GPG/PGP signing |
| Authentication/authorization | **No** | Use proper auth tokens |
| Tamper-proof verification | **No** | Use digital signatures |

### Fingerprint Regeneration

When contract content changes, fingerprints MUST be regenerated:

```bash
# Compute new fingerprint
poetry run python scripts/compute_contract_fingerprint.py path/to/contract.yaml

# Update contract YAML with new fingerprint value
# Then validate
poetry run python scripts/compute_contract_fingerprint.py path/to/contract.yaml --validate
```

See [scripts/README.md](../../scripts/README.md) for detailed regeneration procedures.

### Fingerprint Location

Fingerprints appear in:
1. `node.metadata.contract_fingerprint` - Node metadata
2. Adapter response metadata - Tracing
3. Contract validation logs - Debugging

---

## Contract Hash Registry

### Location

`src/omnibase_core/contracts/hash_registry.py`

### API

```python
class ContractHashRegistry:
    """Stores deterministic SHA256 fingerprints for loaded contracts."""

    def register(self, contract_id: str, fingerprint: str) -> None:
        """Register a contract fingerprint."""

    def lookup(self, contract_id: str) -> str | None:
        """Look up a contract fingerprint."""

    def verify(self, contract_id: str, expected: str) -> bool:
        """Verify a contract matches expected fingerprint."""

    def detect_drift(self, contract_id: str, computed: str) -> bool:
        """Detect if contract has drifted from registered fingerprint."""
```

### Use Cases

```text
| Use Case            | Method         |
|---------------------|----------------|
| Migration debugging | detect_drift() |
| Contract loading    | verify()       |
| Registration        | register()     |
```

---

## Validation Phases

Contract validation MUST proceed in this order:

### Phase 1: Structural Validation

- Schema compliance (Pydantic)
- Required fields present
- Type correctness

### Phase 2: Semantic Validation

- Field value ranges
- Enum membership
- Cross-field constraints

### Phase 3: Capability Validation

- Required capabilities declared
- Capabilities supported by runtime
- No conflicting capabilities

### Phase 4: Fingerprint Computation

- Normalize contract
- Compute fingerprint
- Register in hash registry

### Error Format

All validation errors MUST use this format:

```text
ERR_CODE: message (path.to.field)
```

**Examples**:

```text
CONTRACT_INVALID_TYPE: Expected string (input.name)
CONTRACT_MISSING_FIELD: Required field missing (output.result)
CONTRACT_UNSUPPORTED_CAPABILITY: Capability not available (capabilities[0])
```

---

## Cross-Repository Usage

### omnibase_core (Source of Truth)

> **Note (v0.3.6+)**: Protocol definitions are now Core-native in `omnibase_core.protocols`.

- Defines `ServiceContractValidator` interface (Core-native)
- Implements validation logic

### omnibase_spi

- Extends Core protocols for cross-service use
- Depends on Core (not the reverse)

### omnibase_infra

- Consumes fingerprints for logging/tracing
- Validates contracts at runtime load time
- Reports fingerprint mismatches

### omniintelligence

- Uses fingerprints for contract caching
- Validates contracts on agent registration

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-03 | Initial specification |
| 1.0.1 | 2025-12-12 | Added security considerations, collision probability table, regeneration procedures |

---

## References

- [ONEX Four-Node Architecture](./ONEX_FOUR_NODE_ARCHITECTURE.md)
- [scripts/README.md](../../scripts/README.md) - CLI documentation for fingerprint tools
