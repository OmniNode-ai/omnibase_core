# OmniNode Architecture – Constraint Map (omniclaude)

> **Role**: Claude Code integration – hooks, skills, agent definitions
> **Handshake Version**: 0.1.0

## Core Principles

- Hooks never block Claude Code
- Data loss acceptable; UI freeze is not
- Graceful degradation on infrastructure failure
- Explicit timestamps (no `datetime.now()` defaults)

## This Repo Contains

- Claude Code hooks (SessionStart, PostToolUse, etc.)
- Agent YAML definitions
- Slash commands and skills
- Event emission to Kafka
- Context injection system

## Rules the Agent Must Obey

1. **Hook scripts must NEVER block on Kafka** - Blocking hooks freeze Claude Code UI
2. **Hooks must exit 0 unless blocking is intentional** - Non-zero exit blocks the tool/prompt
3. **All event schemas are frozen** (`frozen=True`) - Events are immutable after emission
4. **`emitted_at` timestamps must be explicitly injected** - No `datetime.now()` defaults
5. **SessionStart must be idempotent** - May be called multiple times on reconnect
6. **Only preview-safe data to `onex.evt.*` topics** - Observability topics have broad access
7. **Full prompts ONLY to `onex.cmd.omniintelligence.*`** - Intelligence topics are access-restricted

## Performance Budgets

| Hook | Budget | Notes |
|------|--------|-------|
| SessionStart | <50ms | Kafka emit backgrounded |
| UserPromptSubmit | <500ms | Routing is synchronous |
| PostToolUse | <100ms | Quality check is fast |

## Non-Goals (DO NOT)

- ❌ No backwards compatibility - schemas change without deprecation
- ❌ No blocking operations in hooks
- ❌ No hardcoded environment variables - use `.env` or Pydantic Settings

## Failure Mode: Always Continue

| Failure | Behavior | Exit Code |
|---------|----------|-----------|
| Emit daemon down | Events dropped, hook continues | 0 |
| Kafka unavailable | Daemon buffers, then drops | 0 |
| PostgreSQL down | Logging skipped | 0 |
| Routing timeout | Fallback to `polymorphic-agent` | 0 |

**Design principle**: Hooks never block. Data loss is acceptable; UI freeze is not.
