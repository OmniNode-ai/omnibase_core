# ONEX Repository Structure Standards

**Document Version**: 1.0
**Generated**: 2025-09-14
**Authority**: Definitive reference for all omnibase/omninode repositories
**Scope**: Universal standards for the entire ONEX ecosystem

## Executive Summary

This document establishes the canonical repository structure standards for all omnibase and omninode repositories according to ONEX architectural principles. These standards enforce the fundamental ONEX principle: "Everything should be a model or enum" and ensure consistent organization across the entire ecosystem.

## Table of Contents

1. [Core ONEX Principles](#core-onex-principles)
2. [Canonical Repository Structure](#canonical-repository-structure)
3. [Component Placement Rules](#component-placement-rules)
4. [ONEX Compliance Guidelines](#onex-compliance-guidelines)
5. [Migration Guidelines](#migration-guidelines)
6. [Validation Procedures](#validation-procedures)
7. [Cross-Repository Consistency](#cross-repository-consistency)
8. [Enforcement and Governance](#enforcement-and-governance)

## Core ONEX Principles

### 1. Everything is a Model or Enum Principle

**Primary Rule**: All data structures must be either:
- **Models**: Pydantic BaseModel classes with strong typing
- **Enums**: Python Enum classes for fixed value sets

**Implications**:
- No plain dictionaries or tuples for data transfer
- No primitive types for complex data
- No untyped data structures
- All interfaces must be contract-driven

### 2. Node-Based Architecture

**Four-Node Pattern**: All tools and utilities must be organized as nodes:
- **EFFECT**: Data persistence and external interactions
- **COMPUTE**: Business logic computations
- **REDUCER**: Data aggregation and stream processing
- **ORCHESTRATOR**: Workflow coordination

### 3. Zero Backwards Compatibility Policy

**Breaking Changes Always Acceptable**:
- No deprecated code maintenance
- All models MUST conform to current protocols
- Clean, modern architecture only
- Remove old patterns immediately

### 4. Strong Typing Enforcement

**Type Safety Requirements**:
- Comprehensive type hints throughout
- mypy compliance mandatory
- Protocol-based interfaces
- Generic types with constraints

## Canonical Repository Structure

### Root Level Structure

```
repository-name/
├── src/                           # Source code (MANDATORY)
│   └── {package_name}/           # Main package
├── tests/                        # Test code (MANDATORY)
│   ├── unit/                     # Unit tests
│   ├── integration/             # Integration tests
│   └── performance/             # Performance tests
├── docs/                        # Documentation (MANDATORY)
│   ├── api/                     # API documentation
│   ├── architecture/            # Architecture docs
│   └── guides/                  # User guides
├── deployment/                  # Deployment configurations
│   ├── docker/                  # Docker configurations
│   ├── k8s/                     # Kubernetes manifests
│   └── config/                  # Environment configs
├── examples/                    # Usage examples
├── scripts/                     # Development scripts
├── .github/                     # GitHub workflows
├── pyproject.toml              # Project configuration
├── CLAUDE.md                   # Claude Code instructions
├── README.md                   # Project overview
└── .gitignore                  # Git ignore rules
```

### Source Code Organization (src/)

```
src/{package_name}/
├── models/                      # ONEX Models (MANDATORY)
│   ├── core/                   # Core domain models
│   ├── {domain}/               # Domain-specific models
│   └── types/                  # Type definitions and constraints
├── enums/                      # ONEX Enums (MANDATORY)
│   ├── core/                   # Core enumerations
│   └── {domain}/               # Domain-specific enums
├── nodes/                      # ONEX Nodes (replaces tools/)
│   ├── effect/                 # Effect nodes
│   ├── compute/                # Compute nodes
│   ├── reducer/                # Reducer nodes
│   └── orchestrator/           # Orchestrator nodes
├── core/                       # Core infrastructure
│   ├── infrastructure_service_bases.py
│   ├── model_onex_container.py
│   └── onex_protocols.py
├── services/                   # Service layer
│   ├── {domain}/               # Domain-specific services
│   └── infrastructure/         # Infrastructure services
├── protocols/                  # Protocol definitions
│   ├── contracts/              # YAML subcontracts
│   └── interfaces/             # Protocol interfaces
├── config/                     # Configuration models
├── exceptions/                 # Exception definitions
├── mixins/                     # Reusable mixins
├── utils/                      # Utility functions
├── cli/                        # Command-line interface
└── __init__.py                 # Package initialization
```

## Component Placement Rules

### Models Organization

**Rule**: All models go in `src/{package}/models/`

**Structure**:
```
models/
├── core/                       # Core domain models
│   ├── model_base_entity.py   # Base entity models
│   ├── model_container.py     # Container models
│   └── model_response.py      # Response models
├── {domain}/                  # Domain-specific models
│   ├── model_{entity}.py      # Entity models
│   ├── model_{operation}.py   # Operation models
│   └── model_{result}.py      # Result models
├── types/                     # Type definitions
│   ├── model_typed_value.py   # Generic typed values
│   ├── model_validation_result.py  # Validation results
│   └── protocol_constraints.py     # Protocol type constraints
├── __init__.py               # Model exports
└── __exposed__.py            # Public API exports
```

**Naming Conventions**:
- File names: `model_{description}.py`
- Class names: `Model{Description}`
- Domain folders: `{domain_name}/`

### Enums Organization

**Rule**: All enums go in `src/{package}/enums/`

**Structure**:
```
enums/
├── core/                      # Core enumerations
│   ├── enum_status.py        # Status enumerations
│   ├── enum_operation_type.py # Operation types
│   └── enum_priority.py      # Priority levels
├── {domain}/                 # Domain-specific enums
│   ├── enum_{concept}.py     # Domain concept enums
│   └── enum_{state}.py       # State enumerations
├── __init__.py              # Enum exports
└── __exposed__.py           # Public API exports
```

**Naming Conventions**:
- File names: `enum_{description}.py`
- Class names: `Enum{Description}`
- Values: `UPPER_SNAKE_CASE`

### Nodes Organization (replaces tools/)

**Rule**: All utilities must be implemented as ONEX nodes in `src/{package}/nodes/`

**Structure**:
```
nodes/
├── effect/                    # Effect nodes (data persistence)
│   ├── node_database_writer.py
│   ├── node_file_handler.py
│   └── node_api_client.py
├── compute/                   # Compute nodes (business logic)
│   ├── node_data_processor.py
│   ├── node_validator.py
│   └── node_transformer.py
├── reducer/                   # Reducer nodes (aggregation)
│   ├── node_data_aggregator.py
│   ├── node_stream_processor.py
│   └── node_batch_processor.py
├── orchestrator/             # Orchestrator nodes (coordination)
│   ├── node_workflow_manager.py
│   ├── node_task_coordinator.py
│   └── node_pipeline_controller.py
├── __init__.py              # Node exports
└── __exposed__.py           # Public API exports
```

**Node Implementation Pattern**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeService
from omnibase_core.core.model_onex_container import ModelOnexContainer

class Node{Description}(NodeService):
    """ONEX {TYPE} node for {purpose}."""

    def __init__(self, container: ModelOnexContainer):
        super().__init__(container)

    async def process(self, input_model: Model{Input}) -> Model{Output}:
        """Process input through ONEX node pattern."""
        # Implementation follows ONEX patterns
        pass
```

### Core Infrastructure

**Rule**: Core ONEX infrastructure goes in `src/{package}/core/`

**Required Files**:
```
core/
├── infrastructure_service_bases.py  # Base service classes
├── model_onex_container.py         # Dependency injection
├── onex_protocols.py              # Core protocols
├── core_structured_logging.py     # Logging infrastructure
├── core_errors.py                 # Error handling
└── node_reducer_service.py        # Node reducer base
```

### Services Organization

**Rule**: Service layer goes in `src/{package}/services/`

**Structure**:
```
services/
├── infrastructure/           # Infrastructure services
│   ├── service_container.py
│   ├── service_health.py
│   └── service_registry.py
├── {domain}/                # Domain-specific services
│   ├── service_{operation}.py
│   └── service_{manager}.py
└── __init__.py             # Service exports
```

### Protocols and Contracts

**Rule**: Protocol definitions go in `src/{package}/protocols/`

**Structure**:
```
protocols/
├── contracts/               # YAML subcontracts
│   ├── {domain}.yaml
│   └── {operation}.yaml
├── interfaces/             # Protocol interfaces
│   ├── protocol_{interface}.py
│   └── protocol_{contract}.py
└── __init__.py            # Protocol exports
```

### Configuration Management

**Rule**: Configuration models go in `src/{package}/config/`

**Structure**:
```
config/
├── model_app_config.py     # Application configuration
├── model_env_config.py     # Environment configuration
├── model_service_config.py # Service configuration
└── __init__.py            # Config exports
```

### CLI Components

**Rule**: CLI code goes in `src/{package}/cli/`

**Structure**:
```
cli/
├── commands/              # CLI command implementations
│   ├── cmd_{operation}.py
│   └── cmd_{utility}.py
├── models/               # CLI-specific models
│   ├── model_cli_config.py
│   └── model_cli_result.py
├── main.py              # CLI entry point
└── __init__.py          # CLI exports
```

### Examples Organization

**Rule**: Examples go in `examples/` at repository root

**Structure**:
```
examples/
├── basic/               # Basic usage examples
├── advanced/           # Advanced patterns
├── integration/        # Integration examples
└── README.md          # Examples documentation
```

## ONEX Compliance Guidelines

### Model Design Compliance

**Requirements**:
1. **All models extend BaseModel**: `from pydantic import BaseModel`
2. **Strong typing mandatory**: All fields must have explicit types
3. **Field validation**: Use Pydantic validators for complex validation
4. **Immutable by default**: Use `frozen=True` for value objects
5. **Factory methods prohibited**: Direct instantiation only

**Compliant Model Pattern**:
```python
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path

class ModelValidationResult(BaseModel):
    """ONEX-compliant validation result model."""

    is_valid: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    file_path: Path | None = Field(None, description="Path to validated file")

    @classmethod
    def success(cls, file_path: Path | None = None) -> "ModelValidationResult":
        """Create successful validation result."""
        return cls(is_valid=True, file_path=file_path)

    @classmethod
    def failure(cls, errors: list[str], file_path: Path | None = None) -> "ModelValidationResult":
        """Create failed validation result."""
        return cls(is_valid=False, errors=errors, file_path=file_path)
```

### Enum Design Compliance

**Requirements**:
1. **All enums extend Enum**: `from enum import Enum`
2. **String values preferred**: Use string values for serialization
3. **UPPER_SNAKE_CASE**: All enum values in uppercase
4. **Descriptive names**: Clear, unambiguous naming

**Compliant Enum Pattern**:
```python
from enum import Enum

class EnumWorkflowType(Enum):
    """ONEX-compliant workflow type enumeration."""

    DOCUMENT_REGENERATION = "document_regeneration"
    CODE_ANALYSIS = "code_analysis"
    DATA_PROCESSING = "data_processing"
    SYSTEM_ORCHESTRATION = "system_orchestration"
```

### Node Design Compliance

**Requirements**:
1. **Extend NodeService**: All nodes extend appropriate base class
2. **Dependency injection**: Use ModelOnexContainer
3. **Async processing**: All processing methods async
4. **Model-based I/O**: Input/output through models only

**Compliant Node Pattern**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeEffectService
from omnibase_core.core.model_onex_container import ModelOnexContainer
from omnibase_core.models.core.model_processing_input import ModelProcessingInput
from omnibase_core.models.core.model_processing_output import ModelProcessingOutput

class NodeFileProcessor(NodeEffectService):
    """ONEX-compliant effect node for file processing."""

    def __init__(self, container: ModelOnexContainer):
        super().__init__(container)

    async def process(self, input_data: ModelProcessingInput) -> ModelProcessingOutput:
        """Process file through ONEX effect node."""
        # ONEX-compliant implementation
        result = await self._process_file(input_data.file_path)

        return ModelProcessingOutput(
            success=result.success,
            output_data=result.data,
            processing_time_ms=result.duration
        )
```

## Migration Guidelines

### Phase 1: Structure Analysis and Planning

**Steps**:
1. **Audit Current Structure**: Document current repository organization
2. **Identify Violations**: List all structural violations against ONEX standards
3. **Create Migration Plan**: Plan phased migration with minimal disruption
4. **Backup Strategy**: Ensure rollback capability

**Analysis Checklist**:
- [ ] `tools/` directory exists (must migrate to `nodes/`)
- [ ] `types/` directory at root (must migrate to `models/types/`)
- [ ] `metadata/` directory exists (must migrate to `models/`)
- [ ] Plain dictionaries used for data transfer
- [ ] Untyped functions or classes
- [ ] Factory method anti-patterns

### Phase 2: Component Migration

**Migration Order**:
1. **Models First**: Migrate all data structures to models/
2. **Enums Second**: Migrate all constants to enums/
3. **Nodes Third**: Transform tools/ to nodes/
4. **Services Fourth**: Reorganize service layer
5. **Protocols Last**: Implement protocol compliance

**Migration Scripts**:
```python
# Example migration script for tools/ -> nodes/
import shutil
from pathlib import Path

def migrate_tools_to_nodes(repo_path: Path):
    """Migrate tools/ directory to nodes/ structure."""

    tools_path = repo_path / "src" / "{package}" / "tools"
    nodes_path = repo_path / "src" / "{package}" / "nodes"

    if not tools_path.exists():
        return

    # Create nodes/ structure
    (nodes_path / "effect").mkdir(parents=True, exist_ok=True)
    (nodes_path / "compute").mkdir(parents=True, exist_ok=True)
    (nodes_path / "reducer").mkdir(parents=True, exist_ok=True)
    (nodes_path / "orchestrator").mkdir(parents=True, exist_ok=True)

    # Migrate files based on functionality
    for tool_file in tools_path.glob("*.py"):
        # Analyze tool and place in appropriate node category
        target_category = analyze_tool_category(tool_file)
        target_path = nodes_path / target_category / f"node_{tool_file.stem}.py"

        # Transform tool to node pattern
        transform_tool_to_node(tool_file, target_path)
```

### Phase 3: Code Transformation

**Transformation Rules**:

1. **Dictionary to Model**:
```python
# OLD (violates ONEX)
def process_data(data: dict) -> dict:
    return {"result": data["input"] * 2}

# NEW (ONEX compliant)
from models.core.model_processing_input import ModelProcessingInput
from models.core.model_processing_output import ModelProcessingOutput

async def process_data(input_model: ModelProcessingInput) -> ModelProcessingOutput:
    result_value = input_model.input_value * 2
    return ModelProcessingOutput(result=result_value)
```

2. **Constants to Enums**:
```python
# OLD (violates ONEX)
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETE = "complete"

# NEW (ONEX compliant)
from enum import Enum

class EnumProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
```

3. **Tools to Nodes**:
```python
# OLD (violates ONEX)
class FileProcessor:
    def process_file(self, file_path: str) -> bool:
        # Tool implementation
        pass

# NEW (ONEX compliant)
class NodeFileProcessor(NodeEffectService):
    def __init__(self, container: ModelOnexContainer):
        super().__init__(container)

    async def process(self, input_model: ModelFileInput) -> ModelFileOutput:
        # Node implementation
        pass
```

### Phase 4: Validation and Testing

**Validation Steps**:
1. **Structure Validation**: Verify all directories follow ONEX standards
2. **Model Validation**: Ensure all models extend BaseModel
3. **Enum Validation**: Ensure all enums extend Enum
4. **Node Validation**: Ensure all nodes extend appropriate base classes
5. **Integration Testing**: Verify all components work together

## Validation Procedures

### Automated Structure Validation

**Validation Script**:
```python
#!/usr/bin/env python3
"""ONEX Repository Structure Validation Script"""

import sys
from pathlib import Path
from typing import List, Dict, Any

class OnexStructureValidator:
    """Validates repository structure against ONEX standards."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.violations: List[str] = []

    def validate_structure(self) -> Dict[str, Any]:
        """Validate complete repository structure."""

        self._validate_root_structure()
        self._validate_source_structure()
        self._validate_models_structure()
        self._validate_enums_structure()
        self._validate_nodes_structure()

        return {
            "is_compliant": len(self.violations) == 0,
            "violations": self.violations,
            "total_violations": len(self.violations)
        }

    def _validate_root_structure(self):
        """Validate root level directory structure."""

        required_dirs = ["src", "tests", "docs"]
        for dir_name in required_dirs:
            if not (self.repo_path / dir_name).exists():
                self.violations.append(f"Missing required directory: {dir_name}/")

        # Check for violations
        if (self.repo_path / "tools").exists():
            self.violations.append("tools/ directory found - must migrate to src/{package}/nodes/")

        if (self.repo_path / "types").exists():
            self.violations.append("types/ directory found - must migrate to src/{package}/models/types/")

    def _validate_source_structure(self):
        """Validate source code structure."""

        src_path = self.repo_path / "src"
        if not src_path.exists():
            return

        # Find package directory
        package_dirs = [d for d in src_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if not package_dirs:
            self.violations.append("No package directory found in src/")
            return

        package_path = package_dirs[0]  # Assume first package

        required_dirs = ["models", "enums", "core"]
        for dir_name in required_dirs:
            if not (package_path / dir_name).exists():
                self.violations.append(f"Missing required directory: src/{package_path.name}/{dir_name}/")

        # Check for violations
        if (package_path / "tools").exists():
            self.violations.append(f"tools/ found in src/{package_path.name}/ - must migrate to nodes/")

        if (package_path / "types").exists():
            self.violations.append(f"types/ found in src/{package_path.name}/ - must migrate to models/types/")
```

### Pre-commit Hooks

**Hook Configuration** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: local
    hooks:
      - id: onex-structure-validation
        name: ONEX Structure Validation
        entry: python scripts/validate_onex_structure.py
        language: python
        stages: [commit]
        pass_filenames: false

      - id: onex-model-validation
        name: ONEX Model Validation
        entry: python scripts/validate_onex_models.py
        language: python
        files: ^src/.*/models/.*\.py$

      - id: onex-enum-validation
        name: ONEX Enum Validation
        entry: python scripts/validate_onex_enums.py
        language: python
        files: ^src/.*/enums/.*\.py$
```

### CI/CD Integration

**GitHub Actions Workflow**:
```yaml
name: ONEX Compliance Check
on: [push, pull_request]

jobs:
  onex-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: ONEX Structure Validation
        run: python scripts/validate_onex_structure.py --strict

      - name: ONEX Model Validation
        run: python scripts/validate_onex_models.py --all

      - name: ONEX Enum Validation
        run: python scripts/validate_onex_enums.py --all

      - name: Type Safety Check
        run: mypy src/ --strict
```

## Cross-Repository Consistency

### Shared Standards

**Naming Conventions**:
- **Repositories**: `{purpose}_{scope}` (e.g., `omnibase_core`, `omninode_ui`)
- **Packages**: `{org}_{purpose}` (e.g., `omnibase_core`, `omninode_agents`)
- **Models**: `Model{Description}` (e.g., `ModelValidationResult`)
- **Enums**: `Enum{Description}` (e.g., `EnumWorkflowType`)
- **Nodes**: `Node{Description}` (e.g., `NodeFileProcessor`)

**Import Patterns**:
```python
# Standard import organization
# 1. Standard library
import asyncio
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

# 2. Third-party libraries
from pydantic import BaseModel, Field

# 3. Local imports - absolute imports only
from omnibase_core.models.core.model_base import ModelBase
from omnibase_core.enums.core.enum_status import EnumStatus
from omnibase_core.nodes.effect.node_file_processor import NodeFileProcessor
```

**Configuration Standards**:
```toml
# pyproject.toml - Required sections for all repositories
[tool.poetry]
name = "{package-name}"
version = "0.1.0"
description = "ONEX-compliant {description}"
authors = ["OmniNode Team <team@omninode.ai>"]

[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.5.0"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Dependency Management

**Shared Dependencies**:
- **Core Framework**: `omnibase-spi` - Service Provider Interface
- **Core Implementation**: `omnibase-core` - Core ONEX implementation
- **Type System**: Pydantic 2.5+ for all models
- **Async Framework**: asyncio for all async operations
- **Logging**: structlog for structured logging
- **Testing**: pytest + pytest-asyncio for testing
- **Type Checking**: mypy with strict mode

**Dependency Graph**:
```
omnibase-spi (protocols and interfaces)
    ↓
omnibase-core (core implementation)
    ↓
domain-specific repositories (implementations)
    ↓
application repositories (applications)
```

## Enforcement and Governance

### Governance Structure

**Decision Authority**:
1. **ONEX Architecture Committee**: Final authority on structural standards
2. **Repository Maintainers**: Enforce standards in their repositories
3. **Automated Systems**: Continuous validation and compliance checking

### Compliance Levels

**Level 1 - Critical (Breaking)**:
- Repository structure violations
- Model/enum compliance violations
- Type safety violations
- **Action**: Block merge, require immediate fix

**Level 2 - Warning (Non-breaking)**:
- Naming convention violations
- Documentation issues
- Minor organizational issues
- **Action**: Warning, fix in next release

**Level 3 - Advisory (Optimization)**:
- Performance optimizations
- Code style improvements
- Best practice suggestions
- **Action**: Advisory notice, optional fix

### Monitoring and Metrics

**Compliance Metrics**:
- **Structure Compliance**: % of repositories following structure standards
- **Model Compliance**: % of models extending BaseModel
- **Enum Compliance**: % of constants converted to enums
- **Type Safety**: % of code with complete type annotations
- **Test Coverage**: % of code covered by tests

**Reporting Dashboard**:
- Weekly compliance reports
- Repository-level scorecards
- Trend analysis and improvement tracking
- Automated notifications for violations

## Implementation Timeline

### Phase 1: Foundation (Week 1-2)
- [ ] Create validation scripts
- [ ] Set up CI/CD integration
- [ ] Document current state across all repositories

### Phase 2: Core Repositories (Week 3-4)
- [ ] Migrate omnibase-spi to standards
- [ ] Migrate omnibase-core to standards
- [ ] Update shared tooling and templates

### Phase 3: Domain Repositories (Week 5-8)
- [ ] Migrate omniagent repositories
- [ ] Migrate omnibase_infra repository
- [ ] Migrate omnimemory repository
- [ ] Migrate all remaining repositories

### Phase 4: Validation and Optimization (Week 9-10)
- [ ] Complete compliance validation
- [ ] Performance optimization
- [ ] Documentation finalization
- [ ] Training and rollout

## Appendices

### Appendix A: Common Migration Patterns

**Pattern 1: Dictionary to Model Migration**
```python
# Before
def create_user(data: dict) -> dict:
    return {
        "id": generate_id(),
        "name": data["name"],
        "email": data["email"],
        "created": datetime.utcnow().isoformat()
    }

# After
from models.user.model_user_input import ModelUserInput
from models.user.model_user_output import ModelUserOutput

async def create_user(input_model: ModelUserInput) -> ModelUserOutput:
    user_id = await generate_id()
    return ModelUserOutput(
        id=user_id,
        name=input_model.name,
        email=input_model.email,
        created=datetime.utcnow()
    )
```

**Pattern 2: Constants to Enums Migration**
```python
# Before
class Constants:
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_PENDING = "pending"

# After
from enum import Enum

class EnumUserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
```

### Appendix B: Validation Script Examples

**Complete Structure Validator**:
```python
#!/usr/bin/env python3
"""Complete ONEX structure validation script."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

def validate_repository_structure(repo_path: Path) -> Dict[str, Any]:
    """Validate complete repository structure against ONEX standards."""

    validator = OnexStructureValidator(repo_path)
    results = validator.validate_structure()

    # Generate detailed report
    report = {
        "repository": repo_path.name,
        "compliance_level": "COMPLIANT" if results["is_compliant"] else "NON_COMPLIANT",
        "total_violations": results["total_violations"],
        "violations": results["violations"],
        "recommendations": validator.get_recommendations(),
        "migration_priority": validator.get_migration_priority()
    }

    return report

if __name__ == "__main__":
    repo_path = Path.cwd()
    results = validate_repository_structure(repo_path)

    print(json.dumps(results, indent=2))

    if not results["compliance_level"] == "COMPLIANT":
        sys.exit(1)
```

### Appendix C: Repository Templates

**New Repository Template Structure**:
```
template-repository/
├── src/
│   └── {package_name}/
│       ├── models/
│       │   ├── core/
│       │   ├── types/
│       │   ├── __init__.py
│       │   └── __exposed__.py
│       ├── enums/
│       │   ├── core/
│       │   ├── __init__.py
│       │   └── __exposed__.py
│       ├── nodes/
│       │   ├── effect/
│       │   ├── compute/
│       │   ├── reducer/
│       │   ├── orchestrator/
│       │   ├── __init__.py
│       │   └── __exposed__.py
│       ├── core/
│       ├── services/
│       ├── protocols/
│       ├── config/
│       ├── exceptions/
│       ├── mixins/
│       ├── utils/
│       ├── cli/
│       └── __init__.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── performance/
├── docs/
│   ├── api/
│   ├── architecture/
│   └── guides/
├── deployment/
├── examples/
├── scripts/
├── .github/
├── pyproject.toml
├── CLAUDE.md
├── README.md
└── .gitignore
```

---

**Document Status**: ACTIVE
**Last Updated**: 2025-09-14
**Next Review**: 2025-10-14
**Approval**: ONEX Architecture Committee

This document serves as the definitive reference for repository organization across the entire omnibase/omninode ecosystem and must be followed by all repositories without exception.
