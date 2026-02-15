> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Claude Code Hooks

# Claude Code Hooks Architecture

> **Why in core?** These hook models are part of the shared contract surface consumed by omniclaude. They define the canonical event types for Claude Code integration.

---

## Hook Event Types

| Event | Purpose | Category |
|-------|---------|----------|
| `SESSION_START` | Session initialization | Lifecycle |
| `USER_PROMPT_SUBMIT` | Prompt submission | Lifecycle |
| `PRE_TOOL_USE` | Before tool execution | Agentic Loop |
| `POST_TOOL_USE` | After tool execution | Agentic Loop |
| `SUBAGENT_START/STOP` | Subagent lifecycle | Agentic Loop |
| `STOP` | Session stopping | Lifecycle |

---

## Hook Event Model

```python
class ModelClaudeCodeHookEvent(BaseModel):
    event_type: EnumClaudeCodeHookEventType
    session_id: str
    correlation_id: UUID | None
    timestamp_utc: datetime  # Must be timezone-aware
    payload: ModelClaudeCodeHookEventPayload
```

---

## Lifecycle Flow

```
SessionStart → UserPromptSubmit → [PreToolUse → PostToolUse]* → Stop → SessionEnd
```

---

## Key Files

| Purpose | Location |
|---------|----------|
| Hook event type enum | `src/omnibase_core/enums/hooks/enum_claude_code_hook_event_type.py` |
| Hook event model | `src/omnibase_core/models/hooks/model_claude_code_hook_event.py` |
| Hook payload model | `src/omnibase_core/models/hooks/model_claude_code_hook_event_payload.py` |

---

## Related Documentation

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md)
