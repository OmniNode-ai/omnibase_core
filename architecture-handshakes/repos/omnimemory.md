# OmniNode Architecture – Constraint Map (omnimemory)

> **Role**: Memory system – persistence, recall, embeddings, vector storage
> **Handshake Version**: 0.1.0

## Core Principles

- **ZERO BACKWARDS COMPATIBILITY** - Breaking changes always acceptable
- Sub-100ms memory operations
- ONEX 4.0 compliance
- Strong typing (zero `Any` types)

## This Repo Contains

- Qdrant vector storage integration
- Memgraph graph operations
- Memory retrieval and management
- Pattern storage and recall
- 26+ Pydantic models (zero `Any` types)

## Rules the Agent Must Obey

1. **ALL version fields MUST use `ModelSemVer` directly** - No `str` fallbacks, no union types
2. **No backwards compatibility EVER** - Delete old code, never deprecate
3. **Zero `Any` types** - Strong typing throughout
4. **All models must have Field descriptions** - `Field(..., description="...")`
5. **Models in `models/` directory** - Not `core/`
6. **Follow model exemption pattern** when placing models with handlers

## Non-Goals (DO NOT)

- ❌ **NEVER keep backwards compatibility** - This is non-negotiable
- ❌ No deprecated code maintenance - Delete old code immediately
- ❌ No compatibility shims or migration paths
- ❌ No `version: ModelSemVer | str` union types
- ❌ No string-to-semver convenience validators

## Forbidden Patterns

```python
# WRONG - Union types for backwards compatibility
version: ModelSemVer | str  # NEVER

# WRONG - Convenience validators accepting strings
@field_validator("version", mode="before")
def convert_string(cls, v):
    if isinstance(v, str):
        return ModelSemVer.from_str(v)
    return v
```

## Required Pattern

```python
# CORRECT - ModelSemVer only, callers convert
version: ModelSemVer = Field(..., description="Semantic version")

# Callers convert BEFORE calling
config = MyConfig(version=ModelSemVer.from_str("1.0.0"))
```

## When You See Old Code

1. **DELETE IT** - Do not refactor, do not deprecate
2. No migration path - Callers update or they break
3. No compatibility layer - Clean break every time
