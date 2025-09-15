# COMPUTE Node Template

## Overview

This template provides the unified architecture pattern for ONEX COMPUTE nodes. COMPUTE nodes are responsible for performing business logic computations and data transformations within the ONEX ecosystem.

## Key Characteristics

- **Business Logic Execution**: Core computational logic implementation
- **Data Transformation**: Input processing and output generation
- **Stateless Operations**: No persistent state, purely functional transformations
- **Performance Focus**: Optimized for computational efficiency
- **Type Safety**: Full Pydantic validation with generic typing

## Directory Structure

```
{REPOSITORY_NAME}/
├── src/
│   └── {REPOSITORY_NAME}/
│       └── nodes/
│           └── node_{DOMAIN}_{MICROSERVICE_NAME}_compute/
│               └── v1_0_0/
│                   ├── __init__.py
│                   ├── node.py
│                   ├── config.py
│                   ├── contracts/
│                   │   ├── __init__.py
│                   │   ├── compute_contract.py
│                   │   └── subcontracts/
│                   │       ├── __init__.py
│                   │       ├── input_subcontract.yaml
│                   │       ├── output_subcontract.yaml
│                   │       └── config_subcontract.yaml
│                   ├── models/
│                   │   ├── __init__.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_compute_input.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_compute_output.py
│                   │   └── model_{DOMAIN}_{MICROSERVICE_NAME}_compute_config.py
│                   ├── enums/
│                   │   ├── __init__.py
│                   │   └── enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type.py
│                   ├── utils/
│                   │   ├── __init__.py
│                   │   ├── {DOMAIN}_calculator.py
│                   │   ├── data_transformer.py
│                   │   └── performance_optimizer.py
│                   └── manifest.yaml
└── tests/
    └── {REPOSITORY_NAME}/
        └── nodes/
            └── node_{DOMAIN}_{MICROSERVICE_NAME}_compute/
                └── v1_0_0/
                    ├── test_node.py
                    ├── test_config.py
                    ├── test_contracts.py
                    └── test_models.py
```

## Template Files

### 1. Node Implementation (`node.py`)

```python
"""ONEX COMPUTE node for {DOMAIN} {MICROSERVICE_NAME} operations."""

import asyncio
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
import time
from contextlib import asynccontextmanager

from pydantic import ValidationError
from omnibase_core.nodes.base.node_compute_service import NodeComputeService
from omnibase_core.models.model_onex_error import ModelONEXError
from omnibase_core.models.model_onex_warning import ModelONEXWarning
from omnibase_core.utils.error_sanitizer import ErrorSanitizer
from omnibase_core.utils.circuit_breaker import CircuitBreakerMixin

from .config import {DomainCamelCase}{MicroserviceCamelCase}ComputeConfig
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_compute_input import Model{DomainCamelCase}{MicroserviceCamelCase}ComputeInput
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_compute_output import Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type import Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType
from .utils.{DOMAIN}_calculator import {DomainCamelCase}Calculator
from .utils.data_transformer import DataTransformer
from .utils.performance_optimizer import PerformanceOptimizer


class Node{DomainCamelCase}{MicroserviceCamelCase}Compute(
    NodeComputeService[
        Model{DomainCamelCase}{MicroserviceCamelCase}ComputeInput,
        Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput,
        {DomainCamelCase}{MicroserviceCamelCase}ComputeConfig
    ],
    CircuitBreakerMixin
):
    """COMPUTE node for {DOMAIN} {MICROSERVICE_NAME} computational operations.

    This node provides high-performance computational services for {DOMAIN} domain
    operations, focusing on {MICROSERVICE_NAME} calculations and data transformations.

    Key Features:
    - Sub-{PERFORMANCE_TARGET}ms computation performance
    - Type-safe input/output validation
    - Circuit breaker protection
    - Comprehensive error handling
    - Performance optimization
    """

    def __init__(self, config: {DomainCamelCase}{MicroserviceCamelCase}ComputeConfig):
        """Initialize the COMPUTE node with configuration.

        Args:
            config: Configuration for the compute operations
        """
        super().__init__(config)
        CircuitBreakerMixin.__init__(
            self,
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_timeout,
            expected_exception=Exception
        )

        # Initialize computational components
        self._calculator = {DomainCamelCase}Calculator(config.calculation_config)
        self._transformer = DataTransformer(config.transformation_config)
        self._optimizer = PerformanceOptimizer(config.performance_config)
        self._error_sanitizer = ErrorSanitizer()

        # Performance tracking
        self._computation_metrics = []
        self._operation_counts = {}

    @asynccontextmanager
    async def _performance_tracking(self, operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType):
        """Track performance metrics for computations."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._computation_metrics.append({
                "operation": operation_type,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })
            self._operation_counts[operation_type] = self._operation_counts.get(operation_type, 0) + 1

    async def process(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ComputeInput
    ) -> Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput:
        """Process {DOMAIN} {MICROSERVICE_NAME} computation with typed interface.

        This is the business logic interface that provides type-safe computation
        processing without ONEX infrastructure concerns.

        Args:
            input_data: Validated input data for computation

        Returns:
            Computed output data with results and metadata

        Raises:
            ValidationError: If input validation fails
            ComputationError: If calculation logic fails
            TimeoutError: If computation exceeds time limits
        """
        async with self._performance_tracking(input_data.operation_type):
            try:
                # Pre-computation validation and optimization
                optimized_input = await self._optimizer.optimize_input(input_data)

                # Execute core computation logic
                computation_result = await self._execute_computation(optimized_input)

                # Transform and validate output
                output_data = await self._transformer.transform_output(
                    computation_result,
                    input_data.output_format
                )

                # Post-computation optimization
                optimized_output = await self._optimizer.optimize_output(output_data)

                return Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput(
                    operation_type=input_data.operation_type,
                    computation_result=optimized_output,
                    success=True,
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=(
                        self._computation_metrics[-1]["duration_ms"]
                        if self._computation_metrics else 0.0
                    ),
                    metadata={
                        "input_size": len(str(input_data.computation_data)),
                        "optimization_applied": True,
                        "performance_tier": self._optimizer.get_current_tier()
                    }
                )

            except ValidationError as e:
                sanitized_error = self._error_sanitizer.sanitize_validation_error(str(e))
                return Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    error_message=f"Input validation failed: {sanitized_error}",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=0.0
                )

            except asyncio.TimeoutError:
                return Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    error_message="Computation timeout exceeded",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=self.config.computation_timeout_ms
                )

            except Exception as e:
                sanitized_error = self._error_sanitizer.sanitize_error(str(e))
                return Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    error_message=f"Computation failed: {sanitized_error}",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=0.0
                )

    async def _execute_computation(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ComputeInput
    ) -> Any:
        """Execute the core computational logic.

        Args:
            input_data: Optimized input data

        Returns:
            Raw computation result
        """
        # Apply circuit breaker protection
        async with self.circuit_breaker():
            if input_data.operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.CALCULATE:
                return await self._calculator.calculate(
                    input_data.computation_data,
                    input_data.calculation_parameters
                )

            elif input_data.operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.TRANSFORM:
                return await self._transformer.transform(
                    input_data.computation_data,
                    input_data.transformation_rules
                )

            elif input_data.operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.ANALYZE:
                return await self._calculator.analyze(
                    input_data.computation_data,
                    input_data.analysis_criteria
                )

            else:
                raise ValueError(f"Unsupported operation type: {input_data.operation_type}")

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for monitoring.

        Returns:
            Dictionary with performance statistics
        """
        if not self._computation_metrics:
            return {
                "total_computations": 0,
                "average_duration_ms": 0.0,
                "operation_counts": {},
                "performance_tier": "idle"
            }

        total_computations = len(self._computation_metrics)
        average_duration = sum(m["duration_ms"] for m in self._computation_metrics) / total_computations

        return {
            "total_computations": total_computations,
            "average_duration_ms": round(average_duration, 2),
            "max_duration_ms": max(m["duration_ms"] for m in self._computation_metrics),
            "min_duration_ms": min(m["duration_ms"] for m in self._computation_metrics),
            "operation_counts": self._operation_counts.copy(),
            "performance_tier": self._optimizer.get_current_tier(),
            "circuit_breaker_status": self.circuit_breaker_status
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status information
        """
        try:
            # Test core components
            calculator_healthy = await self._calculator.health_check()
            transformer_healthy = await self._transformer.health_check()
            optimizer_healthy = await self._optimizer.health_check()

            # Check performance metrics
            recent_metrics = [
                m for m in self._computation_metrics
                if time.time() - m["timestamp"] < 300  # Last 5 minutes
            ]

            avg_performance = (
                sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics)
                if recent_metrics else 0.0
            )

            return {
                "status": "healthy" if all([
                    calculator_healthy,
                    transformer_healthy,
                    optimizer_healthy,
                    avg_performance < self.config.performance_threshold_ms
                ]) else "degraded",
                "components": {
                    "calculator": "healthy" if calculator_healthy else "unhealthy",
                    "transformer": "healthy" if transformer_healthy else "unhealthy",
                    "optimizer": "healthy" if optimizer_healthy else "unhealthy"
                },
                "performance": {
                    "average_duration_ms": round(avg_performance, 2),
                    "threshold_ms": self.config.performance_threshold_ms,
                    "recent_computations": len(recent_metrics)
                },
                "circuit_breaker": self.circuit_breaker_status
            }

        except Exception as e:
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))
            return {
                "status": "unhealthy",
                "error": sanitized_error,
                "timestamp": time.time()
            }
```

### 2. Configuration (`config.py`)

```python
"""Configuration for {DOMAIN} {MICROSERVICE_NAME} COMPUTE node."""

from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, Field, validator

from omnibase_core.config.base_node_config import BaseNodeConfig

ConfigT = TypeVar('ConfigT', bound='BaseNodeConfig')


class CalculationConfig(BaseModel):
    """Configuration for calculation operations."""

    precision_digits: int = Field(default=6, ge=1, le=15, description="Numerical precision digits")
    max_iterations: int = Field(default=10000, ge=1, description="Maximum calculation iterations")
    convergence_threshold: float = Field(default=1e-6, ge=1e-12, le=1e-1, description="Convergence threshold")
    parallel_processing: bool = Field(default=True, description="Enable parallel calculation processing")
    optimization_level: str = Field(default="balanced", regex="^(minimal|balanced|aggressive)$", description="Optimization level")


class TransformationConfig(BaseModel):
    """Configuration for data transformation operations."""

    max_input_size_mb: float = Field(default=50.0, ge=0.1, le=1000.0, description="Maximum input size in MB")
    output_compression: bool = Field(default=False, description="Enable output compression")
    validation_level: str = Field(default="strict", regex="^(minimal|standard|strict)$", description="Validation strictness level")
    batch_processing: bool = Field(default=True, description="Enable batch transformation processing")


class PerformanceConfig(BaseModel):
    """Configuration for performance optimization."""

    caching_enabled: bool = Field(default=True, description="Enable result caching")
    cache_size_mb: float = Field(default=100.0, ge=1.0, le=2000.0, description="Cache size in MB")
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86400, description="Cache TTL in seconds")
    adaptive_optimization: bool = Field(default=True, description="Enable adaptive performance optimization")
    memory_limit_mb: float = Field(default=500.0, ge=100.0, le=8192.0, description="Memory usage limit in MB")


class {DomainCamelCase}{MicroserviceCamelCase}ComputeConfig(BaseNodeConfig):
    """Configuration for {DOMAIN} {MICROSERVICE_NAME} COMPUTE operations."""

    # Core computation settings
    computation_timeout_ms: float = Field(
        default=5000.0,
        ge=100.0,
        le=60000.0,
        description="Maximum computation time in milliseconds"
    )

    performance_threshold_ms: float = Field(
        default=1000.0,
        ge=10.0,
        le=10000.0,
        description="Performance threshold for health checks"
    )

    max_concurrent_computations: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum concurrent computation operations"
    )

    # Component configurations
    calculation_config: CalculationConfig = Field(default_factory=CalculationConfig)
    transformation_config: TransformationConfig = Field(default_factory=TransformationConfig)
    performance_config: PerformanceConfig = Field(default_factory=PerformanceConfig)

    # Circuit breaker settings
    circuit_breaker_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Circuit breaker failure threshold"
    )

    circuit_breaker_timeout: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Circuit breaker recovery timeout in seconds"
    )

    # Domain-specific settings
    domain_specific_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific configuration parameters"
    )

    @validator('computation_timeout_ms')
    def validate_timeout(cls, v, values):
        """Ensure computation timeout is reasonable for the performance threshold."""
        threshold = values.get('performance_threshold_ms', 1000.0)
        if v < threshold:
            raise ValueError(f"Computation timeout ({v}ms) must be >= performance threshold ({threshold}ms)")
        return v

    @validator('max_concurrent_computations')
    def validate_concurrency(cls, v, values):
        """Ensure concurrency settings are appropriate for the configuration."""
        if 'performance_config' in values:
            memory_limit = values['performance_config'].memory_limit_mb
            estimated_memory_per_computation = 10.0  # MB estimate
            max_by_memory = int(memory_limit / estimated_memory_per_computation)
            if v > max_by_memory:
                raise ValueError(f"Concurrent computations ({v}) may exceed memory limit. Max recommended: {max_by_memory}")
        return v

    @classmethod
    def for_environment(cls: Type[ConfigT], environment: str) -> ConfigT:
        """Create environment-specific configuration.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Environment-optimized configuration
        """
        if environment == "production":
            return cls(
                computation_timeout_ms=3000.0,
                performance_threshold_ms=500.0,
                max_concurrent_computations=100,
                calculation_config=CalculationConfig(
                    precision_digits=8,
                    optimization_level="aggressive",
                    parallel_processing=True
                ),
                performance_config=PerformanceConfig(
                    cache_size_mb=500.0,
                    cache_ttl_seconds=600,
                    adaptive_optimization=True,
                    memory_limit_mb=1024.0
                ),
                circuit_breaker_threshold=3,
                circuit_breaker_timeout=30
            )

        elif environment == "staging":
            return cls(
                computation_timeout_ms=5000.0,
                performance_threshold_ms=1000.0,
                max_concurrent_computations=50,
                calculation_config=CalculationConfig(
                    precision_digits=6,
                    optimization_level="balanced"
                ),
                performance_config=PerformanceConfig(
                    cache_size_mb=200.0,
                    memory_limit_mb=512.0
                )
            )

        else:  # development
            return cls(
                computation_timeout_ms=10000.0,
                performance_threshold_ms=2000.0,
                max_concurrent_computations=20,
                calculation_config=CalculationConfig(
                    precision_digits=4,
                    optimization_level="minimal",
                    parallel_processing=False
                ),
                performance_config=PerformanceConfig(
                    cache_size_mb=50.0,
                    adaptive_optimization=False,
                    memory_limit_mb=256.0
                )
            )

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "computation_timeout_ms": 5000.0,
                "performance_threshold_ms": 1000.0,
                "max_concurrent_computations": 50,
                "calculation_config": {
                    "precision_digits": 6,
                    "max_iterations": 10000,
                    "optimization_level": "balanced"
                },
                "performance_config": {
                    "caching_enabled": True,
                    "cache_size_mb": 100.0,
                    "adaptive_optimization": True
                }
            }
        }
```

### 3. Input Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_compute_input.py`)

```python
"""Input model for {DOMAIN} {MICROSERVICE_NAME} COMPUTE operations."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator

from ..enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type import Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType


class Model{DomainCamelCase}{MicroserviceCamelCase}ComputeInput(BaseModel):
    """Input model for {DOMAIN} {MICROSERVICE_NAME} computation operations."""

    operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType = Field(
        description="Type of computation operation to perform"
    )

    computation_data: Dict[str, Any] = Field(
        description="Primary data for computation processing"
    )

    correlation_id: UUID = Field(
        description="Request correlation ID for tracing"
    )

    # Operation-specific parameters
    calculation_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters for calculation operations"
    )

    transformation_rules: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Rules for data transformation operations"
    )

    analysis_criteria: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Criteria for analysis operations"
    )

    # Output control
    output_format: str = Field(
        default="standard",
        regex="^(minimal|standard|detailed|raw)$",
        description="Desired output format level"
    )

    include_metadata: bool = Field(
        default=True,
        description="Include processing metadata in output"
    )

    # Performance hints
    priority_level: str = Field(
        default="normal",
        regex="^(low|normal|high|critical)$",
        description="Processing priority level"
    )

    max_processing_time_ms: Optional[float] = Field(
        default=None,
        ge=100.0,
        le=60000.0,
        description="Maximum allowed processing time in milliseconds"
    )

    # Context information
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional processing context"
    )

    request_timestamp: float = Field(
        description="Request timestamp as Unix timestamp",
        ge=0
    )

    @validator('computation_data')
    def validate_computation_data(cls, v, values):
        """Validate computation data based on operation type."""
        operation_type = values.get('operation_type')

        if not isinstance(v, dict) or not v:
            raise ValueError("Computation data must be a non-empty dictionary")

        if operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.CALCULATE:
            required_fields = ['input_values', 'calculation_type']
            missing_fields = [field for field in required_fields if field not in v]
            if missing_fields:
                raise ValueError(f"Calculate operation missing required fields: {missing_fields}")

        elif operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.TRANSFORM:
            if 'source_data' not in v:
                raise ValueError("Transform operation requires 'source_data' field")

        elif operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.ANALYZE:
            if 'analysis_target' not in v:
                raise ValueError("Analyze operation requires 'analysis_target' field")

        return v

    @validator('calculation_parameters')
    def validate_calculation_parameters(cls, v, values):
        """Validate calculation parameters when provided."""
        operation_type = values.get('operation_type')

        if operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.CALCULATE and v is None:
            raise ValueError("Calculate operation requires calculation_parameters")

        if v is not None and operation_type != Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.CALCULATE:
            raise ValueError(f"calculation_parameters only valid for CALCULATE operation, got {operation_type}")

        return v

    @validator('transformation_rules')
    def validate_transformation_rules(cls, v, values):
        """Validate transformation rules when provided."""
        operation_type = values.get('operation_type')

        if operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.TRANSFORM and v is None:
            raise ValueError("Transform operation requires transformation_rules")

        if v is not None:
            if operation_type != Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.TRANSFORM:
                raise ValueError(f"transformation_rules only valid for TRANSFORM operation, got {operation_type}")

            # Validate rule structure
            for i, rule in enumerate(v):
                if not isinstance(rule, dict):
                    raise ValueError(f"Transformation rule {i} must be a dictionary")
                if 'rule_type' not in rule:
                    raise ValueError(f"Transformation rule {i} missing 'rule_type'")

        return v

    @validator('analysis_criteria')
    def validate_analysis_criteria(cls, v, values):
        """Validate analysis criteria when provided."""
        operation_type = values.get('operation_type')

        if operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.ANALYZE and v is None:
            raise ValueError("Analyze operation requires analysis_criteria")

        if v is not None and operation_type != Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.ANALYZE:
            raise ValueError(f"analysis_criteria only valid for ANALYZE operation, got {operation_type}")

        return v

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "operation_type": "calculate",
                "computation_data": {
                    "input_values": [1, 2, 3, 4, 5],
                    "calculation_type": "statistical_analysis"
                },
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                "calculation_parameters": {
                    "method": "mean_variance",
                    "confidence_level": 0.95
                },
                "output_format": "detailed",
                "include_metadata": True,
                "priority_level": "normal",
                "request_timestamp": 1640995200.0
            }
        }
```

### 4. Output Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_compute_output.py`)

```python
"""Output model for {DOMAIN} {MICROSERVICE_NAME} COMPUTE operations."""

from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from ..enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type import Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType


class Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput(BaseModel):
    """Output model for {DOMAIN} {MICROSERVICE_NAME} computation operations."""

    operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType = Field(
        description="Type of operation that was executed"
    )

    computation_result: Optional[Any] = Field(
        default=None,
        description="Primary computation result data"
    )

    success: bool = Field(
        description="Whether the computation was successful"
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Error message if computation failed"
    )

    correlation_id: UUID = Field(
        description="Request correlation ID for tracing"
    )

    timestamp: float = Field(
        description="Response timestamp as Unix timestamp",
        ge=0
    )

    processing_time_ms: float = Field(
        description="Total computation processing time in milliseconds",
        ge=0
    )

    # Computation metrics
    computation_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed computation performance metrics"
    )

    # Result metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional result metadata and context"
    )

    # Quality indicators
    result_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the computation result"
    )

    optimization_applied: Optional[bool] = Field(
        default=None,
        description="Whether performance optimizations were applied"
    )

    # Resource usage
    memory_usage_mb: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Memory usage during computation in MB"
    )

    cpu_utilization_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="CPU utilization percentage during computation"
    )

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "operation_type": "calculate",
                "computation_result": {
                    "mean": 3.0,
                    "variance": 2.5,
                    "standard_deviation": 1.58,
                    "confidence_interval": [2.1, 3.9]
                },
                "success": True,
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": 1640995205.123,
                "processing_time_ms": 45.7,
                "computation_metrics": {
                    "iterations_required": 1,
                    "convergence_achieved": True,
                    "optimization_level": "balanced"
                },
                "metadata": {
                    "input_size": 5,
                    "output_format": "detailed",
                    "calculation_method": "analytical"
                },
                "result_confidence": 0.98,
                "optimization_applied": True,
                "memory_usage_mb": 12.4,
                "cpu_utilization_percent": 23.7
            }
        }
```

### 5. Operation Type Enum (`enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type.py`)

```python
"""Operation type enumeration for {DOMAIN} {MICROSERVICE_NAME} COMPUTE operations."""

from enum import Enum


class Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType(str, Enum):
    """Enumeration of supported {DOMAIN} {MICROSERVICE_NAME} computation operation types."""

    CALCULATE = "calculate"
    """Perform mathematical calculations and statistical analysis."""

    TRANSFORM = "transform"
    """Transform data from one format or structure to another."""

    ANALYZE = "analyze"
    """Analyze data patterns, trends, and characteristics."""

    OPTIMIZE = "optimize"
    """Optimize data structures or computational parameters."""

    VALIDATE = "validate"
    """Validate data integrity and business rule compliance."""

    AGGREGATE = "aggregate"
    """Aggregate multiple data sources or results."""

    FILTER = "filter"
    """Filter data based on specified criteria."""

    SORT = "sort"
    """Sort data according to specified ordering rules."""

    BATCH_PROCESS = "batch_process"
    """Process multiple computation requests in batch mode."""

    HEALTH_CHECK = "health_check"
    """Perform system health and performance validation."""

    @classmethod
    def get_computational_operations(cls):
        """Get operations that involve core computational logic."""
        return [
            cls.CALCULATE,
            cls.TRANSFORM,
            cls.ANALYZE,
            cls.OPTIMIZE,
            cls.AGGREGATE
        ]

    @classmethod
    def get_data_operations(cls):
        """Get operations that primarily manipulate data structure."""
        return [
            cls.FILTER,
            cls.SORT,
            cls.VALIDATE,
            cls.BATCH_PROCESS
        ]

    @classmethod
    def get_system_operations(cls):
        """Get operations related to system management."""
        return [
            cls.HEALTH_CHECK
        ]

    def is_computational(self) -> bool:
        """Check if this operation involves core computational logic."""
        return self in self.get_computational_operations()

    def is_data_operation(self) -> bool:
        """Check if this operation primarily manipulates data."""
        return self in self.get_data_operations()

    def is_system_operation(self) -> bool:
        """Check if this operation is system-related."""
        return self in self.get_system_operations()

    def get_expected_performance_ms(self) -> float:
        """Get expected performance threshold for this operation type."""
        performance_map = {
            cls.CALCULATE: 1000.0,
            cls.TRANSFORM: 500.0,
            cls.ANALYZE: 2000.0,
            cls.OPTIMIZE: 5000.0,
            cls.VALIDATE: 200.0,
            cls.AGGREGATE: 1500.0,
            cls.FILTER: 300.0,
            cls.SORT: 800.0,
            cls.BATCH_PROCESS: 10000.0,
            cls.HEALTH_CHECK: 100.0
        }
        return performance_map.get(self, 1000.0)

    def requires_high_precision(self) -> bool:
        """Check if this operation requires high numerical precision."""
        return self in [
            cls.CALCULATE,
            cls.ANALYZE,
            cls.OPTIMIZE
        ]

    def supports_parallel_processing(self) -> bool:
        """Check if this operation supports parallel processing."""
        return self in [
            cls.CALCULATE,
            cls.TRANSFORM,
            cls.BATCH_PROCESS,
            cls.AGGREGATE,
            cls.FILTER,
            cls.SORT
        ]
```

### 6. YAML Subcontracts

#### Input Subcontract (`subcontracts/input_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} COMPUTE Input Subcontract
# Defines the expected input structure for computation operations

api_version: "v1.0.0"
kind: "InputSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-compute-input"
  description: "Input contract for {DOMAIN} {MICROSERVICE_NAME} computation operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "COMPUTE"

schema:
  type: "object"
  required:
    - "operation_type"
    - "computation_data"
    - "correlation_id"
    - "request_timestamp"

  properties:
    operation_type:
      type: "string"
      enum:
        - "calculate"
        - "transform"
        - "analyze"
        - "optimize"
        - "validate"
        - "aggregate"
        - "filter"
        - "sort"
        - "batch_process"
        - "health_check"
      description: "Type of computation operation to perform"

    computation_data:
      type: "object"
      minProperties: 1
      description: "Primary data for computation processing"
      # Schema varies by operation_type - validated at runtime

    correlation_id:
      type: "string"
      format: "uuid"
      description: "Request correlation ID for tracing"

    calculation_parameters:
      type: ["object", "null"]
      description: "Parameters for calculation operations"
      properties:
        method:
          type: "string"
          description: "Calculation method identifier"
        precision:
          type: "integer"
          minimum: 1
          maximum: 15
          description: "Numerical precision requirements"
        convergence_criteria:
          type: "object"
          description: "Convergence criteria for iterative calculations"

    transformation_rules:
      type: ["array", "null"]
      description: "Rules for data transformation operations"
      items:
        type: "object"
        required: ["rule_type"]
        properties:
          rule_type:
            type: "string"
            description: "Type of transformation rule"
          parameters:
            type: "object"
            description: "Rule-specific parameters"

    analysis_criteria:
      type: ["object", "null"]
      description: "Criteria for analysis operations"
      properties:
        analysis_type:
          type: "string"
          description: "Type of analysis to perform"
        parameters:
          type: "object"
          description: "Analysis-specific parameters"

    output_format:
      type: "string"
      enum: ["minimal", "standard", "detailed", "raw"]
      default: "standard"
      description: "Desired output format level"

    include_metadata:
      type: "boolean"
      default: true
      description: "Include processing metadata in output"

    priority_level:
      type: "string"
      enum: ["low", "normal", "high", "critical"]
      default: "normal"
      description: "Processing priority level"

    max_processing_time_ms:
      type: ["number", "null"]
      minimum: 100
      maximum: 60000
      description: "Maximum allowed processing time in milliseconds"

    context:
      type: ["object", "null"]
      description: "Additional processing context"

    request_timestamp:
      type: "number"
      minimum: 0
      description: "Request timestamp as Unix timestamp"

validation_rules:
  - name: "operation_specific_parameters"
    description: "Validate operation-specific parameters are provided"
    rule: |
      if operation_type == "calculate":
        assert calculation_parameters is not None
      elif operation_type == "transform":
        assert transformation_rules is not None
      elif operation_type == "analyze":
        assert analysis_criteria is not None

  - name: "computation_data_structure"
    description: "Validate computation data structure based on operation"
    rule: |
      if operation_type == "calculate":
        assert "input_values" in computation_data
        assert "calculation_type" in computation_data
      elif operation_type == "transform":
        assert "source_data" in computation_data
      elif operation_type == "analyze":
        assert "analysis_target" in computation_data

  - name: "performance_constraints"
    description: "Validate performance constraints are reasonable"
    rule: |
      if max_processing_time_ms is not None:
        expected_time = get_expected_performance_for_operation(operation_type)
        assert max_processing_time_ms >= expected_time * 0.1

examples:
  - name: "statistical_calculation"
    description: "Statistical calculation operation"
    data:
      operation_type: "calculate"
      computation_data:
        input_values: [1, 2, 3, 4, 5]
        calculation_type: "descriptive_statistics"
      correlation_id: "550e8400-e29b-41d4-a716-446655440000"
      calculation_parameters:
        method: "analytical"
        precision: 6
      output_format: "detailed"
      priority_level: "normal"
      request_timestamp: 1640995200.0

  - name: "data_transformation"
    description: "Data format transformation"
    data:
      operation_type: "transform"
      computation_data:
        source_data:
          format: "csv"
          content: "name,age,city\nJohn,30,NYC"
      correlation_id: "550e8400-e29b-41d4-a716-446655440001"
      transformation_rules:
        - rule_type: "format_conversion"
          parameters:
            target_format: "json"
            include_headers: true
      output_format: "standard"
      request_timestamp: 1640995200.0
```

### 7. Output Subcontract (`subcontracts/output_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} COMPUTE Output Subcontract
# Defines the expected output structure for computation operations

api_version: "v1.0.0"
kind: "OutputSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-compute-output"
  description: "Output contract for {DOMAIN} {MICROSERVICE_NAME} computation operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "COMPUTE"

schema:
  type: "object"
  required:
    - "operation_type"
    - "success"
    - "correlation_id"
    - "timestamp"
    - "processing_time_ms"

  properties:
    operation_type:
      type: "string"
      enum:
        - "calculate"
        - "transform"
        - "analyze"
        - "optimize"
        - "validate"
        - "aggregate"
        - "filter"
        - "sort"
        - "batch_process"
        - "health_check"
      description: "Type of operation that was executed"

    computation_result:
      description: "Primary computation result data"
      # Type varies based on operation - can be any valid result

    success:
      type: "boolean"
      description: "Whether the computation was successful"

    error_message:
      type: ["string", "null"]
      description: "Error message if computation failed"

    correlation_id:
      type: "string"
      format: "uuid"
      description: "Request correlation ID for tracing"

    timestamp:
      type: "number"
      minimum: 0
      description: "Response timestamp as Unix timestamp"

    processing_time_ms:
      type: "number"
      minimum: 0
      description: "Total computation processing time in milliseconds"

    computation_metrics:
      type: ["object", "null"]
      description: "Detailed computation performance metrics"
      properties:
        iterations_required:
          type: "integer"
          minimum: 0
          description: "Number of computation iterations required"
        convergence_achieved:
          type: "boolean"
          description: "Whether iterative computation converged"
        optimization_level:
          type: "string"
          description: "Level of optimization applied"
        memory_efficiency:
          type: "number"
          minimum: 0
          maximum: 1
          description: "Memory efficiency score (0-1)"

    metadata:
      type: ["object", "null"]
      description: "Additional result metadata and context"
      properties:
        input_size:
          type: "integer"
          minimum: 0
          description: "Size of input data processed"
        output_format:
          type: "string"
          description: "Format of the output data"
        calculation_method:
          type: "string"
          description: "Method used for calculation"
        data_quality_score:
          type: "number"
          minimum: 0
          maximum: 1
          description: "Quality score of input data (0-1)"

    result_confidence:
      type: ["number", "null"]
      minimum: 0
      maximum: 1
      description: "Confidence score for the computation result"

    optimization_applied:
      type: ["boolean", "null"]
      description: "Whether performance optimizations were applied"

    memory_usage_mb:
      type: ["number", "null"]
      minimum: 0
      description: "Memory usage during computation in MB"

    cpu_utilization_percent:
      type: ["number", "null"]
      minimum: 0
      maximum: 100
      description: "CPU utilization percentage during computation"

validation_rules:
  - name: "success_result_consistency"
    description: "Validate success flag consistency with result presence"
    rule: |
      if success == true:
        assert error_message is None
        if operation_type != "health_check":
          assert computation_result is not None
      else:
        assert error_message is not None
        assert len(error_message.strip()) > 0

  - name: "performance_thresholds"
    description: "Validate performance metrics are within expected ranges"
    rule: |
      expected_time = get_expected_performance_for_operation(operation_type)
      if processing_time_ms > expected_time * 2:
        # Performance degradation detected - should be logged
        pass

  - name: "confidence_score_validity"
    description: "Validate confidence scores are reasonable"
    rule: |
      if result_confidence is not None:
        if success == false:
          assert result_confidence == 0.0
        else:
          assert 0.0 <= result_confidence <= 1.0

performance_guarantees:
  - operation_type: "calculate"
    max_processing_time_ms: 1000
    typical_processing_time_ms: 200
  - operation_type: "transform"
    max_processing_time_ms: 500
    typical_processing_time_ms: 100
  - operation_type: "analyze"
    max_processing_time_ms: 2000
    typical_processing_time_ms: 500
  - operation_type: "health_check"
    max_processing_time_ms: 100
    typical_processing_time_ms: 20

examples:
  - name: "successful_calculation"
    description: "Successful statistical calculation result"
    data:
      operation_type: "calculate"
      computation_result:
        mean: 3.0
        variance: 2.5
        standard_deviation: 1.58
        confidence_interval: [2.1, 3.9]
      success: true
      correlation_id: "550e8400-e29b-41d4-a716-446655440000"
      timestamp: 1640995205.123
      processing_time_ms: 45.7
      computation_metrics:
        iterations_required: 1
        convergence_achieved: true
        optimization_level: "balanced"
        memory_efficiency: 0.92
      metadata:
        input_size: 5
        output_format: "detailed"
        calculation_method: "analytical"
        data_quality_score: 0.98
      result_confidence: 0.98
      optimization_applied: true
      memory_usage_mb: 12.4
      cpu_utilization_percent: 23.7

  - name: "failed_computation"
    description: "Failed computation with error details"
    data:
      operation_type: "calculate"
      success: false
      error_message: "Invalid input: computation data contains non-numeric values"
      correlation_id: "550e8400-e29b-41d4-a716-446655440001"
      timestamp: 1640995206.456
      processing_time_ms: 5.2
      result_confidence: 0.0
```

### 8. Config Subcontract (`subcontracts/config_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} COMPUTE Config Subcontract
# Defines the configuration schema for computation operations

api_version: "v1.0.0"
kind: "ConfigSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-compute-config"
  description: "Configuration contract for {DOMAIN} {MICROSERVICE_NAME} computation operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "COMPUTE"

schema:
  type: "object"
  required:
    - "computation_timeout_ms"
    - "performance_threshold_ms"
    - "max_concurrent_computations"

  properties:
    # Core computation settings
    computation_timeout_ms:
      type: "number"
      minimum: 100
      maximum: 60000
      default: 5000
      description: "Maximum computation time in milliseconds"

    performance_threshold_ms:
      type: "number"
      minimum: 10
      maximum: 10000
      default: 1000
      description: "Performance threshold for health checks"

    max_concurrent_computations:
      type: "integer"
      minimum: 1
      maximum: 1000
      default: 50
      description: "Maximum concurrent computation operations"

    # Calculation configuration
    calculation_config:
      type: "object"
      properties:
        precision_digits:
          type: "integer"
          minimum: 1
          maximum: 15
          default: 6
          description: "Numerical precision digits"
        max_iterations:
          type: "integer"
          minimum: 1
          default: 10000
          description: "Maximum calculation iterations"
        convergence_threshold:
          type: "number"
          minimum: 1e-12
          maximum: 1e-1
          default: 1e-6
          description: "Convergence threshold"
        parallel_processing:
          type: "boolean"
          default: true
          description: "Enable parallel calculation processing"
        optimization_level:
          type: "string"
          enum: ["minimal", "balanced", "aggressive"]
          default: "balanced"
          description: "Optimization level"

    # Transformation configuration
    transformation_config:
      type: "object"
      properties:
        max_input_size_mb:
          type: "number"
          minimum: 0.1
          maximum: 1000
          default: 50
          description: "Maximum input size in MB"
        output_compression:
          type: "boolean"
          default: false
          description: "Enable output compression"
        validation_level:
          type: "string"
          enum: ["minimal", "standard", "strict"]
          default: "strict"
          description: "Validation strictness level"
        batch_processing:
          type: "boolean"
          default: true
          description: "Enable batch transformation processing"

    # Performance configuration
    performance_config:
      type: "object"
      properties:
        caching_enabled:
          type: "boolean"
          default: true
          description: "Enable result caching"
        cache_size_mb:
          type: "number"
          minimum: 1
          maximum: 2000
          default: 100
          description: "Cache size in MB"
        cache_ttl_seconds:
          type: "integer"
          minimum: 1
          maximum: 86400
          default: 300
          description: "Cache TTL in seconds"
        adaptive_optimization:
          type: "boolean"
          default: true
          description: "Enable adaptive performance optimization"
        memory_limit_mb:
          type: "number"
          minimum: 100
          maximum: 8192
          default: 500
          description: "Memory usage limit in MB"

    # Circuit breaker settings
    circuit_breaker_threshold:
      type: "integer"
      minimum: 1
      maximum: 100
      default: 5
      description: "Circuit breaker failure threshold"

    circuit_breaker_timeout:
      type: "integer"
      minimum: 1
      maximum: 3600
      default: 60
      description: "Circuit breaker recovery timeout in seconds"

    # Domain-specific settings
    domain_specific_config:
      type: "object"
      description: "Domain-specific configuration parameters"
      additionalProperties: true

validation_rules:
  - name: "timeout_threshold_consistency"
    description: "Computation timeout must be >= performance threshold"
    rule: |
      computation_timeout_ms >= performance_threshold_ms

  - name: "memory_concurrency_balance"
    description: "Memory limit should accommodate concurrent operations"
    rule: |
      estimated_memory_per_op = 10  # MB
      max_memory_usage = max_concurrent_computations * estimated_memory_per_op
      if performance_config and "memory_limit_mb" in performance_config:
        max_memory_usage <= performance_config["memory_limit_mb"] * 1.2

  - name: "cache_size_reasonable"
    description: "Cache size should not exceed 50% of memory limit"
    rule: |
      if performance_config:
        cache_size = performance_config.get("cache_size_mb", 100)
        memory_limit = performance_config.get("memory_limit_mb", 500)
        cache_size <= memory_limit * 0.5

environment_profiles:
  production:
    computation_timeout_ms: 3000
    performance_threshold_ms: 500
    max_concurrent_computations: 100
    calculation_config:
      precision_digits: 8
      optimization_level: "aggressive"
      parallel_processing: true
    performance_config:
      cache_size_mb: 500
      cache_ttl_seconds: 600
      adaptive_optimization: true
      memory_limit_mb: 1024
    circuit_breaker_threshold: 3
    circuit_breaker_timeout: 30

  staging:
    computation_timeout_ms: 5000
    performance_threshold_ms: 1000
    max_concurrent_computations: 50
    calculation_config:
      precision_digits: 6
      optimization_level: "balanced"
    performance_config:
      cache_size_mb: 200
      memory_limit_mb: 512

  development:
    computation_timeout_ms: 10000
    performance_threshold_ms: 2000
    max_concurrent_computations: 20
    calculation_config:
      precision_digits: 4
      optimization_level: "minimal"
      parallel_processing: false
    performance_config:
      cache_size_mb: 50
      adaptive_optimization: false
      memory_limit_mb: 256

examples:
  - name: "production_config"
    description: "Production-optimized configuration"
    data:
      computation_timeout_ms: 3000
      performance_threshold_ms: 500
      max_concurrent_computations: 100
      calculation_config:
        precision_digits: 8
        max_iterations: 50000
        convergence_threshold: 1e-8
        parallel_processing: true
        optimization_level: "aggressive"
      performance_config:
        caching_enabled: true
        cache_size_mb: 500
        cache_ttl_seconds: 600
        adaptive_optimization: true
        memory_limit_mb: 1024
      circuit_breaker_threshold: 3
      circuit_breaker_timeout: 30

  - name: "development_config"
    description: "Development-friendly configuration"
    data:
      computation_timeout_ms: 10000
      performance_threshold_ms: 2000
      max_concurrent_computations: 20
      calculation_config:
        precision_digits: 4
        max_iterations: 5000
        optimization_level: "minimal"
        parallel_processing: false
      performance_config:
        caching_enabled: true
        cache_size_mb: 50
        adaptive_optimization: false
        memory_limit_mb: 256
      circuit_breaker_threshold: 10
      circuit_breaker_timeout: 120
```

### 9. Manifest (`manifest.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} COMPUTE Node Manifest
# Defines metadata, dependencies, and deployment specifications

api_version: "v1.0.0"
kind: "NodeManifest"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-compute"
  description: "COMPUTE node for {DOMAIN} {MICROSERVICE_NAME} operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  microservice_name: "{MICROSERVICE_NAME}"
  node_type: "COMPUTE"
  created_at: "2024-01-15T10:00:00Z"
  updated_at: "2024-01-15T10:00:00Z"
  maintainers:
    - "team@{DOMAIN}.com"
  tags:
    - "compute"
    - "calculation"
    - "data-transformation"
    - "{DOMAIN}"
    - "onex-v4"

specification:
  # Node classification
  node_class: "COMPUTE"
  processing_type: "synchronous"
  stateful: false

  # Performance characteristics
  performance:
    expected_latency_ms: 500
    max_latency_ms: 5000
    throughput_ops_per_second: 1000
    memory_requirement_mb: 256
    cpu_requirement_cores: 1.0
    scaling_factor: "horizontal"

  # Operational requirements
  reliability:
    availability_target: "99.9%"
    error_rate_target: "0.1%"
    recovery_time_target_seconds: 30
    circuit_breaker_enabled: true
    retry_policy: "exponential_backoff"

  # Resource management
  resources:
    memory:
      min_mb: 128
      max_mb: 1024
      typical_mb: 256
    cpu:
      min_cores: 0.5
      max_cores: 4.0
      typical_cores: 1.0
    storage:
      temp_space_mb: 100
      cache_space_mb: 200

  # Security requirements
  security:
    input_validation: "strict"
    output_sanitization: "enabled"
    audit_logging: "enabled"
    encryption_at_rest: "not_required"
    encryption_in_transit: "required"

# Dependency specifications
dependencies:
  runtime:
    python: ">=3.11,<4.0"
    pydantic: ">=2.0.0"
    asyncio: "builtin"

  internal:
    omnibase_core:
      version: ">=2.0.0"
      components:
        - "nodes.base.node_compute_service"
        - "models.model_onex_error"
        - "models.model_onex_warning"
        - "utils.error_sanitizer"
        - "utils.circuit_breaker"

  external:
    numpy: ">=1.24.0"  # For numerical computations
    scipy: ">=1.10.0"  # For advanced calculations
    pandas: ">=2.0.0"  # For data transformation

  optional:
    redis: ">=4.0.0"    # For caching
    prometheus_client: ">=0.16.0"  # For metrics

# Interface contracts
contracts:
  input:
    contract_file: "subcontracts/input_subcontract.yaml"
    validation_level: "strict"

  output:
    contract_file: "subcontracts/output_subcontract.yaml"
    validation_level: "strict"

  config:
    contract_file: "subcontracts/config_subcontract.yaml"
    validation_level: "strict"

# API specification
api:
  endpoints:
    compute:
      path: "/api/v1/compute"
      method: "POST"
      input_model: "Model{DomainCamelCase}{MicroserviceCamelCase}ComputeInput"
      output_model: "Model{DomainCamelCase}{MicroserviceCamelCase}ComputeOutput"
      timeout_ms: 30000
      rate_limit: "1000/minute"

    health:
      path: "/health"
      method: "GET"
      timeout_ms: 5000
      rate_limit: "100/minute"

    metrics:
      path: "/metrics"
      method: "GET"
      timeout_ms: 10000
      rate_limit: "10/minute"

# Testing requirements
testing:
  unit_tests:
    coverage_minimum: 90
    test_files:
      - "test_node.py"
      - "test_config.py"
      - "test_models.py"
      - "test_contracts.py"

  integration_tests:
    required: true
    test_scenarios:
      - "basic_computation"
      - "error_handling"
      - "performance_limits"
      - "circuit_breaker_activation"

  performance_tests:
    required: true
    benchmarks:
      - name: "latency_p99"
        target: "< 1000ms"
        measurement: "response_time"
      - name: "throughput"
        target: "> 500 ops/sec"
        measurement: "operations_per_second"
      - name: "memory_efficiency"
        target: "< 256MB typical"
        measurement: "memory_usage"

# Deployment configuration
deployment:
  container:
    base_image: "python:3.11-slim"
    entrypoint: "python -m {REPOSITORY_NAME}.nodes.node_{DOMAIN}_{MICROSERVICE_NAME}_compute.v1_0_0.node"
    healthcheck:
      endpoint: "/health"
      interval_seconds: 30
      timeout_seconds: 5
      retries: 3

  scaling:
    min_replicas: 1
    max_replicas: 10
    target_cpu_utilization: 70
    target_memory_utilization: 80

  environment_variables:
    required:
      - "ONEX_ENVIRONMENT"
      - "NODE_CONFIG_PATH"
    optional:
      - "REDIS_URL"
      - "METRICS_ENDPOINT"
      - "LOG_LEVEL"

# Monitoring and observability
monitoring:
  metrics:
    - name: "computation_duration_seconds"
      type: "histogram"
      description: "Time spent on computation operations"
      labels: ["operation_type", "success"]

    - name: "computation_errors_total"
      type: "counter"
      description: "Total computation errors"
      labels: ["error_type", "operation_type"]

    - name: "concurrent_computations"
      type: "gauge"
      description: "Number of concurrent computations"

    - name: "memory_usage_bytes"
      type: "gauge"
      description: "Current memory usage"

    - name: "circuit_breaker_state"
      type: "gauge"
      description: "Circuit breaker state (0=closed, 1=open, 2=half-open)"

  logging:
    level: "INFO"
    format: "structured_json"
    fields:
      - "timestamp"
      - "level"
      - "correlation_id"
      - "operation_type"
      - "processing_time_ms"
      - "success"
      - "error_message"

  alerts:
    - name: "high_error_rate"
      condition: "error_rate > 5%"
      severity: "warning"
      notification: "team_channel"

    - name: "high_latency"
      condition: "p99_latency > 2000ms"
      severity: "warning"
      notification: "team_channel"

    - name: "circuit_breaker_open"
      condition: "circuit_breaker_state == 1"
      severity: "critical"
      notification: "oncall"

# Documentation
documentation:
  readme: "README.md"
  api_docs: "docs/api.md"
  deployment_guide: "docs/deployment.md"
  troubleshooting: "docs/troubleshooting.md"
  examples: "examples/"

# Compliance and governance
compliance:
  code_quality:
    linting: "enabled"
    type_checking: "strict"
    security_scanning: "enabled"
    dependency_scanning: "enabled"

  security:
    vulnerability_scanning: "required"
    penetration_testing: "recommended"
    access_controls: "rbac"

  data_governance:
    data_classification: "internal"
    retention_policy: "30_days_logs"
    privacy_controls: "none_required"

# Lifecycle management
lifecycle:
  deprecation_policy: "6_months_notice"
  upgrade_path: "rolling_deployment"
  backward_compatibility: "1_major_version"
  support_window: "24_months"

# Integration points
integrations:
  upstream_nodes:
    - node_type: "ORCHESTRATOR"
      interface: "onex_standard"
      data_flow: "request_response"

  downstream_nodes:
    - node_type: "EFFECT"
      interface: "onex_standard"
      data_flow: "fire_and_forget"

  external_services:
    - service_type: "cache"
      protocol: "redis"
      optional: true
    - service_type: "metrics"
      protocol: "prometheus"
      optional: true
```

## Usage Instructions

### Template Customization

Replace the following placeholders throughout all files:

- `{REPOSITORY_NAME}`: Target repository name (e.g., "omniplan")
- `{DOMAIN}`: Business domain (e.g., "rsd", "finance", "analytics")  
- `{MICROSERVICE_NAME}`: Specific microservice name (e.g., "priority_calculator")
- `{DomainCamelCase}`: Domain in CamelCase (e.g., "RSD", "Finance")
- `{MicroserviceCamelCase}`: Microservice in CamelCase (e.g., "PriorityCalculator")
- `{PERFORMANCE_TARGET}`: Performance target (e.g., "100", "500", "1000")

### Key Architectural Features

1. **Dual Interface Pattern**: Typed `process()` method + ONEX-compliant `compute()` method
2. **Generic Type Safety**: Full Pydantic validation with `InputT`, `OutputT`, `ConfigT`
3. **Performance Focus**: Built-in metrics, optimization, and performance tracking
4. **Circuit Breaker Protection**: Automatic failure detection and recovery
5. **Comprehensive Configuration**: Environment-specific settings with validation
6. **Error Sanitization**: Security-focused error handling
7. **Resource Management**: Memory and CPU usage monitoring
8. **Contract-Driven**: YAML subcontracts define strict input/output interfaces

### Implementation Checklist

- [ ] Replace all template placeholders
- [ ] Implement domain-specific calculation logic in `{DOMAIN}_calculator.py`
- [ ] Implement data transformation logic in `data_transformer.py`
- [ ] Implement performance optimization logic in `performance_optimizer.py`
- [ ] Update enum values to match domain requirements
- [ ] Customize configuration for domain-specific needs
- [ ] Write comprehensive unit tests
- [ ] Update manifest with accurate performance characteristics
- [ ] Validate contract compliance
- [ ] Set up monitoring and alerting

This template ensures all COMPUTE nodes follow the unified ONEX architecture while maintaining domain-specific computational capabilities and performance requirements.
