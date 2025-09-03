# CLAUDE.md - Phase 1: Reducer Pattern Engine Core Demo

## Project Overview

**Service**: Omnibase Core - Reducer Pattern Engine  
**Phase**: Phase 1 - Core Demo Implementation (Router + Single Subreducer)  
**Task ID**: 4ed98546-9fac-496e-9216-75e4490cee74  
**Timeline**: 1-2 weeks  
**Architecture**: ONEX Four-Node Compliance  

This document provides comprehensive guidance for implementing Phase 1 of the Reducer Pattern Engine, focusing on creating a minimal viable implementation with WorkflowRouter and ReducerDocumentRegenerationSubreducer that extends the existing NodeReducer architecture.

## Architecture Overview

### Core Components (Phase 1)

```
ReducerPatternEngine (Phase 1)
├── WorkflowRouter                     # Top-level routing by {workflowType, instanceId}  
├── ReducerDocumentRegenerationSubreducer  # Single subreducer for document workflows
├── InstanceIsolationManager          # Basic workflow instance isolation
└── ONEX Integration Layer            # Minimal ONEX four-node compliance
```

### Design Principles

- **ONEX Four-Node Compliance**: Must integrate with existing NodeReducerService architecture
- **Pure Functional Programming**: Deterministic behavior through immutable state patterns
- **Minimal Viable Implementation**: Focus on core routing + single subreducer only
- **No Protocol Binding**: Keep implementation simple, defer protocol complexity to Phase 3
- **ModelOnexContainer Integration**: Use existing dependency injection patterns

## Technical Architecture

### 1. WorkflowRouter Implementation

The WorkflowRouter provides consistent routing for workflow instances:

```python
# src/omnibase_core/patterns/workflow_router.py

from typing import Any, Dict
from uuid import UUID
import hashlib

from omnibase_core.core.model_onex_container import ModelOnexContainer
from omnibase_core.enums.enum_workflow_type import EnumWorkflowType
from omnibase_core.model.workflow.model_workflow_execution_state import ModelWorkflowExecutionState

class WorkflowRouter:
    """Phase 1 workflow router for document regeneration workflows."""
    
    def __init__(self, container: ModelOnexContainer):
        self.container = container
        self._subreducer_registry = {}
        
    def route_workflow(
        self,
        workflow_type: EnumWorkflowType,
        instance_id: str,
        workflow_data: Dict[str, Any]
    ) -> "ReducerDocumentRegenerationSubreducer":
        """Route workflow to appropriate subreducer instance."""
        
        # Phase 1: Simple routing to document regeneration subreducer
        if workflow_type != EnumWorkflowType.DOCUMENT_REGENERATION:
            raise NotImplementedError(f"Phase 1 only supports DOCUMENT_REGENERATION, got {workflow_type}")
            
        route_key = self._calculate_route_key(workflow_type, instance_id)
        
        # For Phase 1, always return the same subreducer instance
        if "document_regeneration" not in self._subreducer_registry:
            from omnibase_core.patterns.subreducers.reducer_document_regeneration_subreducer import (
                ReducerDocumentRegenerationSubreducer
            )
            self._subreducer_registry["document_regeneration"] = (
                ReducerDocumentRegenerationSubreducer(self.container)
            )
            
        return self._subreducer_registry["document_regeneration"]
    
    def _calculate_route_key(self, workflow_type: EnumWorkflowType, instance_id: str) -> str:
        """Calculate consistent routing key for workflow instance."""
        combined_key = f"{workflow_type.value}:{instance_id}"
        return hashlib.sha256(combined_key.encode()).hexdigest()[:16]
```

### 2. Document Regeneration Subreducer

Single subreducer focused on document workflows:

```python
# src/omnibase_core/patterns/subreducers/reducer_document_regeneration_subreducer.py

from typing import Any, Dict
from uuid import uuid4

from omnibase_core.core.model_onex_container import ModelOnexContainer
from omnibase_core.patterns.models.model_subreducer_result import ModelSubreducerResult
from omnibase_core.patterns.models.model_workflow_context import ModelWorkflowContext

class ReducerDocumentRegenerationSubreducer:
    """Phase 1 subreducer for document regeneration workflows."""
    
    def __init__(self, container: ModelOnexContainer):
        self.container = container
        self.correlation_id = str(uuid4())
        
    async def process_workflow(
        self, 
        workflow_context: ModelWorkflowContext
    ) -> ModelSubreducerResult:
        """Process document regeneration workflow."""
        
        # Phase 1: Simple document processing logic
        # Extract document data from workflow context
        document_data = workflow_context.data.get("document", {})
        
        if not document_data:
            raise ValueError("No document data provided in workflow context")
            
        # Process document regeneration
        processed_document = await self._regenerate_document(document_data)
        
        return ModelSubreducerResult(
            success=True,
            result_data={"regenerated_document": processed_document},
            execution_time_ms=workflow_context.execution_time_ms,
            correlation_id=self.correlation_id
        )
    
    async def _regenerate_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Core document regeneration logic."""
        
        # Phase 1: Placeholder implementation
        # In real implementation, this would integrate with:
        # - Document analysis services
        # - Content generation models  
        # - Template engines
        # - Version control systems
        
        return {
            "original_title": document_data.get("title", "Unknown"),
            "regenerated_content": f"Regenerated: {document_data.get('content', '')}",
            "regeneration_timestamp": "2025-01-15T10:30:00Z",
            "status": "completed"
        }
```

### 3. Main Engine Integration

ONEX-compliant reducer pattern engine:

```python
# src/omnibase_core/patterns/reducer_pattern_engine.py

from typing import Any, Dict

from omnibase_core.core.infrastructure_service_bases import NodeReducerService
from omnibase_core.core.model_onex_container import ModelOnexContainer
from omnibase_core.patterns.workflow_router import WorkflowRouter
from omnibase_core.patterns.models.model_workflow_context import ModelWorkflowContext
from omnibase_core.patterns.models.model_reducer_pattern_input import ModelReducerPatternInput
from omnibase_core.patterns.models.model_reducer_pattern_output import ModelReducerPatternOutput

class ReducerPatternEngine(NodeReducerService):
    """
    Phase 1 Reducer Pattern Engine - Core Demo Implementation.
    
    ONEX four-node compliant engine with minimal viable functionality:
    - WorkflowRouter for consistent routing
    - Single subreducer (ReducerDocumentRegenerationSubreducer)
    - Basic instance isolation
    - ModelOnexContainer integration
    """
    
    def __init__(self, container: ModelOnexContainer):
        super().__init__(container)
        
        # Initialize Phase 1 components
        self.workflow_router = WorkflowRouter(container)
        
        # Load configuration (Phase 1 minimal)
        self._load_phase1_config()
        
    async def reduce(self, reducer_input: ModelReducerPatternInput) -> ModelReducerPatternOutput:
        """Main reduction entry point for workflow processing."""
        
        try:
            # Create workflow context from input
            workflow_context = ModelWorkflowContext(
                workflow_type=reducer_input.workflow_type,
                instance_id=reducer_input.instance_id,
                data=reducer_input.data,
                execution_time_ms=0  # Will be calculated
            )
            
            # Route to appropriate subreducer
            subreducer = self.workflow_router.route_workflow(
                workflow_context.workflow_type,
                workflow_context.instance_id, 
                workflow_context.data
            )
            
            # Process workflow
            result = await subreducer.process_workflow(workflow_context)
            
            return ModelReducerPatternOutput(
                success=result.success,
                result_data=result.result_data,
                workflow_type=workflow_context.workflow_type,
                instance_id=workflow_context.instance_id,
                execution_time_ms=result.execution_time_ms
            )
            
        except Exception as e:
            return ModelReducerPatternOutput(
                success=False,
                error_message=str(e),
                workflow_type=reducer_input.workflow_type,
                instance_id=reducer_input.instance_id,
                execution_time_ms=0
            )
    
    def _load_phase1_config(self) -> None:
        """Load Phase 1 minimal configuration."""
        # Phase 1: Minimal configuration
        # Later phases will add comprehensive config loading
        pass
```

## Data Models

### Core Models (Phase 1)

```python
# src/omnibase_core/patterns/models/model_reducer_pattern_input.py

from typing import Any, Dict
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

class ModelReducerPatternInput(BaseModel):
    """Input model for Reducer Pattern Engine."""
    
    workflow_type: EnumWorkflowType = Field(..., description="Type of workflow to process")
    instance_id: str = Field(..., description="Unique workflow instance identifier")  
    data: Dict[str, Any] = Field(default_factory=dict, description="Workflow data payload")


# src/omnibase_core/patterns/models/model_reducer_pattern_output.py

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

class ModelReducerPatternOutput(BaseModel):
    """Output model for Reducer Pattern Engine."""
    
    success: bool = Field(..., description="Whether workflow processing succeeded")
    result_data: Optional[Dict[str, Any]] = Field(None, description="Workflow result data")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    workflow_type: EnumWorkflowType = Field(..., description="Type of workflow processed")
    instance_id: str = Field(..., description="Workflow instance identifier")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


# src/omnibase_core/patterns/models/model_workflow_context.py

from typing import Any, Dict
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

class ModelWorkflowContext(BaseModel):
    """Context data for workflow processing."""
    
    workflow_type: EnumWorkflowType = Field(..., description="Workflow type")
    instance_id: str = Field(..., description="Instance identifier")
    data: Dict[str, Any] = Field(..., description="Workflow data")
    execution_time_ms: int = Field(default=0, description="Execution time tracking")


# src/omnibase_core/patterns/models/model_subreducer_result.py

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ModelSubreducerResult(BaseModel):
    """Result model for subreducer processing."""
    
    success: bool = Field(..., description="Whether processing succeeded")
    result_data: Dict[str, Any] = Field(..., description="Processing result data")
    execution_time_ms: int = Field(..., description="Processing time in milliseconds")
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    error_details: Optional[str] = Field(None, description="Error details if failed")
```

## File Structure (Phase 1)

```
src/omnibase_core/patterns/                    # New patterns module
├── __init__.py                               # Module exports
├── reducer_pattern_engine.py                # Main engine (ONEX compliant)
├── workflow_router.py                       # Workflow routing logic
├── models/                                  # Data models
│   ├── __init__.py
│   ├── model_reducer_pattern_input.py       # Input model  
│   ├── model_reducer_pattern_output.py      # Output model
│   ├── model_workflow_context.py           # Workflow context
│   └── model_subreducer_result.py          # Subreducer result
└── subreducers/                            # Subreducer implementations
    ├── __init__.py
    └── reducer_document_regeneration_subreducer.py  # Document workflows

# Required enum (if not exists)
src/omnibase_core/enums/enum_workflow_type.py

# Testing structure
tests/unit/patterns/                         # Unit tests
├── test_reducer_pattern_engine.py
├── test_workflow_router.py  
└── test_document_regeneration_subreducer.py

tests/integration/patterns/                  # Integration tests
└── test_reducer_pattern_integration.py
```

## Implementation Guidelines

### 1. ONEX Architecture Compliance

**NodeReducerService Integration**:
- Extend `NodeReducerService` base class
- Use `ModelOnexContainer` dependency injection
- Follow existing service initialization patterns
- Implement health check endpoints via `MixinHealthCheck`

**Container Integration**:
```python
# Follow existing patterns from infrastructure_service_bases.py
def __init__(self, container: ModelOnexContainer):
    super().__init__(container)  # Handles all ONEX boilerplate
    
    # Load services from container  
    self.event_bus = container.get_service("ProtocolEventBus")
    self.metadata_loader = container.get_service("ProtocolSchemaLoader")
```

### 2. Error Handling Standards

**Consistent Error Patterns**:
```python
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError

# Use ONEX error patterns
try:
    result = await self.process_workflow(context)
except Exception as e:
    raise OnexError(
        error_code=CoreErrorCode.WORKFLOW_PROCESSING_FAILED,
        message=f"Workflow processing failed: {str(e)}",
        context={"workflow_type": context.workflow_type, "instance_id": context.instance_id}
    )
```

**Logging Standards**:
```python
from omnibase_core.core.core_structured_logging import emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

# Use structured logging
emit_log_event(
    level=LogLevel.INFO,
    message="Workflow processing started",
    metadata={
        "workflow_type": workflow_context.workflow_type.value,
        "instance_id": workflow_context.instance_id,
        "correlation_id": self.correlation_id
    }
)
```

### 3. Async/Await Patterns

**Follow Existing Patterns**:
```python
# Match NodeReducer async patterns
async def reduce(self, reducer_input: ModelReducerPatternInput) -> ModelReducerPatternOutput:
    """Follow existing NodeReducer.reduce() signature patterns."""
    
    # Use existing async patterns from NodeReducer
    async with self.container.get_async_context() as context:
        result = await self._process_with_context(context, reducer_input)
        return result
```

## Testing Strategy (Phase 1)

### Unit Tests

**Test WorkflowRouter**:
```python
# tests/unit/patterns/test_workflow_router.py

import pytest
from unittest.mock import Mock

from omnibase_core.patterns.workflow_router import WorkflowRouter
from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

class TestWorkflowRouter:
    def test_route_document_regeneration_workflow(self):
        """Test routing document regeneration workflows."""
        container = Mock()
        router = WorkflowRouter(container)
        
        subreducer = router.route_workflow(
            EnumWorkflowType.DOCUMENT_REGENERATION,
            "test-instance-123", 
            {"document": {"title": "Test Doc"}}
        )
        
        assert subreducer is not None
        assert hasattr(subreducer, 'process_workflow')
    
    def test_unsupported_workflow_type_raises_error(self):
        """Test that unsupported workflow types raise NotImplementedError."""
        container = Mock() 
        router = WorkflowRouter(container)
        
        with pytest.raises(NotImplementedError):
            router.route_workflow(
                EnumWorkflowType.CODE_ANALYSIS,  # Not supported in Phase 1
                "test-instance-123",
                {}
            )
```

**Test Document Subreducer**:
```python
# tests/unit/patterns/test_document_regeneration_subreducer.py

import pytest
from unittest.mock import Mock

from omnibase_core.patterns.subreducers.reducer_document_regeneration_subreducer import (
    ReducerDocumentRegenerationSubreducer
)
from omnibase_core.patterns.models.model_workflow_context import ModelWorkflowContext
from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

class TestDocumentRegenerationSubreducer:
    @pytest.mark.asyncio
    async def test_process_workflow_success(self):
        """Test successful document workflow processing."""
        container = Mock()
        subreducer = ReducerDocumentRegenerationSubreducer(container)
        
        context = ModelWorkflowContext(
            workflow_type=EnumWorkflowType.DOCUMENT_REGENERATION,
            instance_id="test-123",
            data={
                "document": {
                    "title": "Test Document",
                    "content": "Original content"
                }
            }
        )
        
        result = await subreducer.process_workflow(context)
        
        assert result.success is True
        assert "regenerated_document" in result.result_data
        assert result.correlation_id is not None
    
    @pytest.mark.asyncio 
    async def test_process_workflow_no_document_data(self):
        """Test workflow processing with missing document data."""
        container = Mock()
        subreducer = ReducerDocumentRegenerationSubreducer(container)
        
        context = ModelWorkflowContext(
            workflow_type=EnumWorkflowType.DOCUMENT_REGENERATION,
            instance_id="test-123", 
            data={}  # No document data
        )
        
        with pytest.raises(ValueError, match="No document data provided"):
            await subreducer.process_workflow(context)
```

### Integration Tests

**Test Full Engine Integration**:
```python
# tests/integration/patterns/test_reducer_pattern_integration.py

import pytest
from unittest.mock import Mock

from omnibase_core.patterns.reducer_pattern_engine import ReducerPatternEngine
from omnibase_core.patterns.models.model_reducer_pattern_input import ModelReducerPatternInput
from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

class TestReducerPatternIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_document_workflow(self):
        """Test complete document regeneration workflow."""
        container = Mock()
        # Configure container mocks for ONEX services
        container.get_service.return_value = Mock()
        
        engine = ReducerPatternEngine(container)
        
        input_data = ModelReducerPatternInput(
            workflow_type=EnumWorkflowType.DOCUMENT_REGENERATION,
            instance_id="integration-test-123",
            data={
                "document": {
                    "title": "Integration Test Document", 
                    "content": "Test content for integration"
                }
            }
        )
        
        result = await engine.reduce(input_data)
        
        assert result.success is True
        assert result.workflow_type == EnumWorkflowType.DOCUMENT_REGENERATION
        assert result.instance_id == "integration-test-123"
        assert "regenerated_document" in result.result_data
```

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone and setup project
cd /Volumes/PRO-G40/Code/omnibase-core
poetry install

# Create feature branch  
git checkout -b feature/reducer-pattern-engine-phase1

# Run existing tests to ensure clean baseline
poetry run pytest tests/ -v
```

### 2. Implementation Order

**Step 1: Create Required Enum** (if not exists)
```python
# src/omnibase_core/enums/enum_workflow_type.py
from enum import Enum

class EnumWorkflowType(Enum):
    DOCUMENT_REGENERATION = "document_regeneration"
    # Phase 2+ will add more types
```

**Step 2: Implement Data Models**
- Create `src/omnibase_core/patterns/models/` directory
- Implement all model classes with proper Pydantic validation
- Add comprehensive docstrings and type hints

**Step 3: Implement Core Components**
- WorkflowRouter (simple routing logic)
- ReducerDocumentRegenerationSubreducer (single workflow type)
- ReducerPatternEngine (ONEX integration)

**Step 4: Testing and Validation**
- Unit tests for each component
- Integration tests for full workflow
- Performance validation for basic scenarios

### 3. Code Quality Standards

**Type Hints and Documentation**:
```python
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ExampleClass:
    """Comprehensive class documentation."""
    
    def __init__(self, container: ModelOnexContainer) -> None:
        """Initialize with proper type hints."""
        self.container = container
    
    async def process_data(
        self, 
        input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process input data with comprehensive documentation.
        
        Args:
            input_data: Dictionary containing workflow data
            
        Returns:
            Processed data dictionary, or None if processing failed
            
        Raises:
            ValueError: If input_data is invalid
            OnexError: If processing fails
        """
        pass
```

**Import Organization**:
```python
# Standard library imports
import asyncio
import hashlib
from typing import Any, Dict, Optional
from uuid import uuid4

# Third-party imports
from pydantic import BaseModel, Field

# Local imports
from omnibase_core.core.model_onex_container import ModelOnexContainer
from omnibase_core.core.infrastructure_service_bases import NodeReducerService
from omnibase_core.patterns.models.model_workflow_context import ModelWorkflowContext
```

## Validation and Acceptance Criteria

### Phase 1 Success Criteria

**Functional Requirements** ✅:
- [ ] WorkflowRouter successfully routes DOCUMENT_REGENERATION workflows
- [ ] ReducerDocumentRegenerationSubreducer processes document workflows  
- [ ] ReducerPatternEngine integrates with ONEX NodeReducerService
- [ ] All components use ModelOnexContainer dependency injection
- [ ] Error handling follows ONEX patterns

**Technical Requirements** ✅:
- [ ] Extends existing NodeReducerService architecture
- [ ] Uses ModelOnexContainer for dependency injection
- [ ] Follows ONEX four-node compliance patterns
- [ ] Implements proper async/await patterns
- [ ] Uses structured logging and error handling

**Testing Requirements** ✅:
- [ ] Unit tests for all core components (>90% coverage)
- [ ] Integration tests for end-to-end workflows
- [ ] Error scenario testing
- [ ] Performance validation (basic scenarios)

**Code Quality Requirements** ✅:
- [ ] Comprehensive type hints and documentation
- [ ] Follows existing code organization patterns
- [ ] Proper import organization and dependency management
- [ ] Passes linting and type checking (mypy)

### Performance Benchmarks (Phase 1)

**Basic Performance Targets**:
- Workflow routing latency: <50ms
- Document processing time: <2 seconds for typical documents  
- Memory usage: <100MB for typical workflows
- Error recovery: <1 second for handled errors

### Demo Capabilities

**Phase 1 Demo Script**:
```python
# Demo script showing Phase 1 capabilities
async def demo_phase1_reducer_pattern():
    """Demonstrate Phase 1 Reducer Pattern Engine capabilities."""
    
    # Initialize container (mock for demo)
    container = create_demo_container()
    
    # Create engine
    engine = ReducerPatternEngine(container)
    
    # Demo workflow input
    demo_input = ModelReducerPatternInput(
        workflow_type=EnumWorkflowType.DOCUMENT_REGENERATION,
        instance_id="demo-workflow-001",
        data={
            "document": {
                "title": "Demo Document",
                "content": "This is a demo document for Phase 1 testing.",
                "format": "markdown",
                "version": "1.0"
            }
        }
    )
    
    # Process workflow
    print("🚀 Processing Phase 1 workflow...")
    result = await engine.reduce(demo_input)
    
    # Display results
    if result.success:
        print("✅ Workflow processed successfully!")
        print(f"📊 Execution time: {result.execution_time_ms}ms")
        print(f"📄 Result: {result.result_data}")
    else:
        print(f"❌ Workflow failed: {result.error_message}")

# Run demo
if __name__ == "__main__":
    asyncio.run(demo_phase1_reducer_pattern())
```

## Future Phases (Roadmap)

### Phase 2: Expanded Subreducers (Weeks 3-4)
- Add CodeAnalysisSubreducer, PRCreationSubreducer  
- Implement SubreducerFramework with FSM logic
- Enhanced state management and persistence

### Phase 3: Protocol Integration (Weeks 5-6)
- Full ONEX protocol compliance
- Contract definitions and validation
- Inter-node communication protocols

### Phase 4: Production Features (Weeks 7-8)
- Advanced monitoring and metrics
- Circuit breakers and resilience patterns
- Performance optimization and scaling

## Deployment Notes

### Development Deployment
```bash
# Run with Docker for real environment testing
docker-compose -f docker-compose.dev.yml up --build

# Test the implementation
poetry run pytest tests/integration/patterns/ -v
```

### Integration with Existing Systems
- Leverages existing canary deployment infrastructure
- Uses established ONEX monitoring and logging
- Compatible with current development workflows

## Support and Documentation

**Key Files for Reference**:
- `src/omnibase_core/core/node_reducer_service.py` - Base service patterns
- `src/omnibase_core/core/infrastructure_service_bases.py` - Service initialization
- `src/omnibase_core/core/onex_container.py` - Dependency injection
- `REDUCER_PATTERN_ENGINE_IMPLEMENTATION_PLAN.md` - Complete implementation plan

**Development Resources**:
- Follow existing NodeReducer patterns for consistency
- Use ModelOnexContainer service registry for all dependencies  
- Implement comprehensive error handling and logging
- Maintain ONEX four-node architecture compliance

---

**Document Version**: 1.0  
**Generated**: 2025-01-15  
**Phase**: 1 - Core Demo Implementation  
**Next Review**: After Phase 1 completion