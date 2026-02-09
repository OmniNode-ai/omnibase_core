# OmniNode Architecture – Constraint Map (omnimemory)

> **Role**: Memory system – persistence, recall, embeddings, vector storage
> **Handshake Version**: 0.1.0

## Platform-Wide Rules

1. **No backwards compatibility** - Breaking changes always acceptable. No deprecation periods, shims, or migration paths.
2. **Delete old code immediately** - Never leave deprecated code "for reference." If unused, delete it.
3. **No speculative refactors** - Only make changes that are directly requested or clearly necessary.
4. **No silent schema changes** - All schema changes must be explicit and deliberate.
5. **Frozen event schemas** - All models crossing boundaries (events, intents, actions, envelopes, projections) must use `frozen=True`. Internal mutable state is fine.
6. **Explicit timestamps** - Never use `datetime.now()` defaults. Inject timestamps explicitly.
7. **No hardcoded configuration** - All config via `.env` or Pydantic Settings. No localhost defaults.
8. **Kafka is required infrastructure** - Use async/non-blocking patterns. Never block the calling thread waiting for Kafka acks.
9. **No `# type: ignore` without justification** - Requires explanation comment and ticket reference.

## Core Principles

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
2. **Zero `Any` types** - Strong typing throughout
3. **All models must have Field descriptions** - `Field(..., description="...")`
4. **Models in `models/` directory** - Not `core/`
5. **Follow model exemption pattern** when placing models with handlers

## Non-Goals (DO NOT)

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
