# Circuit Breaker Pattern for External Dependencies

The ONEX Circuit Breaker Pattern provides fault tolerance and cascading failure prevention for external service calls with comprehensive monitoring, configuration, and graceful degradation capabilities.

## Overview

The Circuit Breaker pattern prevents an application from repeatedly trying to execute an operation that's likely to fail, allowing it to continue without waiting for the fault to be rectified or wasting CPU cycles while it determines that the fault is long-lasting.

### Key Features

- **State Management**: CLOSED → OPEN → HALF_OPEN state transitions
- **Comprehensive Metrics**: Real-time failure rates, response times, and request counts
- **Fallback Support**: Graceful degradation with fallback functions
- **Environment Configuration**: Fully configurable through environment variables
- **Event System**: Extensible event handlers for monitoring and logging
- **Async/Await Support**: Native asyncio support for modern Python applications
- **Multiple Usage Patterns**: Function calls, context managers, and decorators

## Quick Start

### Basic Usage

```
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

# Create circuit breaker
circuit_breaker = ExternalDependencyCircuitBreaker("payment-api")

async def call_payment_api(amount: float):
    # Your external API call
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.payment.com/charge",
            json={"amount": amount}
        )
        return response.json()

# Use circuit breaker
async def process_payment(amount: float):
    try:
        result = await circuit_breaker.call(
            lambda: call_payment_api(amount)
        )
        return result
    except CircuitBreakerException as e:
        logger.warning(f"Payment service unavailable: {e}")
        return {"status": "deferred", "message": "Payment will be processed later"}
```

## Core Components

### ExternalDependencyCircuitBreaker

The main circuit breaker implementation with comprehensive features.

```
class ExternalDependencyCircuitBreaker:
    def __init__(
        self,
        service_name: str,
        config: Optional[ModelCircuitBreakerConfig] = None
    ):
        """Initialize circuit breaker for a service."""
        ...

    async def call(
        self,
        func: Callable[[], Awaitable[T]],
        fallback: Optional[Callable[[], Awaitable[T]]] = None,
        timeout: Optional[float] = None
    ) -> T:
        """Execute function through circuit breaker."""
        ...
```

### Circuit Breaker States

#### CLOSED State
- **Normal operation** - All requests pass through
- **Failure tracking** - Monitors failure rates and counts
- **Transition trigger** - Opens when failure thresholds are exceeded

#### OPEN State  
- **Fail-fast operation** - Requests fail immediately
- **Recovery timer** - Waits for recovery timeout before testing
- **Transition trigger** - Moves to HALF_OPEN after timeout

#### HALF_OPEN State
- **Limited testing** - Allows small number of test requests
- **Quick decisions** - Single failure returns to OPEN, successes move to CLOSED
- **Transition triggers** - Success threshold closes circuit, any failure opens it

### Configuration

Environment-configurable circuit breaker settings:

```
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

config = ModelCircuitBreakerConfig(
    failure_threshold=5,          # Failures before opening
    failure_rate_threshold=0.5,   # 50% failure rate threshold
    minimum_request_threshold=10, # Min requests before rate calculation
    recovery_timeout_seconds=60,  # Time before testing recovery
    success_threshold=3,          # Successes needed to close
    request_timeout_seconds=10.0, # Individual request timeout
    exponential_backoff=True,     # Increase backoff on repeated failures
    max_backoff_seconds=300       # Maximum backoff time
)
```

## Usage Patterns

### 1. Function Call Pattern

```
async def example_function_call():
    circuit_breaker = ExternalDependencyCircuitBreaker("user-service")

    async def get_user(user_id: str):
        # External API call
        return await user_api.get(user_id)

    try:
        user = await circuit_breaker.call(
            lambda: get_user("user-123")
        )
        return user
    except CircuitBreakerException:
        # Circuit is open - service is down
        return {"id": "user-123", "name": "Anonymous"}
```

### 2. Fallback Pattern

```
async def example_with_fallback():
    circuit_breaker = ExternalDependencyCircuitBreaker("recommendation-service")

    async def get_recommendations(user_id: str):
        return await recommendation_api.get(user_id)

    async def fallback_recommendations(user_id: str):
        # Return cached or default recommendations
        return await cache.get(f"recommendations:{user_id}", default=[])

    # Circuit breaker will automatically use fallback when circuit is open
    recommendations = await circuit_breaker.call(
        lambda: get_recommendations("user-123"),
        fallback=lambda: fallback_recommendations("user-123")
    )

    return recommendations
```

### 3. Context Manager Pattern

```
async def example_context_manager():
    circuit_breaker = ExternalDependencyCircuitBreaker("analytics-service")

    try:
        async with circuit_breaker.protect(timeout=5.0) as cb:
            # Perform external operation
            result = await analytics_api.track_event("user_action", {"user_id": "123"})
            cb.set_result(result)

        print("Analytics event tracked successfully")
    except CircuitBreakerException:
        print("Analytics service unavailable - event cached locally")
    except Exception as e:
        print(f"Analytics tracking failed: {e}")
```

### 4. Environment-Based Configuration

```
import os

# Set circuit breaker configuration via environment variables
os.environ['CB_EMAIL_SERVICE_FAILURE_THRESHOLD'] = '3'
os.environ['CB_EMAIL_SERVICE_FAILURE_RATE_THRESHOLD'] = '0.4'
os.environ['CB_EMAIL_SERVICE_RECOVERY_TIMEOUT_SECONDS'] = '30'

# Create circuit breaker with environment configuration
circuit_breaker = CircuitBreakerFactory.create_from_environment(
    "email-service",
    prefix="CB_EMAIL_SERVICE"
)
```

## Factory Methods

### Pre-configured Circuit Breakers

```
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

# Fast-fail circuit breaker - quick failure detection
fast_cb = CircuitBreakerFactory.create_fast_fail("critical-service")
# Config: failure_threshold=3, recovery_timeout=30s

# Resilient circuit breaker - tolerates more failures
resilient_cb = CircuitBreakerFactory.create_resilient("background-service")
# Config: failure_threshold=10, recovery_timeout=120s, exponential_backoff=True

# Environment-configured circuit breaker
env_cb = CircuitBreakerFactory.create_from_environment("service-name")
```

## Metrics and Monitoring

### Real-time Metrics

```
# Get current metrics
metrics = circuit_breaker.get_metrics()

print(f"State: {metrics.current_state}")
print(f"Total requests: {metrics.total_requests}")
print(f"Success rate: {metrics.get_success_rate():.2%}")
print(f"Failure rate: {metrics.get_failure_rate():.2%}")
print(f"Average response time: {metrics.average_response_time_ms:.1f}ms")
print(f"State changes: {metrics.state_changes}")
```

### Event Handling

```
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState

async def log_state_changes(cb, event, metrics):
    if event == CircuitBreakerEvent.STATE_CHANGE:
        logger.warning(f"Circuit breaker {cb.service_name} changed to {metrics.current_state}")

async def alert_on_failures(cb, event, metrics):
    if event == CircuitBreakerEvent.FAILURE:
        if metrics.get_failure_rate() > 0.5:
            await send_alert(f"High failure rate for {cb.service_name}")

# Register event listeners
circuit_breaker.add_event_listener(CircuitBreakerEvent.STATE_CHANGE, log_state_changes)
circuit_breaker.add_event_listener(CircuitBreakerEvent.FAILURE, alert_on_failures)
```

### Global Registry

```
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

# Register circuit breakers globally
register_circuit_breaker("payment-api", payment_cb)
register_circuit_breaker("user-service", user_cb)

# Get circuit breaker by name
cb = get_circuit_breaker("payment-api")

# List all circuit breakers with status
status_summary = list_circuit_breakers()
for service, status in status_summary.items():
    print(f"{service}: {status['state']} (failure rate: {status['failure_rate']:.1%})")
```

## Advanced Features

### Exponential Backoff

```
config = ModelCircuitBreakerConfig(
    recovery_timeout_seconds=60,
    exponential_backoff=True,      # Enable exponential backoff
    max_backoff_seconds=300        # Cap backoff at 5 minutes
)

circuit_breaker = ExternalDependencyCircuitBreaker("unreliable-service", config)

# Backoff progression: 60s → 120s → 240s → 300s (capped)
```

### Slow Call Detection

```
config = ModelCircuitBreakerConfig(
    slow_call_threshold_ms=5000,    # 5 second threshold
    slow_call_rate_threshold=0.3    # 30% slow calls trigger opening
)

# Circuit will open if 30% of requests take longer than 5 seconds
```

### Manual Control

```
# Force circuit states for maintenance or testing
await circuit_breaker.force_open()    # Force circuit open
await circuit_breaker.force_close()   # Force circuit closed
await circuit_breaker.reset()         # Reset all metrics and state
```

## Integration Examples

### HTTP Client Integration

```
import httpx
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

class ResilientHTTPClient:
    def __init__(self, base_url: str, service_name: str):
        self.client = httpx.AsyncClient(base_url=base_url)
        self.circuit_breaker = CircuitBreakerFactory.create_fast_fail(service_name)

    async def get(self, path: str, **kwargs):
        async def make_request():
            response = await self.client.get(path, **kwargs)
            response.raise_for_status()
            return response.json()

        return await self.circuit_breaker.call(make_request)

    async def post(self, path: str, **kwargs):
        async def make_request():
            response = await self.client.post(path, **kwargs)
            response.raise_for_status()
            return response.json()

        return await self.circuit_breaker.call(make_request)

# Usage
client = ResilientHTTPClient("https://api.example.com", "example-api")
data = await client.get("/users/123")
```

### Database Integration

```
import asyncpg
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

class ResilientDatabase:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.circuit_breaker = CircuitBreakerFactory.create_resilient("database")
        self._pool = None

    async def execute(self, query: str, *args):
        async def db_operation():
            if not self._pool:
                self._pool = await asyncpg.create_pool(self.dsn)

            async with self._pool.acquire() as conn:
                return await conn.execute(query, *args)

        return await self.circuit_breaker.call(db_operation)

    async def fetch(self, query: str, *args):
        async def db_operation():
            if not self._pool:
                self._pool = await asyncpg.create_pool(self.dsn)

            async with self._pool.acquire() as conn:
                return await conn.fetch(query, *args)

        # Use fallback for read operations
        async def cached_fallback():
            # Return cached data or empty result
            return []

        return await self.circuit_breaker.call(
            db_operation,
            fallback=cached_fallback
        )

# Usage
db = ResilientDatabase("postgresql://user:pass@localhost/db")
users = await db.fetch("SELECT * FROM users WHERE active = $1", True)
```

### Message Queue Integration

```
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

class ResilientMessagePublisher:
    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        self.circuit_breaker = ExternalDependencyCircuitBreaker("message-queue")
        self.local_queue = []  # Fallback storage

    async def publish(self, message: dict):
        async def publish_to_queue():
            # Your queue publishing logic
            await queue_client.publish(message)
            return {"status": "published"}

        async def store_locally():
            # Fallback - store message locally for later processing
            self.local_queue.append(message)
            return {"status": "queued_locally"}

        return await self.circuit_breaker.call(
            publish_to_queue,
            fallback=store_locally
        )

    async def flush_local_queue(self):
        """Process locally queued messages when service recovers"""
        if self.circuit_breaker.get_state() == CircuitBreakerState.CLOSED:
            for message in self.local_queue:
                try:
                    await self.publish(message)
                except Exception:
                    break  # Stop if service fails again
            self.local_queue.clear()
```

## Best Practices

### 1. Choose Appropriate Thresholds

```
# Fast-fail for critical services
critical_config = ModelCircuitBreakerConfig(
    failure_threshold=3,
    failure_rate_threshold=0.3,
    recovery_timeout_seconds=30
)

# Resilient for background services
background_config = ModelCircuitBreakerConfig(
    failure_threshold=10,
    failure_rate_threshold=0.6,
    recovery_timeout_seconds=120,
    exponential_backoff=True
)
```

### 2. Implement Meaningful Fallbacks

```
# Good - Provides degraded functionality
async def get_user_recommendations(user_id: str):
    async def primary():
        return await ml_service.get_recommendations(user_id)

    async def fallback():
        # Return popular items or cached recommendations
        return await cache.get_popular_items()

    return await circuit_breaker.call(primary, fallback=fallback)

# Bad - No graceful degradation
async def process_payment(amount: float):
    return await circuit_breaker.call(lambda: payment_api.charge(amount))
    # No fallback - users can't complete purchases when service is down
```

### 3. Monitor Circuit Breaker Health

```
# Set up monitoring
async def circuit_breaker_health_check():
    unhealthy_services = []

    for service, status in list_circuit_breakers().items():
        if status['state'] == 'open':
            unhealthy_services.append(service)
        elif status['failure_rate'] > 0.1:  # 10% failure rate warning
            logger.warning(f"High failure rate for {service}: {status['failure_rate']:.1%}")

    if unhealthy_services:
        await send_alert(f"Circuit breakers open: {unhealthy_services}")

# Run periodically
asyncio.create_task(circuit_breaker_health_check())
```

### 4. Use Environment Configuration

```
# production.env
CB_PAYMENT_API_FAILURE_THRESHOLD=5
CB_PAYMENT_API_RECOVERY_TIMEOUT_SECONDS=60
CB_PAYMENT_API_EXPONENTIAL_BACKOFF=true

# development.env  
CB_PAYMENT_API_FAILURE_THRESHOLD=10
CB_PAYMENT_API_RECOVERY_TIMEOUT_SECONDS=10
CB_PAYMENT_API_EXPONENTIAL_BACKOFF=false

# Application code
payment_cb = CircuitBreakerFactory.create_from_environment("payment-api")
```

### 5. Handle Circuit Breaker Exceptions Appropriately

```
async def handle_user_request():
    try:
        result = await circuit_breaker.call(external_service_call)
        return {"status": "success", "data": result}

    except CircuitBreakerOpenException:
        # Circuit is open - service is known to be down
        logger.info("Service unavailable, using fallback")
        return {"status": "degraded", "data": fallback_data}

    except CircuitBreakerTimeoutException:
        # Request timed out
        logger.warning("Service timeout, request cancelled")
        return {"status": "timeout", "message": "Request cancelled due to timeout"}

    except Exception as e:
        # Actual service error
        logger.error(f"Service error: {e}")
        return {"status": "error", "message": "Service temporarily unavailable"}
```

## Troubleshooting

### Debug Circuit Breaker State

```
# Enable debug logging
import logging
logging.getLogger('your_module_name').setLevel(logging.DEBUG)  # Replace with actual module

# Check circuit breaker state
cb = get_circuit_breaker("my-service")
metrics = cb.get_metrics()

print(f"Service: {cb.service_name}")
print(f"State: {metrics.current_state}")
print(f"Configuration:")
print(f"  Failure threshold: {cb.config.failure_threshold}")
print(f"  Failure rate threshold: {cb.config.failure_rate_threshold}")
print(f"  Recovery timeout: {cb.config.recovery_timeout_seconds}s")

print(f"Metrics:")
print(f"  Total requests: {metrics.total_requests}")
print(f"  Success rate: {metrics.get_success_rate():.2%}")
print(f"  In current window: {metrics.requests_in_window}")
print(f"  Window failure rate: {metrics.get_failure_rate():.2%}")
```

### Common Issues

#### Circuit Opens Too Quickly
```
# Problem: Circuit opens on first few failures
# Solution: Increase minimum_request_threshold
config = ModelCircuitBreakerConfig(
    failure_threshold=5,
    minimum_request_threshold=20  # Need 20 requests before evaluating
)
```

#### Circuit Doesn't Open When Expected  
```
# Problem: Service is failing but circuit stays closed
# Solution: Check failure rate threshold and request count
config = ModelCircuitBreakerConfig(
    failure_rate_threshold=0.3,  # Lower threshold (30%)
    minimum_request_threshold=5  # Lower minimum requests
)
```

#### Slow Recovery
```
# Problem: Circuit takes too long to test recovery
# Solution: Reduce recovery timeout
config = ModelCircuitBreakerConfig(
    recovery_timeout_seconds=30,  # Test recovery sooner
    exponential_backoff=False     # Disable backoff for faster recovery
)
```

This comprehensive circuit breaker implementation provides robust fault tolerance for external dependencies while maintaining observability and configurability for various service interaction patterns.
