# Payload Type Architecture (OMN-1008)

**Status**: Proposed
**Author**: OmniNode Team
**Created**: 2025-12-24
**Last Updated**: 2025-12-25

---

## Decision Summary

Replace `dict[str, Any]` payload fields in 4 core models with **Pydantic discriminated unions** to achieve compile-time type safety and exhaustive pattern matching.

**Affected Models**:
1. `ModelIntent` (extension intents)
2. `ModelAction` (orchestrator actions)
3. `ModelRuntimeDirective` (internal runtime signals)
4. `ModelEventPublishIntent` (event publishing coordination)

---

## Table of Contents

1. [Decision](#decision)
2. [Payload Factory Functions](#payload-factory-functions)
3. [Discriminator Naming Conventions](#discriminator-naming-conventions)
4. [Rationale](#rationale)
5. [Current State Analysis](#current-state-analysis)
6. [Implementation by Model](#implementation-by-model)
7. [Migration Strategy](#migration-strategy)
8. [Examples](#examples)
9. [Appendix: Type Safety Comparison](#appendix-type-safety-comparison)

---

## Decision

Adopt **discriminated unions with Pydantic's `Field(discriminator="...")`** pattern for all payload fields currently typed as `dict[str, Any]`.

### Key Design Choices

1. **Discriminator-first field ordering** - Place discriminator field first in models for optimal union resolution performance
2. **Annotated union aliases** - Define type aliases using `Annotated[Union[...], Field(discriminator="...")]`
3. **Closed sets for core types** - Known, finite payload types per model
4. **Open extension points** - Keep string-based routing for plugins/extensions where needed

---

## Payload Factory Functions

For runtime payload creation, the following factory functions are provided to bridge `EnumActionType` with semantic payload types:

### `create_action_payload()`

Creates typed action payloads by mapping semantic actions to the appropriate payload class:

```python
from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.orchestrator.payloads import create_action_payload

# Create a typed payload for a data operation
payload = create_action_payload(
    action_type=EnumActionType.EFFECT,
    semantic_action="read",
    target_path="/data/users.json",
    filters={"active": True},
)
# Returns ModelDataActionPayload with full type safety
```

### `get_payload_type_for_semantic_action()`

Returns the payload class for a given semantic action string:

```python
from omnibase_core.models.orchestrator.payloads.model_action_typed_payload import (
    get_payload_type_for_semantic_action,
)

payload_type = get_payload_type_for_semantic_action("read")
# Returns ModelDataActionPayload

payload_type = get_payload_type_for_semantic_action("transform")
# Returns ModelTransformationActionPayload
```

### `get_recommended_payloads_for_action_type()`

Returns the list of commonly used payload types for each `EnumActionType`:

```python
from omnibase_core.models.orchestrator.payloads import get_recommended_payloads_for_action_type

payloads = get_recommended_payloads_for_action_type(EnumActionType.COMPUTE)
# Returns [ModelTransformationActionPayload, ModelValidationActionPayload, ...]
```

**See Also**: [ModelAction Typed Payloads](./MODELACTION_TYPED_PAYLOADS.md) for comprehensive usage examples and the semantic action reference table.

---

## Discriminator Naming Conventions

The codebase uses **intentionally different discriminator field names** across payload categories for semantic clarity. This is a deliberate design choice, not an inconsistency.

### Quick Reference

| Payload Category | Discriminator Field | Pattern | Union Type |
|------------------|---------------------|---------|------------|
| **Reducer Intent Payloads** | `intent_type` | `Literal["..."]` | `ProtocolIntentPayload` (Protocol-based) |
| **Runtime Directive Payloads** | `kind` | `Literal["..."]` | `ModelDirectivePayload` |
| **Action Payloads** | `action_type` + `kind` property | `ModelNodeActionType` | `SpecificActionPayload` |
| **Core Registration Intents** | `kind` | `Literal["..."]` | `ModelCoreRegistrationIntent` |
| **Event Payloads** | `event_type` | (varies) | `ModelEventPayloadUnion` |

> **Note on Action Payloads**: Action payloads use `action_type: ModelNodeActionType` as the data field,
> with a `kind` **property** (derived from `action_type.name`) to satisfy `ProtocolActionPayload`.
>
> **Note on Reducer Intent Payloads**: Reducer Intent Payloads use a Protocol-based approach (`ProtocolIntentPayload`) rather than
> a discriminated union, enabling open extensibility for plugins. Payload classes still define an
> `intent_type` attribute for routing, but dispatch is structural (duck typing) rather than union-based.

### Rationale for Different Names

#### 1. `intent_type` (Reducer Intent Payloads)

**Location**: `src/omnibase_core/models/reducer/payloads/`

**Rationale**:
- Aligns semantically with `ModelIntent.intent_type` field
- Clearly indicates this payload describes an *intent* to perform a side effect
- The discriminator value matches what the Effect node uses for dispatch routing

**Example**:
```python
class PayloadLogEvent(ModelIntentPayloadBase):
    # Discriminator FIRST for optimal union resolution
    intent_type: Literal["log_event"] = Field(
        default="log_event",
        description="Discriminator for intent routing"
    )
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(...)
    message: str = Field(...)
```

#### 2. `kind` (Runtime Directive Payloads)

**Location**: `src/omnibase_core/models/runtime/payloads/`

**Rationale**:
- Short, unambiguous internal convention for runtime-level coordination
- Matches Kubernetes and other infrastructure patterns (e.g., `kind: Deployment`)
- Used for internal runtime signals that never leave the system boundary

**Example**:
```python
class ModelScheduleEffectPayload(ModelDirectivePayloadBase):
    kind: Literal["schedule_effect"] = "schedule_effect"
    effect_node_type: str = Field(...)
    effect_input: ModelSchemaValue | None = Field(...)
```

#### 3. `action_type` (Action Payloads)

**Locations**:
- Base payloads: `src/omnibase_core/models/core/model_action_payload*.py`
- Type alias and factory: `src/omnibase_core/models/orchestrator/payloads/model_action_typed_payload.py`

**Rationale**:
- Uses rich `ModelNodeActionType` for **semantic categorization** (not Literal)
- Enables category-based dispatch (lifecycle, data, transformation, validation, etc.)
- This is NOT a Pydantic discriminated union - uses type matching instead
- Matches the semantic action being performed, not just a type tag

**Protocol Conformance**: Action payloads satisfy `ProtocolActionPayload` via a `kind`
**property** (not a field) that returns `action_type.name`. This is implemented in
`ModelActionPayloadBase`:

```python
class ModelActionPayloadBase(BaseModel):
    action_type: ModelNodeActionType = Field(...)

    @property
    def kind(self) -> str:
        """Returns action_type.name for ProtocolActionPayload conformance."""
        return self.action_type.name
```

**Note**: Action payloads do not use the discriminated union pattern. Instead, they use
a factory function (`create_specific_action_payload` in `model_action_payload_types.py` or
`create_action_payload` in `model_action_typed_payload.py`) that selects the payload type
based on the action's semantic category.

### Performance Requirements

For **optimal O(1) discriminator lookup**, all payloads in discriminated unions MUST:

1. **Use Literal types** for the discriminator field:
   ```python
   intent_type: Literal["log_event"] = "log_event"  # Correct
   intent_type: str = "log_event"                    # Wrong - O(n) lookup
   ```

2. **Place discriminator FIRST** in the model definition:
   ```python
   class PayloadLogEvent(ModelIntentPayloadBase):
       intent_type: Literal["log_event"] = ...  # FIRST
       level: str = ...                          # Other fields after
       message: str = ...
   ```

3. **Include Field() with description** for documentation:
   ```python
   intent_type: Literal["log_event"] = Field(
       default="log_event",
       description="Discriminator literal for intent routing"
   )
   ```

### Adding New Payloads Checklist

When adding a new payload to a discriminated union:

- [ ] Define the Literal discriminator as the **FIRST field** in the model
- [ ] Use the **correct field name** for the category:
  - `intent_type` for Reducer intent payloads
  - `kind` for Runtime directive payloads
  - `action_type` for Action payloads (if using discriminated union)
- [ ] Add the payload to the appropriate **union type alias**
- [ ] Update all **Effect dispatch handlers** for exhaustive pattern matching
- [ ] Add **tests** for serialization/deserialization round-trip

---

## Rationale

### Why Discriminated Unions Over TypeVar Generics

| Aspect | Discriminated Union | TypeVar Generic |
|--------|---------------------|-----------------|
| **Pattern Matching** | Native Python `match` support | Requires isinstance checks |
| **Exhaustiveness** | Type checker warns on unhandled cases | No exhaustiveness checking |
| **Pydantic Support** | First-class with `Field(discriminator=)` | Limited, requires custom validators |
| **Serialization** | Automatic type inference on deserialize | Manual type resolution needed |
| **Documentation** | Self-documenting via union variants | Type parameter opaque at runtime |
| **IDE Support** | Full autocomplete for each variant | Generic parameter often invisible |
| **Runtime Validation** | Pydantic validates discriminator | Must validate generic type manually |

### Why NOT TypeVar Generics

```python
# TypeVar approach - compile-time type safety but runtime issues
class ModelIntent(Generic[T]):
    payload: T  # What is T at runtime? How do we deserialize?

# Problem: Deserializing JSON -> What type is payload?
intent_dict = {"intent_type": "webhook", "payload": {"url": "..."}}
ModelIntent.model_validate(intent_dict)  # T is unknown!
```

```python
# Discriminated union - self-describing at runtime
class ModelWebhookIntentPayload(BaseModel):
    intent_type: Literal["webhook.send"] = "webhook.send"
    url: str
    method: str

# Pydantic knows exactly which type from discriminator
intent_dict = {"intent_type": "webhook.send", "payload": {"intent_type": "webhook.send", "url": "..."}}
ModelIntent.model_validate(intent_dict)  # Resolves to ModelWebhookIntentPayload
```

### Proven Pattern in Codebase

The ONEX codebase already successfully uses discriminated unions:

1. **Core Intents** (`omnibase_core.models.intents`):
   ```python
   ModelCoreRegistrationIntent = Annotated[
       ModelConsulRegisterIntent
       | ModelConsulDeregisterIntent
       | ModelPostgresUpsertRegistrationIntent,
       Field(discriminator="kind"),
   ]
   ```

2. **Action Payloads** (`SpecificActionPayload`):
   ```python
   SpecificActionPayload = (
       ModelLifecycleActionPayload
       | ModelOperationalActionPayload
       | ModelDataActionPayload
       | ModelValidationActionPayload
       | ... # 10 total variants
   )
   ```

---

## Current State Analysis

### ModelIntent (Extension Intents)

**Location**: `src/omnibase_core/models/reducer/model_intent.py`

**Current Implementation**:
```python
class ModelIntent(BaseModel):
    intent_type: str  # e.g., "webhook.send", "plugin.execute"
    payload: dict[str, Any]  # <-- Target for replacement
```

**Architecture Context**:
- Two-tier intent system exists:
  - **Core Intents**: Already use discriminated union (`ModelCoreRegistrationIntent`)
  - **Extension Intents**: Generic `ModelIntent` for plugins (this model)

**Complexity**: Medium-High (23+ potential intent types from plugins)

**Recommendation**: Create `ExtensionIntentPayload` discriminated union for known extension patterns, with fallback `ModelGenericIntentPayload` for truly dynamic cases.

---

### ModelAction (Orchestrator Actions)

**Location**: `src/omnibase_core/models/orchestrator/model_action.py`

**Current Implementation**:
```python
class ModelAction(BaseModel):
    action_type: EnumActionType  # COMPUTE, EFFECT, REDUCE, ORCHESTRATE, CUSTOM
    payload: dict[str, Any]  # <-- Target for replacement
```

**Architecture Context**:
- `SpecificActionPayload` union ALREADY EXISTS with 10 typed payloads
- `EnumActionType` has 5 values: `COMPUTE`, `EFFECT`, `REDUCE`, `ORCHESTRATE`, `CUSTOM`
- Each action type has different payload requirements

**Complexity**: Low (infrastructure already in place)

**Recommendation**: Leverage existing `SpecificActionPayload` OR create `ActionPayload` union keyed on `action_type`.

---

### ModelRuntimeDirective (Internal Runtime)

**Location**: `src/omnibase_core/models/runtime/model_runtime_directive.py`

**Current Implementation**:
```python
class ModelRuntimeDirective(BaseModel):
    directive_type: EnumDirectiveType  # SCHEDULE_EFFECT, ENQUEUE_HANDLER, etc.
    payload: dict[str, Any]  # <-- Target for replacement
```

**Architecture Context**:
- INTERNAL-ONLY (never published to event bus, never in handler outputs)
- ZERO external usages (greenfield opportunity)
- 5 directive types with distinct payload schemas:
  - `SCHEDULE_EFFECT`: scheduling params
  - `ENQUEUE_HANDLER`: handler args
  - `RETRY_WITH_BACKOFF`: retry config
  - `DELAY_UNTIL`: timing params
  - `CANCEL_EXECUTION`: cancellation context

**Complexity**: Low (greenfield, small closed set)

**Recommendation**: Create `DirectivePayload` discriminated union with one variant per `EnumDirectiveType`.

---

### ModelEventPublishIntent

**Location**: `src/omnibase_core/models/events/model_event_publish_intent.py`

**Current Implementation**:
```python
class ModelEventPublishIntent(BaseModel):
    target_event_type: str  # Event type name for routing
    target_event_payload: dict[str, Any]  # <-- Target for replacement
```

**Architecture Context**:
- Coordinates event publishing to Kafka
- 23+ event classes exist as Pydantic models in `models/events/`
- Events already have their own typed schemas

**Complexity**: Medium (many event types, but all are Pydantic models)

**Recommendation**: Create `EventPayload` discriminated union referencing existing event models, keyed on `target_event_type`.

---

## Implementation by Model

### 1. ModelIntent

**Discriminator Field**: `intent_type` (existing)

**Payload Field**: `payload` -> `ProtocolIntentPayload` (Protocol-based)

> **See**: [Discriminator Naming Conventions](#discriminator-naming-conventions) for why
> Extension Intent payloads use `intent_type` instead of `kind`.

**Current Implementation** (Protocol-based):

ModelIntent uses a Protocol-based approach (`ProtocolIntentPayload`) rather than a
discriminated union, enabling open extensibility for plugins while maintaining type safety:

```python
from omnibase_core.models.reducer.payloads import ProtocolIntentPayload

class ModelIntent(BaseModel):
    intent_type: str  # Routing key (e.g., "log_event", "notify")
    payload: ProtocolIntentPayload  # Protocol-typed payload
```

Payload classes define an `intent_type` attribute for routing, enabling structural
pattern matching in Effect nodes:

```python
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent, ModelPayloadNotify

# Create intent with typed payload
intent = ModelIntent(
    intent_type="log_event",
    target="logging",
    payload=ModelPayloadLogEvent(
        level="INFO",
        message="Operation completed",
        context={"duration_ms": 125},
    ),
)

# Structural pattern matching in Effect
def handle_payload(payload: ProtocolIntentPayload) -> None:
    match payload:
        case ModelPayloadLogEvent():
            log(payload.level, payload.message)
        case ModelPayloadNotify():
            notify(payload.channel, payload.message)
```

**Alternative Approach** (Discriminated Union - for closed sets):

For scenarios requiring exhaustive handling guarantees, a discriminated union can be used:

```python
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field

class ModelWebhookIntentPayload(BaseModel):
    intent_type: Literal["webhook.send"] = "webhook.send"
    url: str
    method: str = "POST"
    body: dict[str, Any] | None = None  # Optional request body

ExtensionIntentPayload = Annotated[
    ModelWebhookIntentPayload | ModelPluginExecutePayload,
    Field(discriminator="intent_type"),
]
```

**Migration Path**: Deprecate raw `dict[str, Any]`, add adapter methods during transition.

---

### 2. ModelAction

**Discriminator Field**: `action_type` (existing `EnumActionType`)

**Payload Field**: `payload` -> `ActionPayload`

**Approach A** (Leverage existing `SpecificActionPayload`):
```python
from omnibase_core.models.core.model_action_payload_types import SpecificActionPayload

class ModelAction(BaseModel):
    action_type: EnumActionType
    payload: SpecificActionPayload | None = None  # Use existing union
```

**Approach B** (Hypothetical - Create action-type-specific discriminated union):

> **Note**: This is a **hypothetical alternative** NOT currently implemented.
> The actual implementation uses Approach A with `SpecificActionPayload`.
> If implementing this pattern, use `kind` as the discriminator to satisfy
> `ProtocolActionPayload`, which requires a `kind` property/attribute.

```python
# Hypothetical alternative - NOT currently implemented
class ModelComputeActionPayload(BaseModel):
    kind: Literal["compute"] = "compute"  # Discriminator for ProtocolActionPayload
    node_id: str
    input_data: dict[str, Any]

class ModelEffectActionPayload(BaseModel):
    kind: Literal["effect"] = "effect"
    effect_type: str
    params: dict[str, Any]

# ... other variants

ActionPayload = Annotated[
    ModelComputeActionPayload
    | ModelEffectActionPayload
    | ModelReduceActionPayload
    | ModelOrchestrateActionPayload
    | ModelCustomActionPayload,
    Field(discriminator="kind"),  # Uses 'kind' to satisfy ProtocolActionPayload
]
```

**Recommendation**: Approach A (leverage existing infrastructure).

---

### 3. ModelRuntimeDirective

**Discriminator Field**: `directive_type` (existing `EnumDirectiveType`)

**Payload Field**: `payload` -> `DirectivePayload`

**Approach**:
```python
from typing import Literal

class ModelScheduleEffectPayload(BaseModel):
    kind: Literal["schedule_effect"] = "schedule_effect"
    effect_id: str
    schedule_at: datetime
    priority: int = 5

class ModelEnqueueHandlerPayload(BaseModel):
    kind: Literal["enqueue_handler"] = "enqueue_handler"
    handler_id: str
    args: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}

class ModelRetryWithBackoffPayload(BaseModel):
    kind: Literal["retry_with_backoff"] = "retry_with_backoff"
    max_attempts: int = 3
    initial_delay_ms: int = 1000
    multiplier: float = 2.0
    max_delay_ms: int = 30000

class ModelDelayUntilPayload(BaseModel):
    kind: Literal["delay_until"] = "delay_until"
    until: datetime
    reason: str | None = None

class ModelCancelExecutionPayload(BaseModel):
    kind: Literal["cancel_execution"] = "cancel_execution"
    execution_id: str
    reason: str
    force: bool = False

DirectivePayload = Annotated[
    ModelScheduleEffectPayload
    | ModelEnqueueHandlerPayload
    | ModelRetryWithBackoffPayload
    | ModelDelayUntilPayload
    | ModelCancelExecutionPayload,
    Field(discriminator="kind"),
]

class ModelRuntimeDirective(BaseModel):
    directive_type: EnumDirectiveType
    payload: DirectivePayload
```

**Note**: The `kind` discriminator will align with the `EnumDirectiveType` value for consistency.

---

### 4. ModelEventPublishIntent

**Discriminator Field**: `target_event_type` (existing)

**Payload Field**: `target_event_payload` -> `EventPayload`

**Approach**:
```python
from omnibase_core.models.events import (
    ModelNodeRegisteredEvent,
    ModelNodeUnregisteredEvent,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    # ... other event types
)

# Each event already has event_type as a class attribute
# Add discriminator if not present

EventPayload = Annotated[
    ModelNodeRegisteredEvent
    | ModelNodeUnregisteredEvent
    | ModelRuntimeReadyEvent
    | ModelSubscriptionCreatedEvent
    | ModelWiringResultEvent
    | ModelWiringErrorEvent
    # ... all 23+ event types
    | ModelGenericEventPayload,  # Fallback for custom events
    Field(discriminator="event_type"),
]

class ModelEventPublishIntent(BaseModel):
    target_event_type: str
    target_event_payload: EventPayload
```

**Alternative**: If event models don't have discriminator, add `event_type: Literal[...]` to each.

---

## Migration Strategy

### Phase 1: Add Discriminated Union Types (Non-Breaking)

1. Create payload model files:
   - `model_extension_intent_payloads.py`
   - `model_directive_payloads.py`
   - `model_event_payloads.py`

2. Define discriminated unions as type aliases

3. Add `@deprecated` decorator to `dict[str, Any]` fields

4. Add adapter methods for backwards compatibility:
   ```python
   @classmethod
   def from_dict_payload(cls, payload: dict[str, Any]) -> Self:
       """Migration helper - converts untyped dict to typed payload."""
       ...
   ```

### Phase 2: Dual-Accept Transition Period

1. Update model fields to accept both:
   ```python
   payload: ExtensionIntentPayload | dict[str, Any] = Field(...)
   ```

2. Add runtime migration in validators:
   ```python
   @field_validator("payload", mode="before")
   @classmethod
   def migrate_dict_payload(cls, v):
       # NOTE: The discriminator field name varies by model category:
       #   - ModelIntent payloads: "intent_type"
       #   - ModelRuntimeDirective payloads: "kind"
       #   - ModelAction payloads: "action_type"
       # This example uses "intent_type" for ModelIntent:
       if isinstance(v, dict) and "intent_type" not in v:
           # Infer and convert to typed payload
           return infer_payload_type(v)
       return v
   ```

3. Emit deprecation warnings for dict usage

### Phase 3: Remove dict[str, Any] Support

1. Remove dual-accept, require typed payloads
2. Update all callers
3. Remove migration adapters
4. Remove `@allow_dict_str_any` decorators

### Timeline

| Phase | Duration | Milestone |
|-------|----------|-----------|
| Phase 1 | 1-2 sprints | Types defined, adapters available |
| Phase 2 | 2-3 sprints | All new code uses typed payloads |
| Phase 3 | Post-v0.4.0 | Full migration complete |

---

## Examples

### Before: Untyped ModelIntent

```python
# Creating an intent (no type safety)
intent = ModelIntent(
    intent_type="webhook.send",
    target="notifications",
    payload={
        "url": "https://api.example.com/webhook",
        "method": "POST",
        "body": {"event": "user_created", "user_id": 123},
    },
)

# Consuming (manual type checking, error-prone)
def handle_intent(intent: ModelIntent) -> None:
    if intent.intent_type == "webhook.send":
        url = intent.payload.get("url")  # May be None, no autocomplete
        if url is None:
            raise ValueError("Missing url")
        # ... more manual validation
```

### After: Typed ModelIntent

```python
# Creating an intent (full type safety)
intent = ModelIntent(
    intent_type="webhook.send",
    target="notifications",
    payload=ModelWebhookIntentPayload(
        url="https://api.example.com/webhook",
        method="POST",
        body={"event": "user_created", "user_id": 123},
    ),
)

# Consuming (pattern matching, exhaustive)
def handle_intent(intent: ModelIntent) -> None:
    match intent.payload:
        case ModelWebhookIntentPayload() as webhook:
            # Full autocomplete: webhook.url, webhook.method, webhook.body
            send_webhook(webhook.url, webhook.method, webhook.body)
        case ModelPluginExecutePayload() as plugin:
            execute_plugin(plugin.plugin_id, plugin.action, plugin.params)
        case ModelGenericIntentPayload() as generic:
            handle_generic(generic.data)
        # Type checker warns if we miss a variant!
```

### Before: Untyped ModelRuntimeDirective

```python
directive = ModelRuntimeDirective(
    directive_type=EnumDirectiveType.RETRY_WITH_BACKOFF,
    correlation_id=uuid4(),
    payload={
        "max_attempts": 3,
        "initial_delay": 1000,  # Wrong key name!
        "multiplier": 2.0,
    },
)

# Runtime error when accessing wrong key
delay = directive.payload["initial_delay_ms"]  # KeyError!
```

### After: Typed ModelRuntimeDirective

```python
directive = ModelRuntimeDirective(
    directive_type=EnumDirectiveType.RETRY_WITH_BACKOFF,
    correlation_id=uuid4(),
    payload=ModelRetryWithBackoffPayload(
        max_attempts=3,
        initial_delay_ms=1000,  # Correct field, validated at construction
        multiplier=2.0,
    ),
)

# Type-safe access
delay = directive.payload.initial_delay_ms  # Autocomplete, type-checked
```

---

## Appendix: Type Safety Comparison

### Error Detection Timeline

| Error Type | `dict[str, Any]` | Discriminated Union |
|------------|------------------|---------------------|
| Missing required field | Runtime (KeyError) | Construction time |
| Wrong field name | Runtime (silent None) | Construction time |
| Wrong field type | Runtime (downstream) | Construction time |
| Unhandled variant | Never (silent) | Compile time (mypy) |
| Invalid enum value | Runtime | Construction time |

### Code Quality Metrics

| Metric | `dict[str, Any]` | Discriminated Union |
|--------|------------------|---------------------|
| Lines of validation code | 10-20 per handler | 0 (Pydantic handles) |
| Test coverage needed | High (many edge cases) | Lower (type system covers) |
| IDE autocomplete | None | Full |
| Refactoring safety | Low | High |
| Documentation accuracy | Manual, can drift | Self-documenting |

---

## References

- [Pydantic Discriminated Unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions)
- [ONEX Four-Node Architecture](./ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Core Intents Implementation](../../src/omnibase_core/models/intents/__init__.py)
- [SpecificActionPayload Union](../../src/omnibase_core/models/core/model_action_payload_types.py)
