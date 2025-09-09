# Complete Dictionary Metadata Elimination Plan

## 🎯 Objective

Eliminate ALL raw dictionary metadata patterns throughout omnibase_core and replace with **strongly-typed Pydantic models** that:

1. **Start with "Model" prefix** (naming standards compliance)
2. **Use NO basic types** or `Dict[str, Any]` that will require future refactoring
3. **Provide compile-time validation** instead of runtime surprises
4. **Support YAML serialization** natively
5. **Are future-proof** and will never need refactoring again

## 🚨 Current Anti-Patterns to ELIMINATE

```python
# ❌ WRONG - Raw dictionary anti-patterns everywhere
metadata = {
    "environment": "production",
    "port": 8080,
    "active": True
}

processing_metadata = {
    "correlation_id": "123",
    "execution_time": 150.5,
    "status": "completed"
}

routing_metadata = {
    "route_type": "primary",
    "fallback_available": True
}

# ❌ WRONG - Loose typing that causes runtime errors
metadata: Dict[str, Any] = {}
metadata: Optional[Dict[str, Union[str, int, bool]]] = None
```

## ✅ Strongly-Typed Replacement Models

### 1. Service Discovery Metadata

```python
# src/omnibase_core/model/metadata/model_service_metadata.py

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from omnibase_core.enums.node import EnumHealthStatus

class ServiceEnvironment(str, Enum):
    """Constrained service environment values."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    LOCAL = "local"

class ModelServiceMetadata(BaseModel):
    """Strongly-typed service discovery metadata."""

    environment: ServiceEnvironment = Field(
        ...,
        description="Service deployment environment"
    )
    port: int = Field(
        ge=1024,
        le=65535,
        description="Service port number"
    )
    active: bool = Field(
        ...,
        description="Whether service is actively serving requests"
    )
    service_id: UUID = Field(
        default_factory=uuid4,
        description="Unique service instance identifier"
    )
    health_status: EnumHealthStatus = Field(
        default=EnumHealthStatus.UNKNOWN,
        description="Current health status"
    )
    load_factor: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Current load factor (0.0 = no load, 1.0 = max load)"
    )
    datacenter: Optional[str] = Field(
        None,
        max_length=50,
        description="Datacenter location identifier"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
```

### 2. Processing Metadata

```python
# src/omnibase_core/model/metadata/model_processing_metadata.py

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ProcessingStage(str, Enum):
    """Processing stage enumeration."""
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    PROCESSING = "processing"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingStatus(str, Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ModelProcessingMetadata(BaseModel):
    """Strongly-typed processing operation metadata."""

    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation identifier for tracing"
    )
    processing_time_ms: float = Field(
        ge=0.0,
        description="Processing time in milliseconds"
    )
    stage: ProcessingStage = Field(
        ...,
        description="Current processing stage"
    )
    status: ProcessingStatus = Field(
        ...,
        description="Current processing status"
    )
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Processing node identifier"
    )
    protocol_version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Protocol version used"
    )
    has_errors: bool = Field(
        default=False,
        description="Whether processing encountered errors"
    )
    error_count: int = Field(
        ge=0,
        default=0,
        description="Number of errors encountered"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Processing completion timestamp"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

### 3. Workflow Metadata

```python
# src/omnibase_core/model/metadata/model_workflow_metadata.py

from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class WorkflowPriority(str, Enum):
    """Workflow priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class WorkflowExecutionMode(str, Enum):
    """Workflow execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    PIPELINE = "pipeline"

class ModelWorkflowStepMetadata(BaseModel):
    """Metadata for individual workflow steps."""

    step_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique step identifier"
    )
    step_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable step name"
    )
    execution_order: int = Field(
        ge=0,
        description="Step execution order"
    )
    is_optional: bool = Field(
        default=False,
        description="Whether step can be skipped"
    )
    timeout_seconds: int = Field(
        ge=1,
        default=300,
        description="Step timeout in seconds"
    )

class ModelWorkflowMetadata(BaseModel):
    """Strongly-typed workflow metadata."""

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique workflow identifier"
    )
    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable workflow name"
    )
    priority: WorkflowPriority = Field(
        default=WorkflowPriority.MEDIUM,
        description="Workflow execution priority"
    )
    execution_mode: WorkflowExecutionMode = Field(
        ...,
        description="How workflow steps should be executed"
    )
    user_id: Optional[str] = Field(
        None,
        max_length=100,
        description="User who initiated the workflow"
    )
    department: Optional[str] = Field(
        None,
        max_length=100,
        description="Requesting department"
    )
    requestor: Optional[str] = Field(
        None,
        max_length=100,
        description="Original requestor identifier"
    )
    steps: List[ModelWorkflowStepMetadata] = Field(
        default_factory=list,
        description="Workflow step definitions"
    )
    max_parallel_steps: int = Field(
        ge=1,
        default=5,
        description="Maximum parallel steps for parallel execution"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
```

### 4. Routing Metadata

```python
# src/omnibase_core/model/metadata/model_routing_metadata.py

from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class RouteType(str, Enum):
    """Route type enumeration."""
    PRIMARY = "primary"
    FALLBACK = "fallback"
    LOAD_BALANCED = "load_balanced"
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"

class RoutingStrategy(str, Enum):
    """Routing strategy enumeration."""
    DIRECT = "direct"
    FAILOVER = "failover"
    CIRCUIT_BREAKER = "circuit_breaker"
    RETRY = "retry"

class ModelRoutingTargetMetadata(BaseModel):
    """Metadata for routing targets."""

    target_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target identifier"
    )
    target_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Target type (compute, effect, etc.)"
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Routing weight for weighted strategies"
    )
    is_healthy: bool = Field(
        default=True,
        description="Whether target is healthy"
    )
    response_time_ms: float = Field(
        ge=0.0,
        default=0.0,
        description="Average response time in milliseconds"
    )

class ModelRoutingMetadata(BaseModel):
    """Strongly-typed routing metadata."""

    route_id: UUID = Field(
        default_factory=uuid4,
        description="Unique route identifier"
    )
    route_type: RouteType = Field(
        ...,
        description="Type of routing to perform"
    )
    strategy: RoutingStrategy = Field(
        ...,
        description="Routing strategy to use"
    )
    fallback_available: bool = Field(
        default=False,
        description="Whether fallback routes are available"
    )
    max_retries: int = Field(
        ge=0,
        default=3,
        description="Maximum retry attempts"
    )
    retry_delay_ms: int = Field(
        ge=0,
        default=1000,
        description="Delay between retries in milliseconds"
    )
    circuit_breaker_threshold: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="Failure rate threshold for circuit breaker"
    )
    targets: List[ModelRoutingTargetMetadata] = Field(
        default_factory=list,
        description="Available routing targets"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
```

### 5. Error Details Metadata

```python
# src/omnibase_core/model/metadata/model_error_metadata.py

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """Error category enumeration."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"

class ModelErrorContext(BaseModel):
    """Error context information."""

    component: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Component where error occurred"
    )
    function: Optional[str] = Field(
        None,
        max_length=100,
        description="Function where error occurred"
    )
    line_number: Optional[int] = Field(
        None,
        ge=1,
        description="Line number where error occurred"
    )
    file_path: Optional[str] = Field(
        None,
        max_length=500,
        description="File path where error occurred"
    )

class ModelErrorMetadata(BaseModel):
    """Strongly-typed error metadata."""

    error_id: UUID = Field(
        default_factory=uuid4,
        description="Unique error identifier"
    )
    error_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Z_]+$",
        description="Standardized error code"
    )
    error_message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    severity: ErrorSeverity = Field(
        ...,
        description="Error severity level"
    )
    category: ErrorCategory = Field(
        ...,
        description="Error category"
    )
    occurred_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )
    correlation_id: Optional[UUID] = Field(
        None,
        description="Correlation ID for tracing"
    )
    context: Optional[ModelErrorContext] = Field(
        None,
        description="Error context information"
    )
    is_retryable: bool = Field(
        default=False,
        description="Whether the operation can be retried"
    )
    recovery_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested recovery actions"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

## 🔄 Migration Strategy

### Phase 1: Model Creation (Week 1)
```bash
# Create all strongly-typed metadata models
mkdir -p src/omnibase_core/model/metadata/
touch src/omnibase_core/model/metadata/__init__.py
touch src/omnibase_core/model/metadata/model_service_metadata.py
touch src/omnibase_core/model/metadata/model_processing_metadata.py
touch src/omnibase_core/model/metadata/model_workflow_metadata.py
touch src/omnibase_core/model/metadata/model_routing_metadata.py
touch src/omnibase_core/model/metadata/model_error_metadata.py
```

### Phase 2: Service Discovery Migration (Week 2)
```python
# Replace all service discovery dictionary patterns

# Before:
metadata = {
    "environment": "production",
    "port": 8080,
    "active": True
}

# After:
from omnibase_core.model.metadata.model_service_metadata import ModelServiceMetadata
metadata = ModelServiceMetadata(
    environment=ServiceEnvironment.PRODUCTION,
    port=8080,
    active=True
)
```

### Phase 3: Processing & Workflow Migration (Week 3)
```python
# Replace all processing and workflow dictionary patterns

# Before:
processing_metadata = {
    "correlation_id": "123",
    "execution_time": 150.5,
    "status": "completed"
}

# After:
from omnibase_core.model.metadata.model_processing_metadata import ModelProcessingMetadata
processing_metadata = ModelProcessingMetadata(
    correlation_id=uuid4(),
    processing_time_ms=150.5,
    status=ProcessingStatus.COMPLETED,
    stage=ProcessingStage.COMPLETED
)
```

### Phase 4: Routing & Error Migration (Week 4)
```python
# Replace all routing and error dictionary patterns

# Before:
routing_metadata = {
    "route_type": "primary",
    "fallback_available": True
}

# After:
from omnibase_core.model.metadata.model_routing_metadata import ModelRoutingMetadata
routing_metadata = ModelRoutingMetadata(
    route_type=RouteType.PRIMARY,
    strategy=RoutingStrategy.DIRECT,
    fallback_available=True
)
```

## 🧪 Testing Strategy

### 1. Migration Validation Tests
```python
def test_no_dict_any_patterns():
    """Ensure no Dict[str, Any] patterns remain."""
    # Use AST parsing to validate no dictionary patterns exist

def test_all_metadata_strongly_typed():
    """Ensure all metadata uses strongly-typed models."""
    # Validate all metadata variables use Model* classes

def test_yaml_serialization():
    """Test YAML serialization/deserialization."""
    # Ensure all models work with YAML
```

### 2. Performance Tests
```python
def test_performance_overhead_acceptable():
    """Ensure performance overhead is <20%."""
    # Benchmark dict vs typed metadata performance

def test_memory_usage_reasonable():
    """Ensure memory overhead is <10MB."""
    # Memory profiling tests
```

## ✅ Success Criteria

1. **Zero Dictionary Patterns**: No `Dict[str, Any]` or raw dictionary metadata
2. **100% Model Prefix**: All metadata models start with "Model"
3. **Strong Typing**: No basic types that require future refactoring
4. **YAML Support**: Full serialization/deserialization support
5. **Performance**: <20% overhead vs dictionary patterns
6. **Future-Proof**: Models designed to never need refactoring again

## 🎯 Final Result

Instead of this anti-pattern:
```python
# ❌ NEVER AGAIN
metadata = {"environment": "production", "port": 8080, "active": True}
```

We will have this proper pattern:
```python
# ✅ ALWAYS
metadata = ModelServiceMetadata(
    environment=ServiceEnvironment.PRODUCTION,
    port=8080,
    active=True
)
```

**Benefits:**
- **Compile-time validation** catches errors before runtime
- **IDE autocomplete** and type checking support
- **Self-documenting** with field descriptions and constraints
- **YAML-native** serialization/deserialization
- **Future-proof** design that will never need refactoring again
- **ONEX compliant** with strong typing standards

This plan ensures we **NEVER** have to refactor metadata again because we're using proper strongly-typed Pydantic models from the start.
