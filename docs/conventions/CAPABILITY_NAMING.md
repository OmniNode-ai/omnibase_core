# ONEX Capability Naming Conventions

This document defines naming conventions for capability identifiers used in vendor-agnostic dependency declarations throughout the ONEX system.

---

## Table of Contents

1. [Overview](#overview)
2. [Naming Format](#naming-format)
3. [Token Rules](#token-rules)
4. [Preferred Style](#preferred-style)
5. [Version Suffix](#version-suffix)
6. [Valid Examples](#valid-examples)
7. [Invalid Examples](#invalid-examples)
8. [Best Practices](#best-practices)
9. [Implementation Reference](#implementation-reference)

---

## Overview

Capability names are identifiers used in ONEX handler contracts to declare dependencies on abstract capabilities rather than concrete vendors. This enables vendor-agnostic dependency declaration where:

- **Contracts declare capabilities + constraints**
- **Registry resolves to providers at runtime**
- **Vendors never appear in consumer contracts**

Capability names follow a hierarchical structure that allows for domain organization, capability classification, and optional variant specification.

---

## Naming Format

### Pattern Overview

Capabilities follow the pattern:

```text
<domain>.<type>[.<variant>]
```

**Components:**
- `<domain>` - Business domain or namespace (e.g., `database`, `storage`, `llm`)
- `<type>` - Capability type within the domain (e.g., `relational`, `vector`, `text-embedding`)
- `<variant>` - Optional variant or version specifier (e.g., `qdrant`, `v1`)

### Regex Pattern

The capability format is enforced by the following regex pattern:

```regex
^[a-z0-9_-]+(\.[a-z0-9_-]+)+$
```

### Pattern Breakdown

| Component | Pattern | Description |
|-----------|---------|-------------|
| **First token** | `[a-z0-9_-]+` | Lowercase letters, digits, underscores, hyphens |
| **Separator** | `\.` | Dot separator between tokens |
| **Additional tokens** | `([a-z0-9_-]+)+` | One or more additional tokens required |

### Key Rules

1. **Lowercase only**: All characters must be lowercase
2. **At least two tokens**: A dot separator is **required** (minimum: `domain.type`)
3. **No consecutive dots**: `database..relational` is invalid
4. **No leading/trailing dots**: `.database.relational` and `database.relational.` are invalid
5. **Length constraints**: 3-128 characters total

---

## Token Rules

Each token within a capability name can contain:

| Character Type | Allowed | Example |
|----------------|---------|---------|
| Lowercase letters | Yes | `database`, `vector` |
| Digits | Yes | `http2`, `v1` |
| Hyphens (`-`) | Yes | `text-embedding`, `key-value` |
| Underscores (`_`) | Yes | `event_bus`, `key_value` |
| Uppercase letters | No | `Database` is invalid |
| Spaces | No | `text embedding` is invalid |
| Special characters | No | `text@embedding` is invalid |

### Token Length

- Single-character tokens are allowed (e.g., `a.b` is valid)
- The overall capability must be at least 3 characters (enforced by field constraint)

---

## Preferred Style

While both hyphens and underscores are syntactically valid within tokens, **kebab-case (hyphens) is the preferred style** for multi-word tokens.

### Recommended: Kebab-case (Hyphens)

```text
llm.text-embedding.v1       # Preferred
cache.key-value             # Preferred
storage.time-series         # Preferred
messaging.pub-sub           # Preferred
```

### Acceptable: Snake-case (Underscores)

```text
messaging.event_bus         # Acceptable
cache.key_value             # Acceptable
storage.time_series         # Acceptable
```

### Why Kebab-case is Preferred

1. **URL-friendly**: Hyphens are standard in URLs and URIs, making capabilities easier to use in REST APIs and web contexts

2. **Industry conventions**: Kebab-case aligns with common naming conventions in:
   - npm package names (`@scope/package-name`)
   - Docker image names (`my-image-name`)
   - Kubernetes resources (`my-deployment-name`)
   - DNS hostnames (`my-service.example.com`)

3. **Readability**: Hyphens provide clear visual separation without the ambiguity of underscores in some fonts

4. **Consistency**: Using one style throughout the codebase reduces cognitive load and prevents naming drift

### When Snake-case May Be Appropriate

- **Legacy integration**: When interfacing with systems that use snake_case conventions
- **Code generation**: When capability names are used to generate Python identifiers (though aliases handle this)
- **Team preference**: If your team has established snake_case conventions

---

## Version Suffix

Capability names can include an optional version suffix for capability versioning:

### Format

```text
<domain>.<type>@<semver>
```

### Examples

```text
llm.text-embedding@1.0.0        # Specific version
storage.vector@2.1.0            # Major version 2
database.relational@1.0.0       # Versioned database capability
```

### When to Use Version Suffixes

- **Breaking changes**: When a capability API changes incompatibly
- **Feature gates**: When new features require explicit opt-in
- **Migration paths**: When supporting multiple versions during transitions

**Note**: Version suffixes are optional. Most capabilities do not require explicit versioning when changes are backward-compatible.

---

## Valid Examples

### Standard Capabilities

| Capability | Domain | Type | Variant | Description |
|------------|--------|------|---------|-------------|
| `database.relational` | `database` | `relational` | - | Any relational database |
| `database.document` | `database` | `document` | - | Document/NoSQL database |
| `storage.vector` | `storage` | `vector` | - | Vector storage capability |
| `storage.vector.qdrant` | `storage` | `vector` | `qdrant` | Qdrant-compatible vector store |
| `cache.key-value` | `cache` | `key-value` | - | Key-value cache (preferred) |
| `cache.distributed` | `cache` | `distributed` | - | Distributed cache |

### Multi-word Tokens (Preferred Style)

| Capability | Style | Notes |
|------------|-------|-------|
| `llm.text-embedding` | Kebab-case | Preferred for multi-word |
| `llm.text-embedding.v1` | Kebab-case | With variant |
| `messaging.pub-sub` | Kebab-case | Publish-subscribe messaging |
| `storage.time-series` | Kebab-case | Time-series storage |

### Multi-word Tokens (Acceptable Style)

| Capability | Style | Notes |
|------------|-------|-------|
| `messaging.event_bus` | Snake-case | Acceptable alternative |
| `cache.key_value` | Snake-case | Acceptable alternative |
| `storage.time_series` | Snake-case | Acceptable alternative |

### Short Tokens

| Capability | Notes |
|------------|-------|
| `http.client` | Short, clear token names |
| `secrets.vault` | Secrets management |
| `a.b` | Minimal valid capability (edge case) |

---

## Invalid Examples

| Invalid Capability | Issue | Corrected |
|-------------------|-------|-----------|
| `Database.Relational` | Uppercase not allowed | `database.relational` |
| `database` | Missing dot (single token) | `database.relational` |
| `logging` | Missing dot (single token) | `core.logging` |
| `database..relational` | Consecutive dots | `database.relational` |
| `.database.relational` | Leading dot | `database.relational` |
| `database.relational.` | Trailing dot | `database.relational` |
| `database relational` | Spaces not allowed | `database.relational` |
| `database@relational` | @ in wrong position | `database.relational@1.0.0` |
| `db` | Too short (< 3 chars) | `database.relational` |

---

## Best Practices

### 1. Use Descriptive Domain Names

Choose domain names that clearly identify the capability area:

```text
# Good - specific domains
database.relational
storage.vector
messaging.event-bus

# Avoid - too generic
service.provider
thing.capability
```

### 2. Be Consistent Within Projects

Choose one style (kebab-case preferred) and apply it consistently:

```text
# Consistent kebab-case
llm.text-embedding
cache.key-value
storage.time-series

# Avoid mixing styles
llm.text-embedding      # kebab
cache.key_value         # snake (inconsistent)
```

### 3. Use Variants for Specificity

Add variants when you need to narrow capability matching:

```text
# General capability
storage.vector

# Specific variant for compatibility requirements
storage.vector.qdrant
storage.vector.milvus
```

### 4. Keep Names Concise

Balance clarity with brevity:

```text
# Good
llm.text-embedding
cache.distributed

# Too verbose
large-language-model.text-embedding-generation-service
cache.distributed-multi-region-replicated
```

### 5. Document Custom Capabilities

Maintain a registry of capabilities used in your project:

```python
CAPABILITY_REGISTRY = {
    "database.relational": "Any SQL-compliant relational database",
    "storage.vector": "Vector storage for embeddings and similarity search",
    "llm.text-embedding": "Text embedding generation capability",
    "cache.key-value": "Simple key-value cache with TTL support",
}
```

---

## Implementation Reference

### ModelCapabilityDependency

Capability validation is implemented in `ModelCapabilityDependency`:

**Location**: `src/omnibase_core/models/capabilities/model_capability_dependency.py`

**Validation Pattern**:
```python
# Both hyphens and underscores are allowed within tokens
_CAPABILITY_PATTERN = re.compile(r"^[a-z0-9_-]+(\.[a-z0-9_-]+)+$")
```

**Usage**:
```python
from omnibase_core.models.capabilities import ModelCapabilityDependency

# Valid capability with preferred kebab-case
dep = ModelCapabilityDependency(
    alias="vectors",
    capability="storage.vector",
)

# Access parsed components
dep.domain          # "storage"
dep.capability_type # "vector"
dep.variant         # None
```

### Alias Naming

Aliases (the local binding name) follow different rules than capabilities:

- Must start with a lowercase letter
- Can contain lowercase letters, digits, and underscores only
- No hyphens allowed in aliases (must be valid Python identifiers)
- No dots allowed

```python
# Valid alias
dep = ModelCapabilityDependency(
    alias="my_cache",  # Underscores OK in aliases
    capability="cache.key-value",  # Hyphens OK in capabilities
)
```

---

## Related Documentation

- **Naming Conventions**: `docs/conventions/NAMING_CONVENTIONS.md` - General ONEX naming patterns
- **ModelCapabilityDependency**: `src/omnibase_core/models/capabilities/model_capability_dependency.py` - Implementation reference
- **ModelRequirementSet**: `src/omnibase_core/models/capabilities/model_requirement_set.py` - Requirement constraints
- **Pydantic Best Practices**: `docs/conventions/PYDANTIC_BEST_PRACTICES.md`

---

**Last Updated**: 2025-12-30
**Project**: omnibase_core v0.4.0
