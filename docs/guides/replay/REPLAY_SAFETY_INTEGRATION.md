> **Navigation**: [Home](../../index.md) > [Guides](../README.md) > Replay > Replay Safety Integration

# Replay Safety Integration Guide

## Overview

This guide explains how to integrate the `ServiceReplaySafetyEnforcer` into your ONEX pipeline for deterministic replay of non-deterministic effects. The replay safety system ensures that effects like time, random numbers, UUIDs, and external API calls behave predictably during testing and CI.

**Key Takeaway**: Use replay safety enforcement to guarantee deterministic pipeline execution, enabling reliable testing and reproducible debugging.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Enforcement Modes](#enforcement-modes)
3. [Basic Setup](#basic-setup)
4. [Recording and Replaying Effects](#recording-and-replaying-effects)
5. [Using the Audit Trail](#using-the-audit-trail)
6. [Pipeline Integration Patterns](#pipeline-integration-patterns)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)
9. [Data Privacy](#data-privacy)

## System Architecture

The replay safety system consists of three main components:

```
                          ServiceReplaySafetyEnforcer
                                     |
           +-------------------------+-------------------------+
           |                         |                         |
    InjectorTime            InjectorRNG              InjectorUUID
    (time effects)         (random effects)         (uuid effects)
           |                         |                         |
           +-----------+-------------+-----------+-------------+
                       |                         |
                RecorderEffect              ServiceAuditTrail
              (network/db effects)          (decision tracking)
```

### Component Responsibilities

| Component | Purpose | Thread-Safe? |
|-----------|---------|--------------|
| `ServiceReplaySafetyEnforcer` | Classifies effects and applies enforcement policy | No |
| `InjectorTime` | Provides deterministic time values | Yes |
| `InjectorRNG` | Provides seeded random number generation | No |
| `InjectorUUID` | Provides deterministic UUID generation | No |
| `RecorderEffect` | Records and replays external effect results | No |
| `ServiceAuditTrail` | Tracks all enforcement decisions | No |

## Enforcement Modes

The enforcer supports four modes, each appropriate for different contexts:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **STRICT** | Raises `ModelOnexError` on non-deterministic effects | CI/testing environments |
| **WARN** | Logs warning but continues execution | Gradual migration to replay safety |
| **PERMISSIVE** | Allows with full audit trail | Production with monitoring |
| **MOCKED** | Injects deterministic mock values automatically | Testing with automatic stubbing |

### Mode Selection Guide

```python
from omnibase_core.enums.replay import EnumEnforcementMode

# For CI/CD pipelines - fail fast on non-determinism
mode = EnumEnforcementMode.STRICT

# For migration - identify issues without breaking execution
mode = EnumEnforcementMode.WARN

# For production - allow execution but track everything
mode = EnumEnforcementMode.PERMISSIVE

# For unit tests - automatically mock non-deterministic effects
mode = EnumEnforcementMode.MOCKED
```

## Basic Setup

### Minimal Setup (Strict Mode for CI)

```python
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)
from omnibase_core.enums.replay import EnumEnforcementMode

# Create enforcer in strict mode - blocks all non-deterministic effects
enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.STRICT)

# Check an effect before execution
decision = enforcer.enforce("compute.hash")  # Allowed - deterministic
print(f"Decision: {decision.decision}")  # "allowed"

# This would raise ModelOnexError in strict mode:
# decision = enforcer.enforce("time.now")  # Blocked - non-deterministic
```

### Full Setup with All Injectors

```python
from datetime import datetime, timezone
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)
from omnibase_core.services.replay.injector_time import InjectorTime
from omnibase_core.services.replay.injector_rng import InjectorRNG
from omnibase_core.services.replay.injector_uuid import InjectorUUID
from omnibase_core.services.replay.recorder_effect import RecorderEffect
from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
from omnibase_core.enums.replay import EnumEnforcementMode, EnumRecorderMode

# Create injectors for deterministic values
time_injector = InjectorTime(
    fixed_time=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
)
rng_injector = InjectorRNG(seed=42)
uuid_injector = InjectorUUID(mode=EnumRecorderMode.RECORDING)

# Create effect recorder for network/database effects
effect_recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)

# Create the enforcer with all components
enforcer = ServiceReplaySafetyEnforcer(
    mode=EnumEnforcementMode.MOCKED,
    time_injector=time_injector,
    rng_injector=rng_injector,
    uuid_injector=uuid_injector,
    effect_recorder=effect_recorder,
)

# Create audit trail for tracking
audit_trail = ServiceAuditTrail()
```

## Recording and Replaying Effects

### Recording Phase

During the initial execution, record all non-deterministic values:

```python
from omnibase_core.services.replay.injector_time import InjectorTime
from omnibase_core.services.replay.injector_rng import InjectorRNG
from omnibase_core.services.replay.injector_uuid import InjectorUUID
from omnibase_core.services.replay.recorder_effect import RecorderEffect
from omnibase_core.enums.replay import EnumRecorderMode

# Recording mode - captures values as they're generated
rng_injector = InjectorRNG(seed=None)  # Auto-generates secure seed
uuid_injector = InjectorUUID(mode=EnumRecorderMode.RECORDING)
effect_recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)

# Execute your pipeline
random_value = rng_injector.random()
generated_uuid = uuid_injector.uuid4()

# Record an external API call result
effect_recorder.record(
    effect_type="http.get",
    intent={"url": "https://api.example.com/data", "headers": {}},
    result={"status_code": 200, "body": {"key": "value"}},
    success=True,
)

# After execution, save recorded data for replay
recorded_data = {
    "rng_seed": rng_injector.seed,
    "uuids": [str(u) for u in uuid_injector.get_recorded()],
    "effects": [r.model_dump(mode="json") for r in effect_recorder.get_all_records()],
}
print(f"Recorded: {recorded_data}")
```

### Replay Phase

During replay, restore the recorded values:

```python
from uuid import UUID
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

# Load recorded data (from previous execution)
# recorded_data = load_from_manifest()

# Recreate injectors with recorded values
rng_injector = InjectorRNG(seed=recorded_data["rng_seed"])
uuid_injector = InjectorUUID(
    mode=EnumRecorderMode.REPLAYING,
    recorded_uuids=[UUID(u) for u in recorded_data["uuids"]],
)

# Recreate effect recorder with recorded results
records = [ModelEffectRecord(**r) for r in recorded_data["effects"]]
effect_recorder = RecorderEffect(
    mode=EnumRecorderMode.REPLAYING,
    records=records,
)

# Now executing the same pipeline produces identical results
replayed_random = rng_injector.random()  # Same as original
replayed_uuid = uuid_injector.uuid4()    # Same as original

# Replay external API call result
replayed_result = effect_recorder.require_replay_result(
    effect_type="http.get",
    intent={"url": "https://api.example.com/data", "headers": {}},
)
# replayed_result == {"status_code": 200, "body": {"key": "value"}}
```

## Using the Audit Trail

### Recording Decisions

The `ServiceAuditTrail` provides comprehensive tracking of all enforcement decisions:

```python
from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)
from omnibase_core.enums.replay import EnumEnforcementMode

# Create audit trail and enforcer
audit_trail = ServiceAuditTrail()
enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)

# Enforce several effects
for effect_type in ["time.now", "compute.hash", "http.get", "random.randint"]:
    decision = enforcer.enforce(effect_type)
    # Record each decision in the audit trail with context
    audit_trail.record(
        decision=decision,
        context={"handler": "my_pipeline", "step": effect_type},
    )
```

### Querying the Audit Trail

```python
from omnibase_core.enums.replay import EnumNonDeterministicSource

# Get all entries
all_entries = audit_trail.get_entries()
print(f"Total decisions: {len(all_entries)}")

# Query by outcome
allowed = audit_trail.get_entries(outcome="allowed")
blocked = audit_trail.get_entries(outcome="blocked")
warned = audit_trail.get_entries(outcome="warned")

# Query by source type
time_decisions = audit_trail.get_entries(
    source=EnumNonDeterministicSource.TIME
)
network_decisions = audit_trail.get_entries(
    source=EnumNonDeterministicSource.NETWORK
)

# Get with limit
recent = audit_trail.get_entries(limit=10)
```

### Getting Summary Statistics

```python
summary = audit_trail.get_summary()

print(f"Session ID: {summary.session_id}")
print(f"Total decisions: {summary.total_decisions}")
print(f"Decisions by outcome: {summary.decisions_by_outcome}")
print(f"Decisions by source: {summary.decisions_by_source}")
print(f"Blocked effects: {summary.blocked_effects}")
print(f"First decision: {summary.first_decision_at}")
print(f"Last decision: {summary.last_decision_at}")
```

### Exporting for Debugging

```python
import json

# Export as JSON for debugging or compliance
json_output = audit_trail.export_json()

# Parse and analyze
data = json.loads(json_output)
print(f"Session: {data['session_id']}")
print(f"Entries: {len(data['entries'])}")
```

## Pipeline Integration Patterns

### Pattern 1: Test Fixture with Enforcer

```python
import pytest
from datetime import datetime, timezone
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)
from omnibase_core.services.replay.injector_time import InjectorTime
from omnibase_core.services.replay.injector_rng import InjectorRNG
from omnibase_core.services.replay.injector_uuid import InjectorUUID
from omnibase_core.enums.replay import EnumEnforcementMode, EnumRecorderMode

@pytest.fixture
def replay_safe_enforcer():
    """Fixture providing a fully configured enforcer for deterministic tests."""
    time_injector = InjectorTime(
        fixed_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    rng_injector = InjectorRNG(seed=12345)
    uuid_injector = InjectorUUID(mode=EnumRecorderMode.PASS_THROUGH)

    return ServiceReplaySafetyEnforcer(
        mode=EnumEnforcementMode.STRICT,
        time_injector=time_injector,
        rng_injector=rng_injector,
        uuid_injector=uuid_injector,
    )

def test_deterministic_pipeline(replay_safe_enforcer):
    """Test that pipeline only uses deterministic effects."""
    enforcer = replay_safe_enforcer

    # All compute effects should be allowed
    decision = enforcer.enforce("compute.transform")
    assert decision.decision == "allowed"

    # Non-deterministic effects would raise in strict mode
    # This validates the pipeline is replay-safe
```

### Pattern 2: Context Manager for Pipeline Execution

```python
from contextlib import contextmanager
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)
from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
from omnibase_core.enums.replay import EnumEnforcementMode

@contextmanager
def replay_safe_context(mode: EnumEnforcementMode = EnumEnforcementMode.STRICT):
    """Context manager for replay-safe pipeline execution."""
    enforcer = ServiceReplaySafetyEnforcer(mode=mode)
    audit_trail = ServiceAuditTrail()

    try:
        yield enforcer, audit_trail
    finally:
        # Log summary after execution
        summary = audit_trail.get_summary()
        if summary.blocked_effects:
            print(f"Blocked effects: {summary.blocked_effects}")

# Usage
with replay_safe_context(EnumEnforcementMode.WARN) as (enforcer, audit_trail):
    # Execute pipeline with replay safety tracking
    decision = enforcer.enforce("time.now")
    audit_trail.record(decision, context={"step": "get_timestamp"})
```

### Pattern 3: DI Container Integration

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)
from omnibase_core.services.replay.injector_time import InjectorTime
from omnibase_core.services.replay.injector_rng import InjectorRNG
from omnibase_core.enums.replay import EnumEnforcementMode


def configure_replay_services(container: ModelONEXContainer, mode: EnumEnforcementMode):
    """Configure replay services in the DI container."""
    # Register time service
    time_injector = InjectorTime()  # Production mode
    container.register_service("ProtocolTimeService", time_injector)

    # Register RNG service
    rng_injector = InjectorRNG()  # Auto-seeded for production
    container.register_service("ProtocolRNGService", rng_injector)

    # Register enforcer
    enforcer = ServiceReplaySafetyEnforcer(
        mode=mode,
        time_injector=time_injector,
        rng_injector=rng_injector,
    )
    container.register_service("ProtocolReplaySafetyEnforcer", enforcer)

    return container
```

## Troubleshooting

### What to Do When Strict Mode Blocks an Effect

When strict mode blocks a non-deterministic effect, you'll see an error like:

```
ModelOnexError: Non-deterministic effect 'time.now' (time) blocked in strict mode
  error_code: REPLAY_ENFORCEMENT_BLOCKED
  effect_type: time.now
  source: time
  mode: strict
```

**Resolution Steps:**

1. **Identify the effect source** - Check the `source` field (time, random, uuid, network, etc.)

2. **Inject the appropriate service** - Use the corresponding injector:
   ```python
   # For time effects
   from omnibase_core.services.replay.injector_time import InjectorTime
   time_svc = InjectorTime(fixed_time=datetime.now(timezone.utc))

   # For random effects
   from omnibase_core.services.replay.injector_rng import InjectorRNG
   rng_svc = InjectorRNG(seed=42)

   # For UUID effects
   from omnibase_core.services.replay.injector_uuid import InjectorUUID
   uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
   ```

3. **Update your pipeline** to use the injected service instead of direct calls:
   ```python
   # Instead of:
   timestamp = datetime.now()

   # Use:
   timestamp = time_injector.now()
   ```

### How to Migrate from WARN to STRICT Mode

1. **Start with WARN mode** in production to collect data:
   ```python
   enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.WARN)
   ```

2. **Monitor the audit trail** for warnings:
   ```python
   summary = audit_trail.get_summary()
   print(f"Warned effects: {summary.decisions_by_outcome.get('warned', 0)}")
   ```

3. **Address each warned effect type**:
   - Replace direct `datetime.now()` calls with `InjectorTime`
   - Replace `random.random()` calls with `InjectorRNG`
   - Replace `uuid.uuid4()` calls with `InjectorUUID`
   - Record external API calls with `RecorderEffect`

4. **Switch to STRICT mode** once no warnings are generated:
   ```python
   enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.STRICT)
   ```

### Debugging Replay Mismatches Using Audit Trail

When replay produces different results than recording:

1. **Export both audit trails**:
   ```python
   # After recording
   recording_json = recording_audit_trail.export_json()

   # After replay
   replay_json = replay_audit_trail.export_json()
   ```

2. **Compare sequence numbers** - Each decision has a sequence number:
   ```python
   import json

   recording_data = json.loads(recording_json)
   replay_data = json.loads(replay_json)

   for rec, rep in zip(recording_data['entries'], replay_data['entries']):
       if rec['decision']['effect_type'] != rep['decision']['effect_type']:
           print(f"Mismatch at sequence {rec['sequence_number']}")
           print(f"  Recording: {rec['decision']['effect_type']}")
           print(f"  Replay: {rep['decision']['effect_type']}")
   ```

3. **Check for missing records** - Verify all effects are recorded:
   ```python
   # If replay fails with REPLAY_RECORD_NOT_FOUND
   # The error context includes helpful debugging info:
   # - effect_type: What was requested
   # - intent_keys: Keys in the intent dict
   # - available_effect_types: What types are recorded
   # - total_records: How many records exist
   ```

4. **Reset injectors between runs**:
   ```python
   # Reset UUID injector to replay from beginning
   uuid_injector.reset()

   # Reset effect recorder sequence
   # (Create new instance with same records)
   ```

### Common Error Codes

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `REPLAY_ENFORCEMENT_BLOCKED` | Non-deterministic effect blocked in strict mode | Inject appropriate service |
| `REPLAY_SEQUENCE_EXHAUSTED` | More UUIDs requested than recorded | Ensure recording captures all UUID calls |
| `REPLAY_RECORD_NOT_FOUND` | No matching effect record for replay | Verify intent matches exactly |
| `REPLAY_NOT_IN_REPLAY_MODE` | Called `require_replay_result` outside replay mode | Check recorder mode |
| `REPLAY_INVALID_EFFECT_TYPE` | Empty effect type provided | Ensure effect_type is non-empty |

## Best Practices

### 1. Use STRICT Mode in CI/CD

```python
# In CI configuration or test setup
import os
from omnibase_core.enums.replay import EnumEnforcementMode

def get_enforcement_mode() -> EnumEnforcementMode:
    """Get enforcement mode based on environment."""
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return EnumEnforcementMode.STRICT
    return EnumEnforcementMode.WARN
```

### 2. Always Record Seeds

```python
# Record seeds in execution manifest
manifest = {
    "rng_seed": rng_injector.seed,
    "recorded_at": time_injector.now().isoformat(),
    "uuids": uuid_injector.get_recorded(),
}
```

### 3. Use Thread-Local Instances

Since most replay components are NOT thread-safe:

```python
import threading

thread_local = threading.local()

def get_enforcer() -> ServiceReplaySafetyEnforcer:
    """Get thread-local enforcer instance."""
    if not hasattr(thread_local, 'enforcer'):
        thread_local.enforcer = ServiceReplaySafetyEnforcer(
            mode=EnumEnforcementMode.PERMISSIVE
        )
    return thread_local.enforcer
```

### 4. Reset Between Test Cases

```python
@pytest.fixture(autouse=True)
def reset_replay_state(replay_enforcer):
    """Reset replay state between tests."""
    yield
    replay_enforcer.reset()
```

### 5. Document Non-Deterministic Dependencies

```python
class MyEffectNode(NodeEffect):
    """
    Effect node that makes external API calls.

    Replay Safety:
        - Uses InjectorTime for timestamps (effect: time.now)
        - Records HTTP responses (effect: http.get)
        - Requires seed in manifest for RNG (effect: random.choice)
    """
    pass
```

## Data Privacy

When recording enforcement decisions in the audit trail, be mindful of data sensitivity. The `context` and `effect_metadata` dictionaries can inadvertently capture sensitive information.

### Avoid Including in `context` or `effect_metadata`

- **Passwords or Authentication Tokens**: Never log credentials
- **Personal Identifiable Information (PII)**: Names, emails, phone numbers, addresses
- **API Keys or Secrets**: Use masked values or omit entirely
- **Financial Data**: Credit card numbers, bank accounts
- **Health Information**: PHI/HIPAA protected data

### Recommended Practices

#### 1. Use Sanitized Identifiers

```python
# Wrong - exposes PII
context={"user_email": "john.doe@example.com"}

# Correct - use hashed/anonymized ID
context={"user_id": "usr_abc123", "user_hash": hash_pii(email)}
```

#### 2. Mask Sensitive Values

```python
# Wrong - exposes API key
effect_metadata={"api_key": "sk-1234567890abcdef"}

# Correct - mask sensitive data
effect_metadata={"api_key": "sk-****cdef"}
```

#### 3. Use Reference IDs Instead of Data

```python
# Wrong - logs actual request body with credentials
context={"request_body": {"password": "secret123"}}

# Correct - reference only
context={"request_id": "req_xyz789", "request_type": "auth"}
```

#### 4. Consider Audit Trail Retention

- Set `max_entries` to limit data retention
- Implement periodic purging for compliance (GDPR, CCPA)
- Export to secure, encrypted storage for long-term retention

```python
# Limit audit trail size
audit_trail = ServiceAuditTrail(max_entries=10000)

# Clear when no longer needed
audit_trail.clear()
```

### Compliance Notes

| Regulation | Requirement |
|------------|-------------|
| **GDPR** | Audit trails containing EU citizen data must comply with right-to-erasure |
| **HIPAA** | Health-related effect metadata requires additional safeguards |
| **SOC 2** | Audit trail access should be logged and monitored |
| **CCPA** | California residents can request deletion of personal data |

### Example: Safe Audit Trail Recording

```python
from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail

def record_decision_safely(
    audit_trail: ServiceAuditTrail,
    decision,
    user_id: str,
    request_id: str,
) -> None:
    """Record decision with sanitized context - no PII exposure."""
    audit_trail.record(
        decision=decision,
        context={
            # Safe: Use opaque identifiers
            "user_id": user_id,
            "request_id": request_id,
            # Safe: Include non-sensitive metadata
            "handler": "payment_processor",
            "step": "validate_card",
            # Avoid: Never include actual card numbers, emails, names
        },
    )
```

## Related Documentation

- [THREADING.md](../THREADING.md) - Thread safety patterns
- [Node Building Guide](../node-building/README.md) - Node architecture
- [Effect Node Tutorial](../node-building/04_EFFECT_NODE_TUTORIAL.md) - Effect patterns

## Version History

- **v0.6.3**: Initial release of replay safety enforcement (OMN-1150)
- **v0.4.0**: Replay infrastructure foundation (OMN-1116)
