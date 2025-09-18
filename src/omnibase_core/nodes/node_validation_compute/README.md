# ONEX Validation Nodes

This directory contains ONEX validation nodes following the standardized node architecture pattern for centralized validation across the ONEX ecosystem.

## Node Architecture

Validation nodes follow the ONEX 4-node architecture pattern:

```
validation/
├── node_import_validator_compute/
│   └── v1_0_0/
│       ├── node.py                 # NodeImportValidatorCompute implementation
│       ├── contract.yaml          # Node contract specification
│       └── models/
│           └── validation_models.py
├── node_validation_orchestrator/
│   └── v1_0_0/
│       ├── node.py                 # NodeValidationOrchestratorOrchestrator implementation
│       ├── contract.yaml          # Node contract specification
│       └── models/
│           └── orchestration_models.py
├── node_quality_validator_effect/
│   └── v1_0_0/
│       ├── node.py                 # NodeQualityValidatorEffect implementation
│       ├── contract.yaml          # Node contract specification
│       └── models/
│           └── quality_models.py
└── node_compliance_validator_reducer/
    └── v1_0_0/
        ├── node.py                 # NodeComplianceValidatorReducer implementation
        ├── contract.yaml          # Node contract specification
        └── models/
            └── compliance_models.py
```

## Node Responsibilities

### NodeImportValidatorCompute
- **Type**: COMPUTE node
- **Purpose**: Validate import statements and dependencies
- **Input**: Import specifications and dependency requirements
- **Output**: ValidationResult with import analysis
- **Protocols**: ProtocolImportValidator (from omnibase_spi)

### NodeValidationOrchestratorOrchestrator
- **Type**: ORCHESTRATOR node
- **Purpose**: Coordinate validation workflow across all validation nodes
- **Input**: Validation request with scope and requirements
- **Output**: Comprehensive validation report
- **Protocols**: ProtocolValidationOrchestrator (from omnibase_spi)

### NodeQualityValidatorEffect
- **Type**: EFFECT node
- **Purpose**: Perform code quality checks and standards compliance
- **Input**: Code content and quality standards
- **Output**: Quality assessment with recommendations
- **Protocols**: ProtocolQualityValidator (from omnibase_spi)

### NodeComplianceValidatorReducer
- **Type**: REDUCER node
- **Purpose**: Aggregate validation results and generate final compliance report
- **Input**: Multiple ValidationResult objects
- **Output**: Consolidated compliance report
- **Protocols**: ProtocolComplianceValidator (from omnibase_spi)

## Dependencies

### Core Infrastructure
- **ModelONEXContainer**: Dependency injection container
- **ModelValidationConfig**: Validation configuration model
- **ValidationResult**: Standard validation result model
- **ValidationException hierarchy**: From validation.exceptions

### Protocol Interfaces (omnibase_spi)
- **ProtocolImportValidator**: Import validation interface
- **ProtocolValidationOrchestrator**: Orchestration interface
- **ProtocolQualityValidator**: Quality validation interface
- **ProtocolComplianceValidator**: Compliance validation interface

## Integration Pattern

Validation nodes integrate with repository-specific validation scripts via dependency injection:

```python
from omnibase_core.core.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.validation.node_validation_orchestrator.v1_0_0.node import NodeValidationOrchestratorOrchestrator

# Inject validation orchestrator
container = ModelONEXContainer()
orchestrator = container.get_validator_orchestrator()

# Repository-specific validation
result = orchestrator.validate_repository(validation_config)
```

## Implementation Status

**🚧 Planned Implementation**

These nodes will be implemented once the following infrastructure is ready:
1. Protocol interfaces defined in omnibase_spi
2. ModelONEXContainer dependency injection framework
3. Centralized validation utilities completed

## Temporary Solutions

Until these nodes are implemented, repositories use temporary validation abstractions that will be replaced by these centralized nodes.

## Migration Path

1. **Phase 1**: Implement protocol interfaces in omnibase_spi
2. **Phase 2**: Create validation node implementations
3. **Phase 3**: Update repository validation scripts to use dependency injection
4. **Phase 4**: Remove temporary validation abstractions from repositories
