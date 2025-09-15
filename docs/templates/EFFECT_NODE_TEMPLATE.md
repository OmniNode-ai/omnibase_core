# ONEX EFFECT Node Template - Unified Architecture

**Version**: 1.0.0  
**Purpose**: Standardized template for creating EFFECT nodes across OmniNode repositories  
**Compliance**: ONEX 4-Node Architecture + OmniBase Infrastructure Patterns  

## 🎯 Template Overview

This template provides a complete "cookie cutter" approach for generating consistent EFFECT nodes that follow unified architecture patterns across all OmniNode repositories. An agent can use this template to stamp out new EFFECT nodes with minimal customization.

## 📁 Directory Structure Template

```
src/{REPOSITORY_NAME}/nodes/node_{DOMAIN}_{MICROSERVICE_NAME}_effect/
├── __init__.py                                    # Package exports
├── v1_0_0/                                       # Versioned implementation
│   ├── __init__.py                               # Version exports
│   ├── node.py                                   # Main node implementation
│   ├── models/                                   # Typed models
│   │   ├── __init__.py
│   │   ├── model_{MICROSERVICE_NAME}_input.py    # Input envelope
│   │   ├── model_{MICROSERVICE_NAME}_output.py   # Output envelope
│   │   └── model_{MICROSERVICE_NAME}_config.py   # Configuration model
│   ├── enums/                                    # Typed enumerations
│   │   ├── __init__.py
│   │   └── enum_{MICROSERVICE_NAME}_operation_type.py
│   ├── contracts/                                # YAML subcontracts
│   │   ├── {MICROSERVICE_NAME}_processing_subcontract.yaml
│   │   └── {MICROSERVICE_NAME}_management_subcontract.yaml
│   └── manifests/                               # Version manifests
│       ├── version_manifest.yaml
│       └── compatibility_matrix.yaml
└── README.md                                    # Node documentation
```

## 🔧 Customization Points

Replace the following placeholders when using this template:

- `{REPOSITORY_NAME}`: Repository name (e.g., `omniplan`, `omnibase_infra`)
- `{DOMAIN}`: Domain name (e.g., `rsd`, `infrastructure`, `ai`)  
- `{MICROSERVICE_NAME}`: Specific microservice (e.g., `priority_storage`, `postgres_adapter`)
- `{BUSINESS_DESCRIPTION}`: Description of business functionality
- `{EXTERNAL_SYSTEM}`: External system being integrated (e.g., PostgreSQL, Redis)

## 📄 File Templates

### 1. Main Node Implementation Template

**File**: `v1_0_0/node.py`

```python
#!/usr/bin/env python3
"""
{DOMAIN} {MICROSERVICE_NAME} Effect Node - ONEX 4-Node Architecture Implementation.

{BUSINESS_DESCRIPTION}

This microservice handles {DOMAIN} {MICROSERVICE_NAME} operations:
- [OPERATION_1]: [Description]
- [OPERATION_2]: [Description]  
- [OPERATION_3]: [Description]

Key Features:
- [FEATURE_1]: [Description]
- [FEATURE_2]: [Description]
- [FEATURE_3]: [Description]
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Pattern, Callable
from uuid import UUID, uuid4

from omnibase_core.core.node_effect import ModelEffectInput, ModelEffectOutput
from omnibase_core.core.node_effect_service import NodeEffectService
from omnibase_core.core.onex_container import ModelONEXContainer as ONEXContainer
from omnibase_core.enums.node import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.errors.onex_error import OnexError

from .models.model_{MICROSERVICE_NAME}_input import Model{MICROSERVICE_NAME_PASCAL}Input
from .models.model_{MICROSERVICE_NAME}_output import Model{MICROSERVICE_NAME_PASCAL}Output
from .models.model_{MICROSERVICE_NAME}_config import Model{MICROSERVICE_NAME_PASCAL}Config
from .enums.enum_{MICROSERVICE_NAME}_operation_type import Enum{MICROSERVICE_NAME_PASCAL}OperationType


class Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect(NodeEffectService):
    """
    {DOMAIN} {MICROSERVICE_NAME} Effect Node - ONEX 4-Node Architecture Implementation.

    {BUSINESS_DESCRIPTION}

    Integrates with:
    - {MICROSERVICE_NAME}_processing_subcontract: Core operation patterns
    - {MICROSERVICE_NAME}_management_subcontract: Resource management patterns
    """

    # Configuration loaded from container or environment
    config: Model{MICROSERVICE_NAME_PASCAL}Config

    # Pre-compiled security patterns for performance
    _SENSITIVE_DATA_PATTERNS: List[tuple[Pattern, str]] = [
        (re.compile(r'password=[^\s&]*', re.IGNORECASE), 'password=***'),
        (re.compile(r'token=[^\s&]*', re.IGNORECASE), 'token=***'),
        (re.compile(r'api[_-]?key[_-]*[:=][^\s&]*', re.IGNORECASE), 'api_key=***'),
        # Add domain-specific patterns here
    ]

    def __init__(self, container: ONEXContainer):
        """Initialize {MICROSERVICE_NAME} effect node with container injection."""
        super().__init__(container)
        self.node_type = "effect"
        self.domain = "{DOMAIN}"
        self._resource_manager = None
        self._resource_manager_lock = asyncio.Lock()

        # Initialize configuration from container or environment
        self.config = self._load_configuration(container)

        # Performance tracking
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0

        # Circuit breaker for external system resilience
        self.circuit_breaker = {
            "failure_count": 0,
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "last_failure_time": 0,
            "state": "closed",  # closed, open, half_open
        }

    def _load_configuration(self, container: ONEXContainer) -> Model{MICROSERVICE_NAME_PASCAL}Config:
        """Load configuration from container or environment."""
        try:
            # Try container service resolution first
            config = container.get_service("{MICROSERVICE_NAME}_config")
            if config and isinstance(config, Model{MICROSERVICE_NAME_PASCAL}Config):
                return config
        except Exception:
            pass

        # Fallback to environment-based configuration
        import os
        environment = os.getenv("DEPLOYMENT_ENVIRONMENT", "development")
        return Model{MICROSERVICE_NAME_PASCAL}Config.for_environment(environment)

    # === ONEX Compliance Interface ===

    async def effect(self, effect_input: ModelEffectInput) -> ModelEffectOutput:
        """
        ONEX-compliant effect interface wrapper.

        Delegates to typed process() method for business logic.
        """
        start_time = time.perf_counter()
        correlation_id = str(uuid4())

        try:
            # Convert generic input to typed input
            typed_input = Model{MICROSERVICE_NAME_PASCAL}Input.model_validate(effect_input.data)
            typed_input.correlation_id = UUID(correlation_id)

            # Execute typed business logic
            result = await self.process(typed_input)

            execution_time = (time.perf_counter() - start_time) * 1000

            return ModelEffectOutput(
                result=result.model_dump(),
                operation_id=correlation_id,
                effect_type="{MICROSERVICE_NAME}_operation",
                processing_time_ms=execution_time,
                external_system_latency_ms=result.execution_time_ms,
                resources_consumed={"operations": 1},
                metadata={
                    "node_type": "effect",
                    "domain": "{DOMAIN}",
                    "microservice": "{MICROSERVICE_NAME}",
                    "operation_type": result.operation_type.value,
                },
            )

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            error_message = self._sanitize_error_message(str(e))

            return ModelEffectOutput(
                result={"error": error_message},
                operation_id=correlation_id,
                effect_type="{MICROSERVICE_NAME}_operation",
                processing_time_ms=execution_time,
                external_system_latency_ms=0,
                resources_consumed={"operations": 0},
                metadata={
                    "node_type": "effect",
                    "domain": "{DOMAIN}",
                    "error": True,
                    "error_type": type(e).__name__,
                },
            )

    # === Primary Business Interface ===

    async def process(self, input_data: Model{MICROSERVICE_NAME_PASCAL}Input) -> Model{MICROSERVICE_NAME_PASCAL}Output:
        """
        Main business logic interface with typed models.

        Routes operations based on operation_type and executes with proper
        error handling, metrics collection, and circuit breaker patterns.
        """
        start_time = time.perf_counter()

        try:
            self.operation_count += 1

            # Validate correlation ID
            validated_correlation_id = self._validate_correlation_id(input_data.correlation_id)
            input_data.correlation_id = validated_correlation_id

            # Check circuit breaker
            if self._is_circuit_breaker_open():
                raise OnexError(
                    code=CoreErrorCode.CIRCUIT_BREAKER_OPEN,
                    message=f"{MICROSERVICE_NAME} circuit breaker is open"
                )

            # Route based on operation type
            if input_data.operation_type == Enum{MICROSERVICE_NAME_PASCAL}OperationType.OPERATION_1:
                return await self._handle_operation_1(input_data, start_time)
            elif input_data.operation_type == Enum{MICROSERVICE_NAME_PASCAL}OperationType.OPERATION_2:
                return await self._handle_operation_2(input_data, start_time)
            elif input_data.operation_type == Enum{MICROSERVICE_NAME_PASCAL}OperationType.HEALTH_CHECK:
                return await self._handle_health_check_operation(input_data, start_time)
            else:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Unsupported operation type: {input_data.operation_type}",
                )

        except Exception as e:
            self.error_count += 1
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Update circuit breaker on failure
            self._record_failure()

            error_message = self._sanitize_error_message(str(e))

            return Model{MICROSERVICE_NAME_PASCAL}Output(
                operation_type=input_data.operation_type,
                success=False,
                error_message=error_message,
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                execution_time_ms=execution_time_ms,
                context={"error_type": type(e).__name__}
            )

    # === Operation Handlers ===

    async def _handle_operation_1(
        self,
        input_data: Model{MICROSERVICE_NAME_PASCAL}Input,
        start_time: float
    ) -> Model{MICROSERVICE_NAME_PASCAL}Output:
        """Handle operation 1 - customize implementation."""
        # TODO: Implement operation 1 logic
        await asyncio.sleep(0.01)  # Simulate work

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return Model{MICROSERVICE_NAME_PASCAL}Output(
            operation_type=input_data.operation_type,
            success=True,
            data={"result": "operation_1_completed"},
            correlation_id=input_data.correlation_id,
            timestamp=time.time(),
            execution_time_ms=execution_time_ms,
        )

    async def _handle_operation_2(
        self,
        input_data: Model{MICROSERVICE_NAME_PASCAL}Input,
        start_time: float
    ) -> Model{MICROSERVICE_NAME_PASCAL}Output:
        """Handle operation 2 - customize implementation."""
        # TODO: Implement operation 2 logic
        await asyncio.sleep(0.01)  # Simulate work

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return Model{MICROSERVICE_NAME_PASCAL}Output(
            operation_type=input_data.operation_type,
            success=True,
            data={"result": "operation_2_completed"},
            correlation_id=input_data.correlation_id,
            timestamp=time.time(),
            execution_time_ms=execution_time_ms,
        )

    async def _handle_health_check_operation(
        self,
        input_data: Model{MICROSERVICE_NAME_PASCAL}Input,
        start_time: float
    ) -> Model{MICROSERVICE_NAME_PASCAL}Output:
        """Handle health check operation."""
        try:
            # Perform health checks
            health_results = []

            # Add domain-specific health checks here
            overall_healthy = True  # Customize based on actual checks

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            return Model{MICROSERVICE_NAME_PASCAL}Output(
                operation_type=input_data.operation_type,
                success=overall_healthy,
                data={
                    "health_status": "healthy" if overall_healthy else "unhealthy",
                    "checks": health_results,
                    "node_type": "effect",
                    "domain": "{DOMAIN}",
                    "microservice": "{MICROSERVICE_NAME}"
                },
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            error_message = self._sanitize_error_message(f"Health check failed: {str(e)}")

            return Model{MICROSERVICE_NAME_PASCAL}Output(
                operation_type=input_data.operation_type,
                success=False,
                error_message=error_message,
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                execution_time_ms=execution_time_ms,
            )

    # === Utility Methods ===

    def _validate_correlation_id(self, correlation_id: Optional[UUID]) -> UUID:
        """Validate and normalize correlation ID."""
        if correlation_id is None:
            return uuid4()

        if isinstance(correlation_id, str):
            try:
                correlation_id = UUID(correlation_id)
            except ValueError:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message="Invalid correlation ID format - must be valid UUID"
                )

        if not isinstance(correlation_id, UUID):
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="Correlation ID must be UUID type"
            )

        return correlation_id

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        circuit_breaker = self.circuit_breaker

        if circuit_breaker["state"] == "open":
            if time.time() - circuit_breaker["last_failure_time"] > circuit_breaker["recovery_timeout"]:
                circuit_breaker["state"] = "half_open"
                return False
            return True

        return False

    def _record_failure(self) -> None:
        """Record failure for circuit breaker."""
        circuit_breaker = self.circuit_breaker
        circuit_breaker["failure_count"] += 1
        circuit_breaker["last_failure_time"] = time.time()

        if circuit_breaker["failure_count"] >= circuit_breaker["failure_threshold"]:
            circuit_breaker["state"] = "open"

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after successful operation."""
        if self.circuit_breaker["state"] in ["half_open", "open"]:
            self.circuit_breaker["state"] = "closed"
            self.circuit_breaker["failure_count"] = 0

    def _sanitize_error_message(self, error_message: str) -> str:
        """Sanitize error messages to prevent sensitive information leakage."""
        if not self.config.enable_error_sanitization:
            return error_message

        sanitized = error_message
        for pattern, replacement in self._SENSITIVE_DATA_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    # === Health Check Interface ===

    async def get_health_status(self) -> ModelHealthStatus:
        """Get health status of the effect node."""
        status = EnumHealthStatus.HEALTHY
        details = {
            "node_type": "effect",
            "domain": "{DOMAIN}",
            "microservice": "{MICROSERVICE_NAME}",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "circuit_breaker_state": self.circuit_breaker["state"],
        }

        # Determine status based on circuit breaker and error rate
        if self.circuit_breaker["state"] != "closed":
            status = EnumHealthStatus.DEGRADED

        min_ops = 10
        error_threshold = 0.1

        if (
            self.operation_count > min_ops
            and (self.error_count / self.operation_count) > error_threshold
        ):
            status = EnumHealthStatus.DEGRADED

        return ModelHealthStatus(
            status=status,
            timestamp=datetime.now(),
            details=details,
        )


# === Entry Point ===

async def main():
    """Main entry point for {MICROSERVICE_NAME} Effect - runs in service mode."""
    from {REPOSITORY_NAME}.core.container import create_{DOMAIN}_container

    container = create_{DOMAIN}_container()
    effect_node = Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect(container)

    await effect_node.initialize()
    await effect_node.start_service_mode()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 2. Input Model Template

**File**: `models/model_{MICROSERVICE_NAME}_input.py`

```python
"""{MICROSERVICE_NAME} input envelope model."""

from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..enums.enum_{MICROSERVICE_NAME}_operation_type import Enum{MICROSERVICE_NAME_PASCAL}OperationType


class Model{MICROSERVICE_NAME_PASCAL}Input(BaseModel):
    """Input envelope for {MICROSERVICE_NAME} operations."""

    operation_type: Enum{MICROSERVICE_NAME_PASCAL}OperationType = Field(
        description="Type of operation to perform"
    )

    # Typed operation-specific requests (add as needed)
    operation_1_request: Optional[Dict[str, Any]] = Field(
        default=None, description="Operation 1 request data"
    )

    operation_2_request: Optional[Dict[str, Any]] = Field(
        default=None, description="Operation 2 request data"
    )

    correlation_id: UUID = Field(description="Request correlation ID for tracing")

    timestamp: float = Field(description="Request timestamp as Unix timestamp", ge=0)

    timeout_seconds: Optional[float] = Field(
        default=30.0, description="Operation timeout in seconds", gt=0
    )

    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional request context"
    )

    # Add domain-specific fields here
```

### 3. Output Model Template

**File**: `models/model_{MICROSERVICE_NAME}_output.py`

```python
"""{MICROSERVICE_NAME} output envelope model."""

from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..enums.enum_{MICROSERVICE_NAME}_operation_type import Enum{MICROSERVICE_NAME_PASCAL}OperationType


class Model{MICROSERVICE_NAME_PASCAL}Output(BaseModel):
    """Output envelope for {MICROSERVICE_NAME} operations."""

    operation_type: Enum{MICROSERVICE_NAME_PASCAL}OperationType = Field(
        description="Type of operation that was executed"
    )

    success: bool = Field(description="Whether the operation was successful")

    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Operation result data"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )

    correlation_id: UUID = Field(description="Request correlation ID for tracing")

    timestamp: float = Field(description="Response timestamp as Unix timestamp", ge=0)

    execution_time_ms: float = Field(
        description="Total operation execution time in milliseconds", ge=0
    )

    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional response context"
    )

    # Add domain-specific response fields here
```

### 4. Configuration Model Template

**File**: `models/model_{MICROSERVICE_NAME}_config.py`

```python
"""{MICROSERVICE_NAME} configuration model."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class Model{MICROSERVICE_NAME_PASCAL}Config(BaseModel):
    """Configuration for {MICROSERVICE_NAME} effect node."""

    # Core configuration
    max_timeout_seconds: float = Field(default=30.0, gt=0)
    enable_error_sanitization: bool = Field(default=True)

    # Circuit breaker configuration
    circuit_breaker_failure_threshold: int = Field(default=5, gt=0)
    circuit_breaker_recovery_timeout: float = Field(default=60.0, gt=0)

    # Performance configuration
    max_concurrent_operations: int = Field(default=100, gt=0)
    operation_queue_size: int = Field(default=1000, gt=0)

    # Add domain-specific configuration fields here

    @classmethod
    def for_environment(cls, environment: str) -> "Model{MICROSERVICE_NAME_PASCAL}Config":
        """Load environment-specific configuration."""
        base_config = {
            "max_timeout_seconds": 30.0,
            "enable_error_sanitization": True,
        }

        if environment == "production":
            return cls(
                **base_config,
                max_timeout_seconds=10.0,
                max_concurrent_operations=200,
                operation_queue_size=2000,
            )
        elif environment == "staging":
            return cls(
                **base_config,
                max_timeout_seconds=15.0,
                max_concurrent_operations=100,
            )
        elif environment == "development":
            return cls(
                **base_config,
                enable_error_sanitization=False,
                max_timeout_seconds=60.0,
            )
        else:
            return cls(**base_config)
```

### 5. Operation Type Enum Template

**File**: `enums/enum_{MICROSERVICE_NAME}_operation_type.py`

```python
"""{MICROSERVICE_NAME} operation type enumeration."""

from enum import Enum


class Enum{MICROSERVICE_NAME_PASCAL}OperationType(str, Enum):
    """Enumeration of supported {MICROSERVICE_NAME} operation types."""

    OPERATION_1 = "operation_1"
    OPERATION_2 = "operation_2"
    HEALTH_CHECK = "health_check"

    # Add domain-specific operation types here
```

### 6. Package Export Templates

**File**: `__init__.py` (root)

```python
"""{DOMAIN} {MICROSERVICE_NAME} Effect Node Package."""

from .v1_0_0 import (
    Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect,
    Model{MICROSERVICE_NAME_PASCAL}Input,
    Model{MICROSERVICE_NAME_PASCAL}Output,
    Model{MICROSERVICE_NAME_PASCAL}Config,
    Enum{MICROSERVICE_NAME_PASCAL}OperationType,
)

__all__ = [
    "Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect",
    "Model{MICROSERVICE_NAME_PASCAL}Input",
    "Model{MICROSERVICE_NAME_PASCAL}Output",
    "Model{MICROSERVICE_NAME_PASCAL}Config",
    "Enum{MICROSERVICE_NAME_PASCAL}OperationType",
]
```

**File**: `v1_0_0/__init__.py`

```python
"""Version 1.0.0 of {DOMAIN} {MICROSERVICE_NAME} Effect Node."""

from .node import Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect
from .models.model_{MICROSERVICE_NAME}_input import Model{MICROSERVICE_NAME_PASCAL}Input
from .models.model_{MICROSERVICE_NAME}_output import Model{MICROSERVICE_NAME_PASCAL}Output
from .models.model_{MICROSERVICE_NAME}_config import Model{MICROSERVICE_NAME_PASCAL}Config
from .enums.enum_{MICROSERVICE_NAME}_operation_type import Enum{MICROSERVICE_NAME_PASCAL}OperationType

__all__ = [
    "Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect",
    "Model{MICROSERVICE_NAME_PASCAL}Input",
    "Model{MICROSERVICE_NAME_PASCAL}Output",
    "Model{MICROSERVICE_NAME_PASCAL}Config",
    "Enum{MICROSERVICE_NAME_PASCAL}OperationType",
]
```

## 📋 Contract Templates

### 7. Processing Subcontract Template

**File**: `contracts/{MICROSERVICE_NAME}_processing_subcontract.yaml`

```yaml
# {MICROSERVICE_NAME} Processing Subcontract
# Defines core operation patterns and business logic flows

apiVersion: contracts.onex.ai/v1
kind: ProcessingSubcontract
metadata:
  name: {MICROSERVICE_NAME}-processing-subcontract
  version: 1.0.0
  domain: {DOMAIN}
  microservice: {MICROSERVICE_NAME}

spec:
  description: |
    Core processing patterns for {MICROSERVICE_NAME} operations including
    operation routing, business logic execution, and result formatting.

  operations:
    - name: operation_1
      description: "First operation - customize description"
      input_schema:
        type: object
        properties:
          operation_1_request:
            type: object
            description: "Operation 1 specific data"
          correlation_id:
            type: string
            format: uuid
            description: "Request correlation ID"
        required: [correlation_id]

      output_schema:
        type: object
        properties:
          success:
            type: boolean
          data:
            type: object
          execution_time_ms:
            type: number
            minimum: 0
        required: [success, execution_time_ms]

      error_handling:
        - code: VALIDATION_ERROR
          message: "Input validation failed"
          recovery: "Return structured error response"
        - code: TIMEOUT_ERROR  
          message: "Operation timeout exceeded"
          recovery: "Abort operation and return timeout error"

    - name: operation_2
      description: "Second operation - customize description"
      # Add operation 2 specification

    - name: health_check
      description: "Health check operation"
      input_schema:
        type: object
        properties:
          correlation_id:
            type: string
            format: uuid
        required: [correlation_id]

      output_schema:
        type: object
        properties:
          success:
            type: boolean
          data:
            type: object
            properties:
              health_status:
                type: string
                enum: [healthy, degraded, unhealthy]
        required: [success, data]

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_seconds: 60
    supported_states: [closed, open, half_open]

  performance_requirements:
    max_response_time_ms: 1000
    max_concurrent_operations: 100
    target_success_rate: 99.5

  monitoring:
    metrics:
      - operation_count
      - success_rate
      - error_rate
      - circuit_breaker_state
      - execution_time_percentiles

    health_indicators:
      - circuit_breaker_state
      - resource_availability
      - external_dependency_health
```

### 8. Management Subcontract Template

**File**: `contracts/{MICROSERVICE_NAME}_management_subcontract.yaml`

```yaml
# {MICROSERVICE_NAME} Management Subcontract  
# Defines resource management, lifecycle, and operational patterns

apiVersion: contracts.onex.ai/v1
kind: ManagementSubcontract
metadata:
  name: {MICROSERVICE_NAME}-management-subcontract
  version: 1.0.0
  domain: {DOMAIN}
  microservice: {MICROSERVICE_NAME}

spec:
  description: |
    Resource management and operational patterns for {MICROSERVICE_NAME}
    including lifecycle management, resource allocation, and monitoring.

  lifecycle:
    initialization:
      description: "Initialize {MICROSERVICE_NAME} resources"
      steps:
        - validate_configuration
        - initialize_external_connections
        - warm_up_caches
        - register_health_checks

      failure_handling:
        - retry_count: 3
        - retry_delay_seconds: 5
        - fallback: "graceful_degradation"

    shutdown:
      description: "Graceful shutdown of {MICROSERVICE_NAME}"
      steps:
        - stop_accepting_requests
        - complete_pending_operations
        - close_external_connections
        - cleanup_resources

      timeout_seconds: 30
      force_shutdown: true

  resource_management:
    external_dependencies:
      - name: "{EXTERNAL_SYSTEM}"
        type: "database|cache|api|filesystem"
        connection_pool:
          min_connections: 5
          max_connections: 20
          connection_timeout_seconds: 10

        health_check:
          method: "ping|query|status_endpoint"
          interval_seconds: 30
          timeout_seconds: 5
          failure_threshold: 3

    memory_management:
      max_memory_mb: 512
      gc_policy: "aggressive|normal|conservative"

    concurrency:
      max_concurrent_operations: 100
      queue_size: 1000
      worker_threads: 4

  configuration:
    environment_variables:
      - name: "{MICROSERVICE_NAME_UPPER}_CONFIG_PATH"
        description: "Path to configuration file"
        required: false
        default: "/etc/{MICROSERVICE_NAME}/config.yaml"

      - name: "{MICROSERVICE_NAME_UPPER}_LOG_LEVEL"
        description: "Logging level"
        required: false
        default: "INFO"
        enum: [DEBUG, INFO, WARN, ERROR]

    container_services:
      - service_name: "{MICROSERVICE_NAME}_config"
        interface: "Model{MICROSERVICE_NAME_PASCAL}Config"
        lifecycle: "singleton"

      - service_name: "{EXTERNAL_SYSTEM}_connection_manager"  
        interface: "{EXTERNAL_SYSTEM_PASCAL}ConnectionManager"
        lifecycle: "singleton"

  monitoring:
    health_endpoints:
      - path: "/health"
        method: "GET"
        response_codes: [200, 503]

      - path: "/health/detailed"
        method: "GET"
        response_codes: [200, 503]
        includes: [dependencies, metrics, circuit_breaker]

    metrics:
      - name: "{MICROSERVICE_NAME}_operations_total"
        type: "counter"
        description: "Total number of operations processed"
        labels: [operation_type, status]

      - name: "{MICROSERVICE_NAME}_duration_seconds"
        type: "histogram"
        description: "Operation duration in seconds"
        labels: [operation_type]
        buckets: [0.001, 0.01, 0.1, 1, 10]

      - name: "{MICROSERVICE_NAME}_circuit_breaker_state"
        type: "gauge"
        description: "Circuit breaker state (0=closed, 1=open, 2=half_open)"

  compliance:
    security:
      - error_sanitization: true
      - input_validation: true
      - correlation_id_validation: true

    onex_standards:
      - node_type: "effect"
      - architecture_version: "4.0"
      - interface_compliance: true
      - health_check_standard: true
```

## 📊 Manifest Templates

### 9. Version Manifest Template

**File**: `manifests/version_manifest.yaml`

```yaml
# Version Manifest for {DOMAIN} {MICROSERVICE_NAME} Effect Node
# Defines version metadata, compatibility, and deployment information

apiVersion: manifests.onex.ai/v1
kind: VersionManifest
metadata:
  name: {MICROSERVICE_NAME}-effect-node
  version: 1.0.0
  domain: {DOMAIN}
  repository: {REPOSITORY_NAME}

spec:
  node_info:
    name: Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect
    type: effect
    architecture: onex-4-node
    domain: {DOMAIN}
    microservice: {MICROSERVICE_NAME}

  version_info:
    version: 1.0.0
    release_date: "2024-01-01"
    stability: "stable"  # alpha|beta|stable|deprecated

  dependencies:
    core:
      omnibase_core: ">=4.0.0,<5.0.0"
      pydantic: ">=2.0.0,<3.0.0"

    optional:
      # Add optional dependencies here

  compatibility:
    python_versions: ["3.11", "3.12"]
    onex_architecture: "4.0"

    compatible_nodes:
      - type: "compute"
        versions: ["1.0.0", "1.1.0"]
      - type: "reducer"
        versions: ["1.0.0"]
      - type: "orchestrator"
        versions: ["1.0.0"]

  deployment:
    container:
      base_image: "python:3.11-slim"
      ports: [8080]
      health_check: "/health"

    resource_requirements:
      cpu: "0.5"
      memory: "512Mi"
      storage: "1Gi"

    environment_variables:
      - name: DEPLOYMENT_ENVIRONMENT
        required: true
        values: ["development", "staging", "production"]

  testing:
    test_coverage: 95.0
    test_suites:
      - unit_tests
      - integration_tests
      - contract_tests
      - security_tests

  documentation:
    readme: README.md
    api_docs: docs/api.md
    contracts: contracts/
    examples: examples/
```

### 10. Compatibility Matrix Template

**File**: `manifests/compatibility_matrix.yaml`

```yaml
# Compatibility Matrix for {DOMAIN} {MICROSERVICE_NAME} Effect Node
# Defines cross-version compatibility and migration paths

apiVersion: manifests.onex.ai/v1
kind: CompatibilityMatrix
metadata:
  name: {MICROSERVICE_NAME}-compatibility-matrix
  domain: {DOMAIN}

spec:
  current_version: 1.0.0

  version_compatibility:
    "1.0.0":
      status: current
      supported_until: "2025-12-31"
      breaking_changes: []
      migration_required: false

    # Add future versions here

  interface_compatibility:
    input_models:
      Model{MICROSERVICE_NAME_PASCAL}Input:
        "1.0.0": "fully_compatible"

    output_models:
      Model{MICROSERVICE_NAME_PASCAL}Output:
        "1.0.0": "fully_compatible"

    operation_types:
      Enum{MICROSERVICE_NAME_PASCAL}OperationType:
        "1.0.0": "fully_compatible"

  dependency_compatibility:
    omnibase_core:
      "4.0.0": "fully_compatible"
      "4.1.0": "fully_compatible"
      "5.0.0": "breaking_changes"

  migration_paths:
    # Define migration paths for future versions
    # "1.0.0->1.1.0":
    #   automated: true
    #   steps: []
    #   data_migration: false

  deprecation_policy:
    notice_period_months: 6
    support_period_months: 12
    removal_timeline: "following_major_version"
```

## 📖 Documentation Template

### 11. README Template

**File**: `README.md`

```markdown
# {DOMAIN_PASCAL} {MICROSERVICE_NAME_PASCAL} Effect Node

**Version**: 1.0.0  
**Type**: EFFECT Node  
**Architecture**: ONEX 4-Node  
**Domain**: {DOMAIN}  

## Overview

{BUSINESS_DESCRIPTION}

This EFFECT node provides {DOMAIN} {MICROSERVICE_NAME} capabilities as a specialized microservice following ONEX 4-node architecture patterns.

## Features

- ✅ **Operation 1**: [Description]
- ✅ **Operation 2**: [Description]
- ✅ **Health Monitoring**: Comprehensive health checks and circuit breaker
- ✅ **Type Safety**: Full Pydantic model validation
- ✅ **Performance**: Sub-second response times with metrics collection
- ✅ **Security**: Error sanitization and input validation
- ✅ **ONEX Compliance**: Full ONEX 4-node architecture compliance

## Quick Start

```python
from {REPOSITORY_NAME}.nodes.node_{DOMAIN}_{MICROSERVICE_NAME}_effect import (
    Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect,
    Model{MICROSERVICE_NAME_PASCAL}Input,
    Enum{MICROSERVICE_NAME_PASCAL}OperationType,
)
from omnibase_core.core.onex_container import ModelONEXContainer
from uuid import uuid4

# Initialize node
container = ModelONEXContainer()
effect_node = Node{DOMAIN_PASCAL}{MICROSERVICE_NAME_PASCAL}Effect(container)

# Create request
request = Model{MICROSERVICE_NAME_PASCAL}Input(
    operation_type=Enum{MICROSERVICE_NAME_PASCAL}OperationType.OPERATION_1,
    correlation_id=uuid4(),
    timestamp=time.time(),
)

# Execute operation
result = await effect_node.process(request)
print(f"Success: {result.success}")
```

## Configuration

The node supports environment-specific configuration:

```python
from {REPOSITORY_NAME}.nodes.node_{DOMAIN}_{MICROSERVICE_NAME}_effect import Model{MICROSERVICE_NAME_PASCAL}Config

# Production configuration
config = Model{MICROSERVICE_NAME_PASCAL}Config.for_environment("production")

# Development configuration
config = Model{MICROSERVICE_NAME_PASCAL}Config.for_environment("development")
```

## Operations

### Operation 1
[Describe operation 1]

### Operation 2  
[Describe operation 2]

### Health Check
Built-in health monitoring with circuit breaker patterns.

## API Reference

### Input Model
- `operation_type`: Type of operation to perform
- `correlation_id`: UUID for request tracing
- `timestamp`: Request timestamp
- `context`: Additional request context

### Output Model
- `success`: Operation success status
- `data`: Operation result data
- `error_message`: Error details (if failed)
- `execution_time_ms`: Processing duration

## Monitoring

The node provides comprehensive monitoring:

- **Metrics**: Operation counts, success rates, execution times
- **Health Checks**: Circuit breaker status, resource availability
- **Tracing**: Full correlation ID tracking

## Development

### Setup
```bash
poetry install
poetry run pytest tests/
```

### Testing
```bash
# Unit tests
poetry run pytest tests/unit/

# Integration tests  
poetry run pytest tests/integration/

# Contract tests
poetry run pytest tests/contracts/
```

## License

MIT License - see LICENSE file for details.
```

## 🚀 Usage Instructions

To use this template:

1. **Replace all placeholders** with actual values:
   - `{REPOSITORY_NAME}` → `omniplan`
   - `{DOMAIN}` → `rsd`
   - `{MICROSERVICE_NAME}` → `priority_storage`
   - `{BUSINESS_DESCRIPTION}` → actual description
   - etc.

2. **Customize operation handlers** in the main node file

3. **Add domain-specific fields** to input/output models

4. **Update contracts** with actual operation specifications  

5. **Implement business logic** in operation handler methods

6. **Add domain-specific configuration** fields

7. **Update documentation** with actual descriptions

This template ensures **consistent EFFECT node patterns** across all OmniNode repositories while maintaining full ONEX compliance and providing a solid foundation for any domain-specific microservice.
