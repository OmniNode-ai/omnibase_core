# OmniNode Architecture – Constraint Map (omniclaude)

> **Role**: Claude Code integration – hooks, skills, agent definitions
> **Handshake Version**: 0.2.0

## Core Principles

- Hooks never block Claude Code
- Data loss acceptable; UI freeze is not
- Graceful degradation on infrastructure failure
- Explicit timestamps (no `datetime.now()` defaults)
- Fail-fast configuration (services disabled by default)
- Privacy-first event emission (public vs restricted topics)

## This Repo Contains

- Claude Code hooks (SessionStart, UserPromptSubmit, PostToolUse, SessionEnd)
- Agent YAML definitions (`plugins/onex/agents/configs/`)
- Slash commands and skills (`plugins/onex/commands/`, `plugins/onex/skills/`)
- Event emission via Unix socket daemon
- Context injection and pattern learning system
- Polymorphic agent coordination (Polly)

## Rules the Agent Must Obey

### Hook Rules

1. **Hook scripts must NEVER block on Kafka** - Blocking hooks freeze Claude Code UI
2. **Hooks must exit 0 unless blocking is intentional** - Non-zero exit blocks the tool/prompt
3. **All event schemas are frozen** (`frozen=True`) - Events are immutable after emission
4. **`emitted_at` timestamps must be explicitly injected** - No `datetime.now()` defaults
5. **SessionStart must be idempotent** - May be called multiple times on reconnect

### Privacy & Topic Rules

6. **Only preview-safe data to `onex.evt.*` topics** - Observability topics have broad access
7. **Full prompts ONLY to `onex.cmd.omniintelligence.*`** - Intelligence topics are access-restricted
8. **Topic naming follows ONEX canonical format** - `onex.{kind}.{producer}.{event-name}.v{n}`
9. **Secrets must be auto-redacted** - OpenAI keys, AWS keys, GitHub tokens, etc.

### Agent YAML Rules

10. **Agent YAML requires `schema_version: "1.0.0"`** - Required for validation
11. **Agent names must start with `agent-`** - Convention: `agent-api-architect`
12. **Agent types use snake_case** - Example: `api_architect`
13. **All agents need `activation_patterns`** - Makes agent routable

### Configuration Rules

14. **No localhost defaults** - Prevents production mistakes
15. **Services default to disabled** - Explicit `USE_EVENT_ROUTING=true` required
16. **`KAFKA_ENVIRONMENT` must be explicit** - One of: `dev`, `staging`, `prod`
17. **Use `${CLAUDE_PLUGIN_ROOT}` for paths** - Never hardcode absolute paths

## Performance Budgets

| Hook | Budget | Sync Components | Async Components |
|------|--------|-----------------|------------------|
| SessionStart | <50ms | daemon check, stdin read | Kafka, Postgres |
| UserPromptSubmit | <500ms | routing, agent load, context | Kafka, intelligence |
| PostToolUse | <100ms | stdin read, quality check | Kafka, content capture |
| SessionEnd | <50ms | stdin read | Kafka, Postgres |

## Parallel Execution Rules (Polymorphic Agents)

- **File Separation**: Each Polly creates own file (zero conflicts)
- **Single Branch**: All work on same branch (no merge overhead)
- **Clear Interfaces**: Contracts defined upfront before dispatch
- **Simultaneous Launch**: All Pollys in single message (true parallelism)

## Non-Goals (DO NOT)

- ❌ No backwards compatibility - schemas change without deprecation
- ❌ No blocking operations in hooks
- ❌ No hardcoded environment variables - use `.env` or Pydantic Settings
- ❌ No localhost defaults in configuration
- ❌ No sensitive data in `onex.evt.*` topics
- ❌ No agent YAML without `schema_version`
- ❌ No sequential Polly dispatch when parallel is possible

## Failure Mode: Always Continue

| Failure | Behavior | Exit Code |
|---------|----------|-----------|
| Emit daemon down | Events dropped, hook continues | 0 |
| Kafka unavailable | Daemon buffers, then drops | 0 |
| PostgreSQL down | Logging skipped | 0 |
| Routing timeout | Fallback to `polymorphic-agent` | 0 |
| Agent YAML missing | Use default agent, log warning | 0 |
| Context injection fails | Proceed without patterns | 0 |
| Malformed stdin | Log error, pass through empty | 0 |

**Design principle**: Hooks never block. Data loss is acceptable; UI freeze is not.

## Pydantic Model Configuration

All event models must use:

```python
model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)
```

- `frozen=True` - Immutable after creation
- `extra="ignore"` - Permit external schema evolution
- `from_attributes=True` - pytest-xdist worker compatibility
