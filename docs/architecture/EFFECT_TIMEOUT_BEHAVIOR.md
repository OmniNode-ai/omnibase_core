# Effect Timeout Behavior

> **Version**: 1.0.0
> **Status**: Documentation
> **Scope**: omnibase_core
> **Last Updated**: 2025-12-09
> **Related**: [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](CONTRACT_DRIVEN_NODEEFFECT_V1_0.md), [THREADING.md](../guides/THREADING.md)

---

## Overview

This document explains when and how timeouts are checked during effect execution in `NodeEffect` and `MixinEffectExecution`. Understanding this behavior is critical for:

- Setting appropriate timeout values
- Debugging timeout-related issues
- Understanding actual execution time vs configured timeout

**Key Insight**: Timeouts are checked **at the start of each retry attempt**, not during operation execution. This means long-running operations may complete even if they exceed the timeout threshold.

---

## Timeout Check Points

```text
+---------------------------------------------------------------------+
|                    Effect Execution Timeline                        |
+---------------------------------------------------------------------+
|                                                                      |
|  Start --> [CHECK TIMEOUT] --> Execute Operation --> Success? -->   |
|              ^                        |                    |         |
|              |                        |                   Yes        |
|              |                        v                    |         |
|              |                      Fail                   v         |
|              |                        |                 Return       |
|              |                        v                              |
|              |                  Retry Needed?                        |
|              |                        |                              |
|              |                       Yes                             |
|              |                        |                              |
|              +-------- Wait (backoff) <--+                           |
|                                                                      |
+---------------------------------------------------------------------+

Legend:
  [CHECK TIMEOUT] = Timeout validation occurs HERE (before each attempt)
  Execute Operation = Handler runs (HTTP call, DB query, etc.)
  Wait (backoff) = Exponential delay with jitter before next retry attempt
```

### Detailed Sequence Diagram

```text
Time
  |
  v
+------------------+
| START            |
+--------+---------+
         |
         v
+------------------+
| Record start_time|
+--------+---------+
         |
         v
+==================+
| RETRY LOOP       |  <-- for attempt in range(max_retries + 1)
+==================+
         |
         v
+------------------+
| Calculate        |
| elapsed_ms       |  <-- (time.time() - start_time) * 1000
+--------+---------+
         |
         v
+------------------+
| elapsed_ms >=    |
| timeout_ms?      |  <-- [TIMEOUT CHECK POINT]
+--------+---------+
    |         |
   Yes        No
    |         |
    v         v
+-------+  +------------------+
| RAISE |  | Check Circuit    |
|TIMEOUT|  | Breaker State    |
+-------+  +--------+---------+
                    |
                    v
           +------------------+
           | Circuit Breaker  |
           | Open?            |
           +--------+---------+
               |         |
              Yes        No
               |         |
               v         v
           +-------+  +------------------+
           | RAISE |  | Execute Handler  |  <-- Handler runs to completion
           | OPEN  |  | (HTTP/DB/etc.)   |      (no interruption)
           +-------+  +--------+---------+
                               |
                               v
                      +------------------+
                      | Success?         |
                      +--------+---------+
                          |         |
                         Yes        No
                          |         |
                          v         v
                      +-------+  +------------------+
                      |RETURN |  | Record Failure   |
                      |SUCCESS|  | Update Circuit   |
                      +-------+  +--------+---------+
                                          |
                                          v
                                 +------------------+
                                 | Retries Left?    |
                                 +--------+---------+
                                     |         |
                                    Yes        No
                                     |         |
                                     v         v
                                 +-------+  +-------+
                                 | WAIT  |  | RAISE |
                                 |(backoff) | ERROR |
                                 +---+---+  +-------+
                                     |
                                     +---> Back to RETRY LOOP
```

---

## Key Behaviors

### 1. Pre-Execution Check

Timeout is validated **BEFORE** each attempt starts:

```python
# From MixinEffectExecution._execute_with_retry()
for attempt in range(max_retries + 1):
    # Check overall timeout FIRST
    elapsed_ms = (time.time() - start_time) * 1000
    if elapsed_ms >= operation_timeout_ms:
        raise ModelOnexError(
            message=f"Operation timeout after {elapsed_ms:.0f}ms",
            error_code=EnumCoreErrorCode.TIMEOUT_EXCEEDED,
            context={...}
        )

    # THEN execute the operation
    result = await self._execute_operation(resolved_context, input_data)
```

### 2. No Mid-Operation Interruption

Once an operation starts executing (e.g., HTTP call begins), it runs to completion. The timeout mechanism does **NOT** interrupt in-flight operations.

**Why?** Interrupting operations mid-execution can leave resources in inconsistent states:
- HTTP connections may leak
- Database transactions may remain open
- Kafka messages may be partially sent
- File operations may result in corrupt files

### 3. Handler Responsibility

Individual handlers (HTTP, DB, Kafka, Filesystem) may implement their own internal timeouts. These are **separate** from the operation-level timeout:

| Timeout Type | Location | Purpose |
|--------------|----------|---------|
| **Operation Timeout** | `operation_timeout_ms` | Guards overall operation including retries |
| **Handler Timeout** | `io_config.timeout_ms` | Guards individual handler execution |

For example, `ModelHttpIOConfig.timeout_ms` (default: 30000ms) controls the HTTP client timeout, while `operation_timeout_ms` controls the overall retry loop.

---

## Implications

### Long-Running Operations

If an operation takes longer than the configured timeout:

1. The operation **will complete** (no interruption)
2. Subsequent retry attempts **will be blocked** (timeout check fails)
3. Success is returned if the long operation succeeded

**Example**: With `operation_timeout_ms=5000` and an HTTP call taking 6000ms:
- The HTTP call completes successfully after 6000ms
- If success, result is returned (no timeout error)
- If failure, timeout would trigger on next retry attempt

### Total Time May Exceed Timeout

The actual total execution time may exceed the configured timeout due to in-flight operations:

```text
Configured timeout: 10000ms

Actual timeline:
  0ms:     Check timeout (OK, elapsed=0ms) -> Start HTTP call
  12000ms: HTTP call completes -> Return success

Total time: 12000ms (exceeds 10000ms timeout)
Result: SUCCESS (not timeout error)
```

This is **by design** - the timeout guards against retry stacking, not operation duration.

### Circuit Breaker Integration

Failed operations (even those exceeding timeout expectations) update circuit breaker state:

```python
# Record failure in circuit breaker
if input_data.circuit_breaker_enabled:
    self._record_circuit_breaker_result(operation_id, success=False)
```

This means repeatedly slow operations that eventually fail will trip the circuit breaker.

---

## Example Timelines

### Example 1: Success on First Attempt

```text
Time 0ms:      Check timeout (OK, elapsed=0ms)
               -> Start HTTP call
Time 3000ms:   HTTP call completes with success
               -> Return success (retry_count=0)

Total time: 3000ms
Result: SUCCESS
```

### Example 2: Success After Retry

```text
Time 0ms:      Check timeout (OK, elapsed=0ms)
               -> Start HTTP call
Time 5000ms:   HTTP call fails
               -> Record failure in circuit breaker
               -> Wait 1000ms backoff
Time 6000ms:   Check timeout (OK, elapsed=6000ms < 30000ms)
               -> Start HTTP call (retry #1)
Time 11000ms:  HTTP call completes with success
               -> Return success (retry_count=1)

Total time: 11000ms
Result: SUCCESS (retry_count=1)
```

### Example 3: Timeout After First Attempt

```text
Time 0ms:       Check timeout (OK, elapsed=0ms)
                -> Start HTTP call
Time 25000ms:   HTTP call fails
                -> Record failure in circuit breaker
                -> Wait 1000ms backoff
Time 26000ms:   Calculate backoff delay (2000ms base + jitter)
Time 28000ms:   Check timeout (FAIL, elapsed=28000ms)
                -> Raise TIMEOUT_EXCEEDED

Total time: 28000ms
Result: TIMEOUT_EXCEEDED (after 1 attempt)

Note: Timeout was 30000ms but check happened after backoff wait
```

### Example 4: Operation Exceeds Timeout But Succeeds

```text
Configuration: operation_timeout_ms=5000, retry_enabled=true, max_retries=3

Time 0ms:      Check timeout (OK, elapsed=0ms)
               -> Start HTTP call
Time 7000ms:   HTTP call completes with success
               -> Return success (retry_count=0)

Total time: 7000ms (exceeds 5000ms timeout)
Result: SUCCESS

Why? Timeout is only checked BEFORE attempts, not during.
The operation succeeded before any retry was needed.
```

### Example 5: Long Operation Fails, Timeout on Retry

```text
Configuration: operation_timeout_ms=10000, retry_enabled=true, max_retries=3

Time 0ms:      Check timeout (OK, elapsed=0ms)
               -> Start HTTP call
Time 8000ms:   HTTP call fails (server error)
               -> Record failure
               -> Calculate backoff: 1000ms base + jitter ~= 1100ms
Time 9100ms:   Check timeout (OK, elapsed=9100ms < 10000ms)
               -> Start HTTP call (retry #1)
Time 17000ms:  HTTP call fails again
               -> Check timeout (FAIL, elapsed=17000ms > 10000ms)

Wait... that's not quite right. Let me clarify:

Time 0ms:      Check timeout (OK) -> Start HTTP call
Time 8000ms:   HTTP call fails -> Wait ~1100ms backoff
Time 9100ms:   Check timeout (OK, 9100ms < 10000ms) -> Start retry #1
Time 17100ms:  HTTP call fails -> Try to start retry #2
               Check timeout (FAIL, 17100ms > 10000ms)
               -> Raise TIMEOUT_EXCEEDED

Total time: 17100ms
Result: TIMEOUT_EXCEEDED (after 2 attempts, retry_count=2)
```

---

## Configuration

### Timeout Configuration Sources

Timeout is resolved from multiple sources in priority order:

1. **Operation-specific**: `operation_config["operation_timeout_ms"]`
2. **Subcontract default**: `subcontract.defaults.default_timeout_ms`
3. **System constant**: `DEFAULT_OPERATION_TIMEOUT_MS` (30000ms fallback)

```python
# Resolution logic in MixinEffectExecution.execute_effect()
operation_timeout_ms = (
    operation_config.get("operation_timeout_ms")
    or DEFAULT_OPERATION_TIMEOUT_MS  # 30000ms
)
```

### Constants

**Location**: `src/omnibase_core/constants/constants_effect.py`

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_OPERATION_TIMEOUT_MS` | 30000 | Default timeout if not configured (30 seconds) |
| `DEFAULT_RETRY_JITTER_FACTOR` | 0.1 | 10% random jitter added to backoff |

### Handler-Level Timeouts

Each IO config type has its own `timeout_ms` field that controls handler-internal timeout:

| Config Type | Default timeout_ms | Controls |
|-------------|-------------------|----------|
| `ModelHttpIOConfig` | 30000 | HTTP client timeout |
| `ModelDbIOConfig` | 30000 | Database query timeout |
| `ModelKafkaIOConfig` | 30000 | Kafka produce timeout |
| `ModelFilesystemIOConfig` | 30000 | File operation timeout |

**Recommendation**: Set `io_config.timeout_ms` <= `operation_timeout_ms` to ensure handler timeouts fire before operation timeout.

---

## Best Practices

### 1. Set Appropriate Timeouts

```yaml
# Good: Handler timeout < operation timeout
effect_subcontract:
  operations:
    - operation_name: "fetch_data"
      operation_timeout_ms: 60000  # 60s for full operation including retries
      io_config:
        handler_type: http
        timeout_ms: 10000  # 10s per individual HTTP call
      max_retries: 3  # Up to 4 attempts (initial + 3 retries)
```

### 2. Account for Backoff in Timeout

With exponential backoff, total time grows quickly:

```text
Attempt 1:  0ms    (immediate)
Backoff:    1000ms
Attempt 2:  1000ms
Backoff:    2000ms
Attempt 3:  3000ms
Backoff:    4000ms
Attempt 4:  7000ms

Total backoff time: 7000ms (before 4th attempt)
Plus ~10% jitter: ~7700ms
Plus operation time: varies
```

### 3. Monitor Timeout Metrics

Track these metrics for timeout tuning:

- `retry_count` in `ModelEffectOutput` - indicates failed attempts
- `processing_time_ms` - actual total execution time
- Circuit breaker state transitions - indicate reliability issues

### 4. Handle Handler Timeouts vs Operation Timeouts

- **Handler timeout error**: Individual call failed, may be retried
- **Operation timeout error**: Overall timeout exceeded, no more retries

```python
# Handler timeout (retryable)
except TimeoutError as e:
    # Will retry if attempts remain and operation timeout not exceeded

# Operation timeout (terminal)
except ModelOnexError as e:
    if e.error_code == EnumCoreErrorCode.TIMEOUT_EXCEEDED:
        # No more retries, operation failed
```

---

## Thread Safety Note

Timeout behavior is the same in single-threaded and multi-threaded contexts. However, the underlying `MixinEffectExecution` is **NOT thread-safe** due to circuit breaker state.

See [THREADING.md](../guides/THREADING.md) for:
- Thread-local instance patterns
- Synchronized wrapper patterns
- Production checklist

---

## See Also

- [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](CONTRACT_DRIVEN_NODEEFFECT_V1_0.md) - Full NodeEffect specification
- [THREADING.md](../guides/THREADING.md) - Thread safety guidelines
- [MixinEffectExecution](../../src/omnibase_core/mixins/mixin_effect_execution.py) - Implementation source
- [constants_effect.py](../../src/omnibase_core/constants/constants_effect.py) - Timeout constants

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-09 | Initial documentation created from PR #135 review feedback |

---

**Last Updated**: 2025-12-09
**Author**: ONEX Framework Team
