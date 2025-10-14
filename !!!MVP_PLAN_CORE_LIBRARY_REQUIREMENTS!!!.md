# MVP PLAN: Core Library Requirements for Autonomous Code Generation

**Priority**: 🔴 **BLOCKER** - Blocks 60% of code generation functionality  
**Estimated Time**: 3-5 days  
**Contact**: omniclaude autonomous code generation workflow  
**Dependencies**: None (this is a dependency for others)

## Overview

The autonomous code generation system in omniclaude requires stable interfaces and metadata from omnibase_core to generate compliant OmniNodes. This document outlines the critical requirements for enabling code generation.

## Critical Requirements

### 1. Mixin Metadata System (BLOCKER)

**Current State**: Mixins exist but lack discoverable metadata  
**Required**: Each mixin must have machine-readable metadata for code generation

#### Required Files to Create:

**File**: `src/omnibase_core/mixins/mixin_metadata.yaml`

```yaml
# Example for MixinEventBus
mixin_event_bus:
  name: "MixinEventBus"
  description: "Event-driven communication capabilities"
  version: "1.0.0"
  category: "communication"

  # Dependencies
  requires:
    - "omnibase_core.core.onex_container"
    - "pydantic"

  # Compatibility
  compatible_with:
    - "MixinCaching"
    - "MixinHealthCheck"
    - "MixinRetry"

  incompatible_with:
    - "MixinSynchronous"  # if such a thing exists

  # Configuration schema
  config_schema:
    event_bus_type:
      type: "string"
      enum: ["redis", "kafka", "memory"]
      default: "redis"
    max_retries:
      type: "integer"
      minimum: 0
      maximum: 10
      default: 3

  # Usage examples
  usage_examples:
    - "Database adapters that need to publish events"
    - "API clients that emit status updates"
    - "Background processors with event notifications"

  # Generated code patterns
  code_patterns:
    inheritance: "class Node{Name}Effect(NodeEffectService, MixinEventBus):"
    initialization: "self._event_bus = EventBus(config.event_bus_type)"
    methods:
      - "async def publish_event(self, event_type: str, data: dict)"
      - "async def subscribe_to_events(self, event_types: list)"
```

#### Required for ALL Mixins:

- `MixinEventBus` - Event-driven communication
- `MixinCaching` - Caching capabilities  
- `MixinHealthCheck` - Health monitoring
- `MixinRetry` - Retry logic
- `MixinCircuitBreaker` - Fault tolerance
- `MixinLogging` - Structured logging
- `MixinMetrics` - Performance monitoring
- `MixinSecurity` - Security features
- `MixinValidation` - Input validation
- `MixinSerialization` - Data serialization

**Action**: Create metadata files for each mixin with the schema above.

### 2. Base Node Class Interface Stability (BLOCKER)

**Current State**: Base classes exist but interfaces may change  
**Required**: Lock down abstract method signatures

#### Required Files to Update:

**File**: `src/omnibase_core/core/node_effect_service.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from omnibase_core.core.node_effect import ModelEffectInput, ModelEffectOutput

class NodeEffectService(ABC):
    """Stable interface for Effect nodes - DO NOT CHANGE without version bump"""

    # Required abstract methods (MUST be implemented by generated code)
    @abstractmethod
    async def process_effect(
        self,
        input_data: ModelEffectInput
    ) -> ModelEffectOutput:
        """
        Process the effect operation.

        Args:
            input_data: Input envelope with operation data

        Returns:
            Output envelope with result data

        Raises:
            OnexError: For operation failures
        """
        pass

    @abstractmethod
    async def validate_input(
        self,
        input_data: ModelEffectInput
    ) -> bool:
        """
        Validate input data before processing.

        Args:
            input_data: Input to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the effect node.

        Returns:
            Health status dictionary
        """
        pass

    # Optional lifecycle methods (can be overridden)
    async def initialize(self) -> None:
        """Initialize the effect node (optional override)"""
        pass

    async def cleanup(self) -> None:
        """Cleanup resources (optional override)"""
        pass
```

**Similar interfaces needed for**:
- `NodeComputeService`
- `NodeReducerService`
- `NodeOrchestratorService`

**Action**: Lock down these interfaces with version comments and ensure they won't change.

### 3. Contract Validation API (HIGH)

**Current State**: Contract models exist but no programmatic validation  
**Required**: API to validate generated contracts

#### Required File to Create:

**File**: `src/omnibase_core/validation/contract_validator.py`

```python
from typing import Dict, List, Tuple, Any
from pydantic import BaseModel, ValidationError
import yaml

class ContractValidationResult(BaseModel):
    is_valid: bool
    score: float  # 0.0 to 1.0
    violations: List[str]
    warnings: List[str]
    suggestions: List[str]

class ContractValidator:
    """Programmatic contract validation for generated code"""

    def validate_contract_yaml(
        self,
        contract_content: str,
        contract_type: str = "effect"
    ) -> ContractValidationResult:
        """
        Validate a YAML contract against ONEX standards.

        Args:
            contract_content: YAML contract content
            contract_type: Type of contract (effect, compute, reducer, orchestrator)

        Returns:
            Validation result with score and violations
        """
        # Implementation needed:
        # 1. Parse YAML content
        # 2. Validate against contract schema
        # 3. Check ONEX compliance
        # 4. Return structured result
        pass

    def validate_model_compliance(
        self,
        model_code: str,
        contract_yaml: str
    ) -> ContractValidationResult:
        """
        Validate Pydantic model against contract.

        Args:
            model_code: Generated Pydantic model code
            contract_yaml: Contract YAML content

        Returns:
            Validation result
        """
        # Implementation needed:
        # 1. Parse model code
        # 2. Extract field definitions
        # 3. Compare with contract schema
        # 4. Check type compliance
        pass
```

**Action**: Implement contract validation logic with ONEX compliance checking.

### 4. Mixin Discovery API (HIGH)

**Current State**: No programmatic way to discover available mixins  
**Required**: API to query mixins and their metadata

#### Required File to Create:

**File**: `src/omnibase_core/discovery/mixin_discovery.py`

```python
from typing import List, Dict, Optional
from pathlib import Path
import yaml

class MixinInfo(BaseModel):
    name: str
    description: str
    version: str
    category: str
    requires: List[str]
    compatible_with: List[str]
    incompatible_with: List[str]
    config_schema: Dict[str, Any]
    usage_examples: List[str]

class MixinDiscovery:
    """Discover and query available mixins"""

    def __init__(self, mixins_path: Optional[Path] = None):
        self.mixins_path = mixins_path or Path(__file__).parent.parent / "mixins"

    def get_all_mixins(self) -> List[MixinInfo]:
        """Get all available mixins with metadata"""
        # Implementation needed:
        # 1. Scan mixins directory
        # 2. Load metadata from YAML files
        # 3. Return list of MixinInfo objects
        pass

    def get_mixins_by_category(self, category: str) -> List[MixinInfo]:
        """Get mixins filtered by category"""
        pass

    def find_compatible_mixins(self, base_mixins: List[str]) -> List[MixinInfo]:
        """Find mixins compatible with given base mixins"""
        pass

    def get_mixin_dependencies(self, mixin_name: str) -> List[str]:
        """Get transitive dependencies for a mixin"""
        pass
```

**Action**: Implement mixin discovery with metadata parsing.

## Success Criteria

### Week 1 Deliverables:

1. ✅ **Mixin metadata files created** for all core mixins
2. ✅ **Base node interfaces locked down** with version comments  
3. ✅ **Contract validator implemented** with ONEX compliance
4. ✅ **Mixin discovery API working** with metadata queries

### Validation Tests:

```python
# Test 1: Mixin discovery
discovery = MixinDiscovery()
mixins = discovery.get_all_mixins()
assert len(mixins) >= 8  # Minimum expected mixins
assert any(m.name == "MixinEventBus" for m in mixins)

# Test 2: Contract validation  
validator = ContractValidator()
result = validator.validate_contract_yaml(sample_contract, "effect")
assert result.is_valid
assert result.score >= 0.8

# Test 3: Interface stability
from omnibase_core.core.node_effect_service import NodeEffectService
# Should not raise import errors
# Should have expected abstract methods
```

## Impact on Code Generation

**Without these requirements**:
- ❌ Cannot discover available mixins for composition
- ❌ Cannot validate generated contracts  
- ❌ Cannot ensure generated code implements required interfaces
- ❌ Cannot check mixin compatibility

**With these requirements**:
- ✅ Can generate nodes with proper mixin composition
- ✅ Can validate generated contracts automatically
- ✅ Can ensure ONEX compliance in generated code
- ✅ Can provide intelligent mixin recommendations

## Next Steps

1. **Create mixin metadata files** (Day 1-2)
2. **Lock down base node interfaces** (Day 2)  
3. **Implement contract validator** (Day 3-4)
4. **Implement mixin discovery** (Day 4-5)
5. **Test with omniclaude integration** (Day 5)

## Contact

- **Primary**: omniclaude code generation workflow
- **Repository**: omnibase_core  
- **Dependencies**: None (this enables others)
- **Blocking**: omniclaude Phase 2-3 (Template System, Contract Generation)
