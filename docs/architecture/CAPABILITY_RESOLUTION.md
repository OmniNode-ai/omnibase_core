# Capability Resolution - omnibase_core

**Status**: Draft
**Version**: 0.4.0
**Related**: [Dependency Injection](DEPENDENCY_INJECTION.md) | [Contract System](CONTRACT_SYSTEM.md)

## Overview

Capability resolution is the process of matching capability dependencies declared in handler contracts to concrete provider implementations at runtime. This enables vendor-agnostic dependency management following the core ONEX principle:

> **"Contracts declare capabilities + constraints. Registry resolves to providers."**

Instead of depending on specific vendors (e.g., "postgres", "redis"), handlers declare dependencies on **capabilities** with **requirements**. The resolver matches these declarations to available providers using a two-phase filtering and selection process.

## Core Concepts

### Capability Dependencies

A `ModelCapabilityDependency` declares what a handler needs without specifying how it's provided:

```python
from omnibase_core.models.capabilities import (
    ModelCapabilityDependency,
    ModelRequirementSet,
)

# Declare a database dependency
db_dep = ModelCapabilityDependency(
    alias="db",                           # Local binding name
    capability="database.relational",     # Capability identifier
    requirements=ModelRequirementSet(
        must={"supports_transactions": True},
        prefer={"max_latency_ms": 20},
    ),
    selection_policy="auto_if_unique",
)
```

### Capability Naming Convention

Capabilities follow a hierarchical pattern: `<domain>.<type>[.<variant>]`

| Pattern | Example | Description |
|---------|---------|-------------|
| `domain.type` | `database.relational` | Any relational database |
| `domain.type.variant` | `storage.vector.qdrant` | Qdrant-compatible vector store |
| With hyphens | `llm.text-embedding.v1` | Text embedding capability |
| With underscores | `messaging.event_bus` | Event bus capability |

**Rules**:
- Tokens contain lowercase letters, digits, underscores, and hyphens
- Dots are semantic separators between tokens (at least one dot required)
- No uppercase, no consecutive dots, no leading/trailing dots

## Resolution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAPABILITY RESOLUTION FLOW                        │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │  Dependency Request │
                    │  (ModelCapability   │
                    │   Dependency)       │
                    └──────────┬──────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 1: FILTERING (Hard Constraints)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────┐         ┌─────────────────┐                       │
│   │ Apply "must"    │────────▶│ Apply "forbid"  │                       │
│   │ constraints     │         │ constraints     │                       │
│   │                 │         │                 │                       │
│   │ Provider MUST   │         │ Provider MUST   │                       │
│   │ have all attrs  │         │ NOT have any    │                       │
│   │ with matching   │         │ forbidden attr  │                       │
│   │ values          │         │ values          │                       │
│   └─────────────────┘         └────────┬────────┘                       │
│                                        │                                 │
│   Result: Providers that satisfy all hard constraints                    │
│                                        │                                 │
└────────────────────────────────────────┼────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │         Filtered Providers              │
                    │    (passed must + forbid checks)        │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 2: SELECTION (Based on Policy)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     Selection Policy                             │   │
│   ├─────────────────────────────────────────────────────────────────┤   │
│   │                                                                  │   │
│   │   auto_if_unique     best_score         require_explicit        │   │
│   │        │                  │                    │                 │   │
│   │        ▼                  ▼                    ▼                 │   │
│   │   ┌─────────┐       ┌─────────┐          ┌─────────┐            │   │
│   │   │ Count=1 │       │ Score   │          │ NEVER   │            │   │
│   │   │ Select  │       │ prefer  │          │ auto-   │            │   │
│   │   │         │       │ matches │          │ select  │            │   │
│   │   │ Count>1 │       │         │          │         │            │   │
│   │   │ REJECT  │       │ Highest │          │ Require │            │   │
│   │   │         │       │ score   │          │ explicit│            │   │
│   │   │ Count=0 │       │ wins    │          │ binding │            │   │
│   │   │ FAIL    │       │         │          │         │            │   │
│   │   └─────────┘       │ Ties:   │          └─────────┘            │   │
│   │                     │ use     │                                  │   │
│   │                     │ hints   │                                  │   │
│   │                     └─────────┘                                  │   │
│   │                                                                  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │              RESULT                      │
                    ├─────────────────────────────────────────┤
                    │  - Selected provider (success)          │
                    │  - Ambiguous (multiple matches)         │
                    │  - No match (zero providers)            │
                    │  - Requires binding (explicit policy)   │
                    └─────────────────────────────────────────┘
```

## Requirement Tiers

Requirements are organized into four tiers that control filtering and ranking:

### 1. `must` - Hard Constraints (Filter)

Providers **MUST** satisfy all `must` constraints to be considered. Any missing or mismatched value excludes the provider.

```python
requirements=ModelRequirementSet(
    must={
        "supports_transactions": True,   # Provider must support transactions
        "encryption_in_transit": True,   # Provider must encrypt data in transit
        "min_version": 14,               # Provider must be at least version 14
    },
)
```

**Behavior**: Providers not meeting ALL `must` constraints are **excluded entirely**.

### 2. `forbid` - Exclusion Constraints (Filter)

Providers matching **ANY** `forbid` constraint are excluded.

```python
requirements=ModelRequirementSet(
    forbid={
        "deprecated": True,              # Exclude deprecated providers
        "scope": "public_internet",      # Exclude public-facing providers
    },
)
```

**Behavior**: Any match on `forbid` **excludes** the provider, even if all `must` constraints pass.

### 3. `prefer` - Soft Preferences (Scoring)

Preferences affect provider ranking but don't exclude. Each match increases the provider's score.

```python
requirements=ModelRequirementSet(
    prefer={
        "region": "us-east-1",           # Prefer providers in us-east-1
        "max_latency_ms": 20,            # Prefer low-latency providers
        "supports_jsonb": True,          # Prefer JSON support
    },
)
```

**Behavior with `strict` flag**:
- `strict=True` (default): Unmet preferences cause match **failure**
- `strict=False`: Unmet preferences generate **warnings** only

### 4. `hints` - Advisory (Tie-Breaking)

Hints provide guidance when multiple providers have equal scores. They are purely advisory and lowest priority.

```python
requirements=ModelRequirementSet(
    hints={
        "vendor_preference": ["postgres", "mysql"],  # Ordered vendor preference
        "team_approved": ["provider_a", "provider_b"],
    },
)
```

**Behavior**: Only consulted when providers are otherwise tied. Resolver-specific implementation.

## Selection Policies

### `auto_if_unique` (Default)

**Best for**: Dependencies where exactly one provider is expected.

**Behavior**:
1. After filtering by `must`/`forbid`, count remaining providers
2. If exactly **one** provider remains: **auto-select** it
3. If **zero** match: resolution **fails** (no provider available)
4. If **multiple** match: resolution is **ambiguous**

```python
# Database dependency - expect unique match
db_dep = ModelCapabilityDependency(
    alias="db",
    capability="database.relational",
    requirements=ModelRequirementSet(
        must={"supports_transactions": True, "engine": "postgres"},
    ),
    selection_policy="auto_if_unique",  # Default
)
```

**Ambiguity Handling**: When multiple providers match, the resolver must:
- Return an "ambiguous" status requiring user resolution, OR
- Raise an error listing matching providers, OR
- Fall back to a secondary strategy (resolver-specific)

### `best_score`

**Best for**: Dependencies where multiple providers may match and preferences should guide selection.

**Behavior**:
1. Filter by `must`/`forbid` constraints
2. Score each remaining provider by `prefer` matches:
   - Each matching `prefer` value adds points (typically +1)
3. Select the **highest-scoring** provider
4. Break ties using `hints`:
   - Process hints in order of declaration
   - First matching hint determines winner
5. If still tied: resolver-specific (e.g., first registered, alphabetical)

```python
# Cache with region preference
cache_dep = ModelCapabilityDependency(
    alias="cache",
    capability="cache.distributed",
    requirements=ModelRequirementSet(
        must={"distributed": True},
        prefer={"region": "us-east-1", "latency_ms": 10},
        hints={"vendor_preference": ["redis", "memcached"]},
    ),
    selection_policy="best_score",
    strict=False,  # Allow fallback if region unavailable
)
```

**Scoring Example**:
| Provider | region | latency_ms | Score |
|----------|--------|------------|-------|
| redis_west | us-west-2 | 20 | 0 |
| redis_east | us-east-1 | 15 | 1 (region match) |
| memcached | us-east-1 | 10 | 2 (region + latency) |

Result: `memcached` selected (highest score).

### `require_explicit`

**Best for**: Security-sensitive dependencies that should **never** be auto-resolved.

**Behavior**:
1. **Never** auto-select, even if exactly one provider matches
2. **Always** require explicit provider binding via:
   - Configuration file (binding section)
   - Runtime API call
   - User prompt/selection
3. Resolution **fails** until explicit binding is provided

```python
# Secrets - must be explicitly bound
secrets_dep = ModelCapabilityDependency(
    alias="secrets",
    capability="secrets.vault",
    requirements=ModelRequirementSet(
        must={"encryption": "aes-256"},
    ),
    selection_policy="require_explicit",
)

# Check programmatically
assert secrets_dep.requires_explicit_binding is True
```

**Use Cases**:
- Secrets management (`secrets.vault`)
- Credential stores
- Production databases
- Payment processors
- Any dependency with security implications

## Ambiguity Handling

### When Ambiguity Occurs

Ambiguity occurs with `auto_if_unique` when multiple providers pass filtering:

```
Request: capability="database.relational", must={"supports_transactions": True}

Available Providers:
  - postgres_primary: supports_transactions=True, engine=postgres
  - postgres_replica: supports_transactions=True, engine=postgres
  - mysql_cluster:    supports_transactions=True, engine=mysql

Result: AMBIGUOUS (3 providers match)
```

### Resolution Strategies

**1. Error with Provider List** (Recommended for development):
```
ResolutionError: Ambiguous capability resolution for 'database.relational'
Multiple providers match:
  - postgres_primary
  - postgres_replica
  - mysql_cluster

Resolution options:
  A) Add more 'must' constraints to narrow selection
  B) Use 'best_score' policy with 'prefer' constraints
  C) Switch to 'require_explicit' policy and bind explicitly
```

**2. Return Ambiguous Status** (For interactive resolution):
```python
result = resolver.resolve(dependency)
if result.status == "ambiguous":
    # Present options to user
    selected = prompt_user_selection(result.matching_providers)
    result = resolver.resolve_with_binding(dependency, selected)
```

**3. Add More Constraints**:
```python
# Before: Ambiguous (multiple postgres instances)
dep = ModelCapabilityDependency(
    alias="db",
    capability="database.relational",
    requirements=ModelRequirementSet(
        must={"supports_transactions": True},
    ),
)

# After: Unique (only one primary)
dep = ModelCapabilityDependency(
    alias="db",
    capability="database.relational",
    requirements=ModelRequirementSet(
        must={"supports_transactions": True, "role": "primary"},
    ),
)
```

**4. Switch to `best_score`**:
```python
dep = ModelCapabilityDependency(
    alias="db",
    capability="database.relational",
    requirements=ModelRequirementSet(
        must={"supports_transactions": True},
        prefer={"role": "primary", "region": "us-east-1"},
    ),
    selection_policy="best_score",
)
```

## Configuration Examples

### YAML Contract with Capability Dependencies

```yaml
# handler_contract.yaml
handler_name: "onex:order-processor"
handler_version: "1.0.0"

capability_dependencies:
  # Database with explicit constraints
  - alias: "db"
    capability: "database.relational"
    requirements:
      must:
        engine: "postgres"
        supports_transactions: true
      prefer:
        max_latency_ms: 20
        region: "us-east-1"
    selection_policy: "best_score"
    strict: true

  # Cache with fallback allowed
  - alias: "cache"
    capability: "cache.distributed"
    requirements:
      prefer:
        region: "us-east-1"
      hints:
        vendor_preference: ["redis", "memcached"]
    selection_policy: "best_score"
    strict: false  # Allow fallback if region unavailable

  # Secrets - explicit binding required
  - alias: "secrets"
    capability: "secrets.vault"
    requirements:
      must:
        encryption: "aes-256"
    selection_policy: "require_explicit"

  # Vector store with variant
  - alias: "vectors"
    capability: "storage.vector"
    requirements:
      must:
        dimensions: 1536
      hints:
        engine_preference: ["qdrant", "milvus"]
    selection_policy: "auto_if_unique"
```

### Explicit Bindings Configuration

When using `require_explicit` or resolving ambiguity:

```yaml
# bindings.yaml
capability_bindings:
  order-processor:
    secrets: "hashicorp-vault-prod"  # Explicit binding for secrets
    db: "postgres-primary-us-east"   # Optional: override auto-selection
```

## Best Practices

### DO

1. **Use specific capabilities**: `database.relational.postgres` vs `database`
2. **Start with `auto_if_unique`**: Simplest policy, switch only when needed
3. **Use `require_explicit` for security**: Secrets, credentials, production databases
4. **Add `must` constraints**: Narrow selection to avoid ambiguity
5. **Use `hints` for tie-breaking**: Document vendor preferences

### DON'T

1. **Avoid vendor names in capability**: Use `database.relational`, not `postgres`
2. **Don't use `best_score` without `prefer`**: Scoring needs preferences
3. **Don't ignore ambiguity errors**: Add constraints or switch policies
4. **Don't use `strict=False` for critical dependencies**: Preferences should be enforced

## Error Messages

### Common Resolution Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoProviderFound` | Zero providers match `must`/`forbid` | Relax constraints or register providers |
| `AmbiguousResolution` | Multiple providers match with `auto_if_unique` | Add constraints or use `best_score` |
| `ExplicitBindingRequired` | `require_explicit` policy without binding | Provide explicit binding in config |
| `PreferencesNotMet` | `prefer` constraints failed with `strict=True` | Set `strict=False` or adjust preferences |

## Future Enhancements

The following enhancements are planned for future releases:

1. **Weighted Preferences**: Allow `prefer` constraints to have different weights
   ```python
   prefer={"region": ("us-east-1", weight=2), "latency_ms": (10, weight=1)}
   ```

2. **Composite Scoring**: Support custom scoring functions
   ```python
   selection_policy="best_score",
   scoring_function="latency_weighted"
   ```

3. **Fallback Chains**: Ordered list of capabilities to try
   ```python
   capability=["database.relational.postgres", "database.relational"]
   ```

4. **Dynamic Constraints**: Runtime-evaluated constraints
   ```python
   must={"capacity_available": lambda p: p.current_load < 0.8}
   ```

5. **Resolution Caching**: Cache resolution results for performance
   ```python
   cache_resolution=True,
   cache_ttl_seconds=300
   ```

---

## Related Documentation

- [ModelCapabilityDependency](../../src/omnibase_core/models/capabilities/model_capability_dependency.py) - Source implementation
- [ModelRequirementSet](../../src/omnibase_core/models/capabilities/model_requirement_set.py) - Requirement tiers
- [Dependency Injection](DEPENDENCY_INJECTION.md) - Container-based DI
- [Contract System](CONTRACT_SYSTEM.md) - Contract architecture

---

**Last Updated**: 2025-12-30 | **Version**: 0.4.0
