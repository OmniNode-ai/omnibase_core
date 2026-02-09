# OmniNode Architecture – Constraint Map (omniintelligence)

> **Role**: Intelligence platform – code quality, pattern learning, semantic analysis
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

- Declarative nodes, imperative handlers
- Thin shell pattern (<100 lines per node)
- Correlation IDs threaded through all operations

## This Repo Contains

- Claude Code hook event processing
- Pattern learning (extraction, clustering, lifecycle)
- Quality scoring with ONEX compliance
- Intent classification (pure computation)
- Semantic code analysis

**Note**: Vector storage (Qdrant) and graph operations (Memgraph) are in `omnimemory`.

## Rules the Agent Must Obey

1. **Node classes must be thin shells** (<100 lines) - Logic belongs in handlers
2. **Handlers must return structured errors, not raise** - Domain errors are data, not exceptions
3. **`correlation_id` must be threaded through all operations** - End-to-end tracing required

## Non-Goals (DO NOT)

- ❌ No developer convenience over strictness - Boilerplate is acceptable if it enforces boundaries
- ❌ No framework agnosticism - This is ONEX-native, no abstraction layers
- ❌ No flexibility over determinism - One way to do things
- ❌ No minimal code - Explicit is better than clever

## Thin Shell Pattern

```python
# CORRECT - ~22 lines, delegates to handler
class NodeQualityScoringCompute(NodeCompute[Input, Output]):
    async def compute(self, input_data: Input) -> Output:
        return handle_quality_scoring_compute(input_data)
```

## Node Types

| Type | Purpose | Output |
|------|---------|--------|
| Orchestrator | Coordinate workflows | `events[]`, `intents[]` |
| Reducer | FSM state transitions | `projections[]` |
| Compute | Pure data processing | `result` (required) |
| Effect | External I/O | `events[]` |
