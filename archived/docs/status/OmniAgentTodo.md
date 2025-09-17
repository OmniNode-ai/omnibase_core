# OmniAgent Todo - Missing Core Features

**Purpose**: Document missing features in omnibase_core that are required by the OmniAgent repository, as identified during PR #18 review and implementation.

**Repository**: https://github.com/OmniNode-ai/omnibase_core
**Related OmniAgent PR**: #18 - ONEX 4-Node Architecture Foundation
**Date Created**: 2024-09-14

## 🎯 Context & Separation of Concerns

During the implementation of ONEX 4-Node Architecture in the OmniAgent repository, several PR comments identified features that should be implemented in the core omnibase_core library rather than in the application layer.

This document maintains clean architectural separation by documenting what belongs in the core vs. application layers.

## 📋 Missing Core Features

### 1. Enhanced Base Class Validation

**Status**: IDENTIFIED
**Priority**: HIGH
**Issue**: Base classes like `NodeCoreBase` could provide enhanced validation methods

**Current State**:
```python
# NodeCoreBase only provides basic null validation
def _validate_input_data(self, input_data: Any) -> None:
    if input_data is None:
        raise OnexError(...)
```

**Proposed Enhancement**:
```python
# Enhanced validation that could be in core
def _validate_correlation_id(self, correlation_id: Any) -> UUID:
    """Validate and convert correlation ID to proper UUID format"""
    # UUID validation, format conversion, security checks

def _validate_bounded_dict(self, data: Dict[str, Any], max_size: int = 1000) -> Dict:
    """Validate dictionary fields aren't unbounded for security"""
    # Size validation, key validation, nested depth checks
```

**Justification**: Security validation and type coercion should be handled at the core framework level, not reimplemented in each application.

### 2. Circuit Breaker Base Integration

**Status**: IDENTIFIED
**Priority**: MEDIUM
**Issue**: Circuit breaker patterns are being implemented at application layer but could be core framework features

**Current State**:
```python
# Each node reimplements circuit breaker logic
from omni_agent.core.circuit_breaker import CircuitBreakerFactory
```

**Proposed Enhancement**:
```python
# Core base class could provide circuit breaker mixins
class NodeCoreBase(ABC):
    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        # Standard circuit breaker implementation
```

**Justification**: Circuit breaker patterns are infrastructure concerns that should be standardized at the core level.

### 3. Smart Responder Chain Integration Points

**Status**: IDENTIFIED
**Priority**: MEDIUM
**Issue**: Integration patterns for AI escalation chains could be standardized

**Current State**:
```python
# Each service node implements its own integration
from omni_agent.workflows.smart_responder_chain import SmartResponderChain
```

**Proposed Enhancement**:
```python
# Core base class could provide standard integration hooks
class NodeCoreBase(ABC):
    def _get_ai_responder(self) -> Optional[AIResponderProtocol]:
        """Get AI responder service if available"""
        # Standard protocol for AI escalation services
```

**Justification**: While specific AI services stay in applications, the integration patterns could be standardized.

### 4. Enhanced Metrics and Observability

**Status**: IDENTIFIED
**Priority**: MEDIUM
**Issue**: Metrics collection patterns are being reimplemented across nodes

**Current State**:
```python
# Each node implements its own metrics tracking
self.metrics: dict[str, float] = {
    "total_operations": 0.0,
    "success_count": 0.0,
    # ... duplicated across nodes
}
```

**Proposed Enhancement**:
```python
# Core base class could provide standardized metrics
class NodeCoreBase(ABC):
    def _record_operation_metric(self, operation: str, duration: float, success: bool):
        """Record standardized operation metrics"""
        # Consistent metrics format across all nodes
```

**Justification**: Observability and metrics should be consistent across all ONEX nodes regardless of application.

### 5. Configuration Schema Validation

**Status**: IDENTIFIED
**Priority**: LOW
**Issue**: Configuration validation patterns could be standardized

**Current State**:
```python
# Each node validates its own config differently
self.config = config or {}
```

**Proposed Enhancement**:
```python
# Core base class could provide config validation
class NodeCoreBase(ABC):
    def _validate_config(self, config: Dict[str, Any]) -> ValidatedConfig:
        """Validate node configuration against schema"""
        # Standard validation patterns
```

**Justification**: Configuration schemas and validation should be consistent across the framework.

## ✅ Features Already Properly Implemented in Core

### 1. NodeCoreBase Abstract Methods

**Status**: ✅ COMPLETE
**Implementation**: `NodeCoreBase.process()` abstract method is properly defined
**Result**: All application nodes correctly implement required abstract methods

### 2. ONEX Container Dependency Injection

**Status**: ✅ COMPLETE
**Implementation**: `ModelONEXContainer` provides proper dependency injection
**Result**: Clean separation between framework and application dependencies

### 3. Base Lifecycle Management

**Status**: ✅ COMPLETE
**Implementation**: `initialize → process → cleanup` lifecycle is well-defined
**Result**: Consistent node lifecycle across all implementations

### 4. Error Handling Framework

**Status**: ✅ COMPLETE
**Implementation**: `OnexError` with proper error chaining and context
**Result**: Consistent error handling patterns across the framework

## 🚀 Implementation Recommendations

### Phase 1: High Priority Core Features
1. **Enhanced Validation Framework** - Add security-conscious validation methods to NodeCoreBase
2. **Metrics Standardization** - Implement consistent metrics collection patterns

### Phase 2: Infrastructure Integration
1. **Circuit Breaker Mixins** - Add optional circuit breaker integration to base classes
2. **AI Service Integration Protocols** - Standardize integration patterns for AI escalation

### Phase 3: Developer Experience
1. **Configuration Schema Framework** - Add configuration validation and documentation
2. **Observability Enhancements** - Expand metrics and monitoring capabilities

## 🔄 Current Status

### OmniAgent Repository Status
- ✅ All generated nodes properly inherit from core base classes
- ✅ Abstract method implementations completed
- ✅ Type safety improvements implemented
- ✅ Hard-coded paths removed for CI/CD compatibility
- ✅ Import error handling improved for development workflows

### Next Steps
1. Prioritize implementation of high-priority core features
2. Coordinate with OmniAgent development to ensure compatibility
3. Create RFC process for core framework changes
4. Establish testing patterns for core framework enhancements

## 📞 Coordination Points

- **OmniAgent Issues**: Features that require core framework changes should reference this document
- **Breaking Changes**: Any core changes must maintain backward compatibility with existing OmniAgent implementations
- **Testing**: Core feature additions require comprehensive test coverage in omnibase_core
- **Documentation**: Core framework changes must include updated documentation and migration guides

---

**Maintained by**: Claude Code Agent Ecosystem
**Last Updated**: 2024-09-14
**Review Cycle**: Monthly or as needed for critical features
