# Omni* Ecosystem Standardization Framework

**Version**: 1.0.0
**Date**: 2025-01-16
**Purpose**: Complete repository standardization across all omni* repositories
**Scope**: Structure, naming conventions, type safety, and quality enforcement

## 🎯 Executive Summary

This framework addresses critical structural governance issues across 8+ omni* repositories:
- **1,279+ scattered model files** in omnibase_core alone
- **Inconsistent directory structures** across all repositories
- **No naming convention enforcement**
- **Excessive Optional type usage** without business justification
- **Scattered protocol definitions** (should be centralized in omnibase_spi)
- **No standardized quality checks** across repositories

## 📁 Mandatory Repository Structure

Every omni* repository MUST follow this exact structure:

```
{REPO_NAME}/
├── .github/                          # GitHub workflows
│   ├── workflows/
│   │   ├── omni-standards-compliance.yml  # Inherited from omnibase_core
│   │   └── {repo-specific}.yml       # Additional repo workflows
│   └── dependabot.yml                # Dependency management
├── src/
│   └── {REPO_NAME}/
│       ├── models/                   # ALL models organized by domain
│       │   ├── workflow/
│       │   │   ├── __init__.py
│       │   │   ├── model_workflow_state.py
│       │   │   └── model_workflow_execution.py
│       │   ├── infrastructure/
│       │   │   ├── __init__.py
│       │   │   ├── model_infrastructure_node.py
│       │   │   └── model_infrastructure_config.py
│       │   ├── agent/
│       │   │   ├── __init__.py
│       │   │   ├── model_agent_context.py
│       │   │   └── model_agent_response.py
│       │   └── core/
│       │       ├── __init__.py
│       │       ├── model_base_node.py
│       │       └── model_container_config.py
│       ├── enums/                    # ALL enums organized by domain
│       │   ├── workflow/
│       │   │   ├── __init__.py
│       │   │   ├── enum_workflow_status.py
│       │   │   └── enum_workflow_type.py
│       │   ├── infrastructure/
│       │   │   ├── __init__.py
│       │   │   ├── enum_node_type.py
│       │   │   └── enum_deployment_status.py
│       │   ├── agent/
│       │   │   ├── __init__.py
│       │   │   ├── enum_agent_type.py
│       │   │   └── enum_agent_status.py
│       │   └── core/
│       │       ├── __init__.py
│       │       ├── enum_log_level.py
│       │       └── enum_environment.py
│       ├── protocols/                # ONLY for omnibase_spi (others import)
│       │   ├── core/
│       │   ├── workflow/
│       │   ├── services/
│       │   └── validation/
│       ├── services/                 # Service implementations
│       │   └── service_{NAME}/
│       │       └── v1_0_0/
│       │           ├── service.py
│       │           ├── protocols/
│       │           └── models/       # Service-specific models only
│       ├── nodes/                    # ONEX 4-node implementations
│       │   └── node_{DOMAIN}_{NAME}_{TYPE}/
│       │       └── v1_0_0/
│       │           ├── node.py
│       │           ├── contracts/
│       │           │   └── {node}_contract.yaml
│       │           └── utils/        # Node-specific utilities only
│       ├── core/                     # Core infrastructure
│       ├── utils/                    # General utilities
│       │   ├── util_string_formatter.py
│       │   ├── util_type_validator.py
│       │   └── util_performance_monitor.py
│       ├── exceptions/               # Custom exceptions
│       │   ├── exception_validation.py
│       │   ├── exception_node.py
│       │   └── exception_service.py
│       └── __init__.py
├── tests/                            # Mirror src/ structure exactly
│   ├── unit/
│   │   └── {REPO_NAME}/             # Mirrors src/{REPO_NAME}
│   ├── integration/
│   │   └── {REPO_NAME}/
│   └── fixtures/
├── tools/                           # Development tools
│   ├── validation/
│   │   ├── validate_structure.py
│   │   ├── validate_naming.py
│   │   └── audit_optional.py
│   ├── migration/
│   │   └── migrate_repository.py
│   └── hooks/
│       └── pre_commit_hooks.py
├── docs/                            # Documentation
│   ├── architecture/
│   ├── templates/
│   └── standards/
├── scripts/                         # Deployment scripts
├── .pre-commit-config.yaml         # Inherited from omnibase_core
├── .omni-structure.yaml            # Structure validation config
├── pyproject.toml                  # Python configuration
├── CLAUDE.md                       # AI assistant instructions
├── STANDARDS_COMPLIANCE.md        # Live compliance report
└── README.md
```

## 🚫 Forbidden Directory Patterns

These directory patterns are BANNED and will cause CI failure:

```
❌ /model/                   # Use /models/ (plural)
❌ /mixin/                   # Use /mixins/ (plural)
❌ /enum/                    # Use /enums/ (plural)
❌ /protocol/                # Use /protocols/ (plural)
❌ /{anything}/models/       # Models belong in root /models/ only
❌ /{anything}/enums/        # Enums belong in root /enums/ only
❌ /src/{repo}/protocols/    # Only allowed in omnibase_spi
❌ /scattered_models/        # All models must be domain-organized
```

## 📝 Strict Naming Conventions

### File Naming Standards
```python
# ✅ CORRECT naming patterns
model_user_profile.py           # Models: model_*
protocol_event_handler.py       # Protocols: protocol_*
node_compute_calculator.py      # Nodes: node_*
enum_workflow_status.py         # Enums: enum_*
service_contract_loader.py      # Services: service_*
util_string_formatter.py        # Utilities: util_*
mixin_health_check.py          # Mixins: mixin_*
exception_validation.py         # Exceptions: exception_*

# ❌ WRONG naming patterns
user_profile.py                 # Missing model_ prefix
event_handler.py               # Missing protocol_ prefix
calculator_node.py             # Wrong word order
status.py                      # Missing enum_ prefix
validation_error.py            # Should be exception_validation.py
```

### Class Naming Standards
```python
# ✅ CORRECT class naming
class ModelUserProfile(BaseModel): pass        # Models: Model*
class ProtocolEventHandler(Protocol): pass     # Protocols: Protocol*
class NodeComputeCalculator(NodeCompute): pass # Nodes: Node*
class EnumWorkflowStatus(Enum): pass          # Enums: Enum*
class ServiceContractLoader: pass             # Services: Service*
class MixinHealthCheck: pass                  # Mixins: Mixin*
class ExceptionValidation(Exception): pass    # Exceptions: Exception*
class UtilStringFormatter: pass               # Utilities: Util*

# ❌ WRONG class naming
class UserProfile(BaseModel): pass            # Missing Model prefix
class EventHandler(Protocol): pass            # Missing Protocol prefix
class CalculatorNode(NodeCompute): pass       # Wrong word order
class Status(Enum): pass                      # Missing Enum prefix
class ValidationError(Exception): pass        # Should be ExceptionValidation
```

## 🚫 Optional Type Usage Standards

### BANNED: Lazy Optional Usage
```python
# ❌ WRONG - No clear business reason for optional
user_name: Optional[str] = None
config_data: Optional[Dict[str, Any]] = None
result: Optional[ModelResult] = None

# ❌ WRONG - Should fail fast instead
def process_data(data: Optional[Dict]) -> Optional[str]:
    if data is None:
        return None  # Lazy handling

# ❌ WRONG - Any type defeats purpose
settings: Optional[Any] = None
```

### ✅ APPROVED: Legitimate Optional Usage
```python
# ✅ GOOD - Truly optional business data
middle_name: str | None = Field(None, description="Optional middle name")
expiration_date: datetime | None = Field(None, description="None = never expires")

# ✅ GOOD - API responses that may legitimately be empty
external_data: ModelApiResponse | None = Field(
    None,
    description="None when external service unavailable"
)

# ✅ GOOD - Configuration with business-justified defaults
cache_ttl_seconds: int | None = Field(
    None,
    description="Cache TTL in seconds. None = cache indefinitely"
)
```

### 🎯 Optional Usage Rules
1. **Business Justification Required**: Every Optional field MUST have Field() with description explaining WHY it's optional
2. **Use Union Syntax**: Prefer `str | None` over `Optional[str]`
3. **No Any Types**: `Optional[Any]` is banned - specify exact types
4. **Fail Fast**: If None represents an error state, raise exception immediately
5. **Document Defaults**: Clearly explain what None means in business terms

## 🏗️ Protocol Centralization Strategy

### Protocol Location Rules
- **✅ omnibase_spi**: Contains ALL protocol definitions for entire ecosystem
- **❌ Other repositories**: Must NOT define protocols, only import from omnibase_spi

### Protocol Organization in omnibase_spi
```python
omnibase_spi/src/omnibase_spi/protocols/
├── core/                          # Core infrastructure protocols
│   ├── protocol_node_base.py
│   ├── protocol_event_bus.py
│   ├── protocol_container.py
│   └── protocol_logger.py
├── workflow/                      # Workflow orchestration protocols
│   ├── protocol_workflow_engine.py
│   ├── protocol_workflow_state.py
│   └── protocol_workflow_step.py
├── services/                      # Service protocols
│   ├── protocol_contract_service.py
│   ├── protocol_discovery_service.py
│   └── protocol_validation_service.py
├── nodes/                        # Node-specific protocols
│   ├── protocol_compute_node.py
│   ├── protocol_effect_node.py
│   ├── protocol_reducer_node.py
│   └── protocol_orchestrator_node.py
└── types/                       # Type system protocols
    ├── protocol_serializable.py
    ├── protocol_validatable.py
    └── protocol_configurable.py
```

### Import Pattern for Other Repositories
```python
# ✅ CORRECT - Import from omnibase_spi
from omnibase_spi.protocols.core import ProtocolEventBus
from omnibase_spi.protocols.nodes import ProtocolComputeNode
from omnibase_spi.protocols.services import ProtocolContractService

# ❌ WRONG - Don't define protocols locally
# from .protocols.local_protocol import LocalProtocol  # BANNED
```

## 🔧 ONEX Four-Node Architecture Compliance

Every node implementation MUST follow this structure:

### Node Directory Structure
```
nodes/node_{DOMAIN}_{NAME}_{TYPE}/
└── v1_0_0/
    ├── node.py                    # Main node implementation
    ├── contracts/                 # Contract definitions
    │   ├── {node}_contract.yaml   # Primary contract
    │   └── subcontracts/          # Subcontract definitions
    │       ├── input.yaml
    │       ├── output.yaml
    │       └── config.yaml
    └── utils/                     # Node-specific utilities ONLY
        ├── {domain}_calculator.py
        └── {domain}_validator.py
```

### Node Type Requirements

#### COMPUTE Nodes (Pure Computation)
```python
# node_pricing_calculator_compute/v1_0_0/node.py
class NodePricingCalculatorCompute(NodeCompute):
    """Pure computation for pricing calculations."""

    # ✅ REQUIRED: Pure functions only
    # ✅ REQUIRED: No external I/O
    # ✅ REQUIRED: Deterministic behavior
    # ✅ REQUIRED: Caching subcontract
```

#### EFFECT Nodes (External Interactions)
```python
# node_database_writer_effect/v1_0_0/node.py
class NodeDatabaseWriterEffect(NodeEffect):
    """External database write operations."""

    # ✅ REQUIRED: External system integration
    # ✅ REQUIRED: I/O operation handling
    # ✅ REQUIRED: Retry and circuit breaker subcontracts
    # ✅ REQUIRED: Transaction management
```

#### REDUCER Nodes (State Management)
```python
# node_workflow_state_reducer/v1_0_0/node.py
class NodeWorkflowStateReducer(NodeReducer):
    """Workflow state transitions and aggregation."""

    # ✅ REQUIRED: State management subcontract
    # ✅ REQUIRED: FSM subcontract (if applicable)
    # ✅ REQUIRED: Aggregation patterns
    # ✅ REQUIRED: Conflict resolution
```

#### ORCHESTRATOR Nodes (Workflow Coordination)
```python
# node_deployment_orchestrator/v1_0_0/node.py
class NodeDeploymentOrchestrator(NodeOrchestrator):
    """Multi-step deployment workflow coordination."""

    # ✅ REQUIRED: Workflow coordination
    # ✅ REQUIRED: Multi-node orchestration
    # ✅ REQUIRED: Event-driven architecture
    # ✅ REQUIRED: Compensation planning
```

## 🎯 Domain Organization Strategy

### Model Domain Categories
Models are organized by business domain, not technical pattern:

```python
models/
├── workflow/                     # Workflow management domain
│   ├── model_workflow_definition.py
│   ├── model_workflow_execution_state.py
│   ├── model_workflow_step.py
│   └── model_workflow_result.py
├── infrastructure/              # Infrastructure management domain
│   ├── model_node_configuration.py
│   ├── model_deployment_config.py
│   ├── model_service_registry.py
│   └── model_health_status.py
├── agent/                      # AI agent domain
│   ├── model_agent_context.py
│   ├── model_agent_response.py
│   ├── model_agent_capability.py
│   └── model_agent_memory.py
└── core/                       # Core system domain
    ├── model_container_config.py
    ├── model_event_envelope.py
    ├── model_error_context.py
    └── model_performance_metrics.py
```

### Enum Domain Categories
```python
enums/
├── workflow/
│   ├── enum_workflow_status.py    # PENDING, RUNNING, COMPLETED, FAILED
│   ├── enum_workflow_type.py      # DEPLOYMENT, MIGRATION, VALIDATION
│   └── enum_step_status.py        # TODO, IN_PROGRESS, DONE, SKIPPED
├── infrastructure/
│   ├── enum_node_type.py          # COMPUTE, EFFECT, REDUCER, ORCHESTRATOR
│   ├── enum_deployment_status.py  # DEPLOYING, DEPLOYED, FAILED, ROLLBACK
│   └── enum_environment_type.py   # DEV, STAGING, PROD
├── agent/
│   ├── enum_agent_type.py         # WORKFLOW, DEBUG, ANALYSIS, COORDINATION
│   ├── enum_agent_status.py       # IDLE, ACTIVE, PROCESSING, ERROR
│   └── enum_capability_type.py    # CODE_ANALYSIS, DOCUMENTATION, TESTING
└── core/
    ├── enum_log_level.py          # DEBUG, INFO, WARNING, ERROR, CRITICAL
    ├── enum_event_type.py         # NODE_CREATED, WORKFLOW_STARTED, ERROR_OCCURRED
    └── enum_validation_result.py  # VALID, INVALID, WARNING, PARTIAL
```

## 📋 Contract and Subcontract Requirements

### Required Contracts by Node Type

#### COMPUTE Node Contracts
```yaml
# contracts/compute_contract.yaml
contract_version:
  major: 1
  minor: 0
  patch: 0

node_type: "COMPUTE"
node_name: "pricing_calculator_compute"

# REQUIRED subcontracts for COMPUTE nodes:
subcontracts:
  - caching_subcontract         # For expensive computations
  - configuration_subcontract   # Runtime configuration management
  - event_type_subcontract      # Event handling patterns

# COMPUTE-specific configuration
algorithm_config:
  parallel_processing: true
  caching_strategy: "LRU"
  computation_timeout: 30
```

#### EFFECT Node Contracts
```yaml
# contracts/effect_contract.yaml
contract_version:
  major: 1
  minor: 0
  patch: 0

node_type: "EFFECT"
node_name: "database_writer_effect"

# REQUIRED subcontracts for EFFECT nodes:
subcontracts:
  - caching_subcontract         # I/O operation caching
  - configuration_subcontract   # External system configuration
  - event_type_subcontract      # External event handling
  - routing_subcontract         # Message routing patterns

# EFFECT-specific configuration
io_operations:
  transaction_support: true
  retry_policy: "exponential_backoff"
  circuit_breaker: true
  connection_pooling: true
```

#### REDUCER Node Contracts
```yaml
# contracts/reducer_contract.yaml
contract_version:
  major: 1
  minor: 0
  patch: 0

node_type: "REDUCER"
node_name: "workflow_state_reducer"

# REQUIRED subcontracts for REDUCER nodes:
subcontracts:
  - aggregation_subcontract       # Data aggregation strategies
  - caching_subcontract          # State caching patterns
  - configuration_subcontract     # Reducer runtime configuration
  - event_type_subcontract       # State change events
  - fsm_subcontract             # Finite state machine (if applicable)
  - state_management_subcontract # State persistence

# REDUCER-specific configuration
reduction_config:
  operation_type: "state_transition"
  conflict_resolution: "last_writer_wins"
  persistence_strategy: "write_through"
```

#### ORCHESTRATOR Node Contracts
```yaml
# contracts/orchestrator_contract.yaml
contract_version:
  major: 1
  minor: 0
  patch: 0

node_type: "ORCHESTRATOR"
node_name: "deployment_orchestrator"

# REQUIRED subcontracts for ORCHESTRATOR nodes:
subcontracts:
  - configuration_subcontract     # Orchestration configuration management
  - event_type_subcontract       # Event coordination
  - routing_subcontract          # Workflow routing
  - state_management_subcontract # Workflow state tracking

# ORCHESTRATOR-specific configuration
workflow_config:
  parallel_execution: true
  compensation_planning: true
  checkpointing: true
  timeout_handling: true
```

## 🔍 Quality Enforcement Framework

This framework provides the baseline quality standards that all repositories inherit from omnibase_core.

### Pre-commit Hook Configuration
```yaml
# .pre-commit-config.yaml (in omnibase_core)
repos:
  # Standard Python quality checks
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/PyCQA/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
        args: [--max-line-length=100]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        args: [--strict, --ignore-missing-imports]

  # OMNI-SPECIFIC QUALITY CHECKS (NEW)
  - repo: local
    hooks:
      - id: validate-structure
        name: Validate Repository Structure
        entry: python tools/validation/validate_structure.py
        language: system
        always_run: true
        pass_filenames: false

      - id: validate-naming
        name: Validate Naming Conventions
        entry: python tools/validation/validate_naming.py
        language: system
        types: [python]

      - id: audit-optional
        name: Audit Optional Type Usage
        entry: python tools/validation/audit_optional.py
        language: system
        types: [python]

      - id: validate-protocols
        name: Validate Protocol Location
        entry: python tools/validation/validate_protocols.py
        language: system
        types: [python]
```

### GitHub Actions CI Workflow
```yaml
# .github/workflows/omni-standards-compliance.yml
name: Omni Standards Compliance

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main, develop ]

jobs:
  omni-standards:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Validate Repository Structure
      run: python tools/validation/validate_structure.py . ${{ github.repository }}

    - name: Validate Naming Conventions
      run: python tools/validation/validate_naming.py .

    - name: Audit Optional Usage
      run: python tools/validation/audit_optional.py .

    - name: Validate Protocol Locations
      run: python tools/validation/validate_protocols.py .

    - name: Generate Compliance Report
      run: python tools/validation/generate_compliance_report.py . > STANDARDS_COMPLIANCE.md

    - name: Upload Compliance Report
      uses: actions/upload-artifact@v3
      with:
        name: compliance-report
        path: STANDARDS_COMPLIANCE.md
```

## 🚀 Migration Strategy

### Phase 1: omnibase_core (Immediate Priority)
**Current Issues**: 1,279+ scattered model files, 92 misplaced protocols, dual directories

**Migration Steps**:
1. Run structure validation: `python tools/validation/validate_structure.py . omnibase_core`
2. Preview migration: `python tools/migration/migrate_repository.py . omnibase_core --dry-run`
3. Execute migration: `python tools/migration/migrate_repository.py . omnibase_core`
4. Validate compliance: `python tools/validation/validate_structure.py . omnibase_core`

**Expected Results**:
- 1,279 model files → Domain-organized in `/models/`
- 153 enum files → Domain-organized in `/enums/`
- 92 protocol files → Migrated to omnibase_spi
- Dual directories eliminated
- 100% naming convention compliance

### Phase 2: omnibase_spi (Protocol Centralization)
**Focus**: Receive migrated protocols from all repositories

**Migration Steps**:
1. Create comprehensive protocol structure
2. Receive protocols from omnibase_core migration
3. Standardize protocol organization by domain
4. Update imports across ecosystem

### Phase 3: Ecosystem Rollout (4-6 weeks)
**Scope**: omniagent, omnibase_infra, omniplan, omnimcp, omnimemory

**Per Repository**:
1. Structure validation and gap analysis
2. Domain-based model/enum organization
3. Protocol import standardization
4. Quality hook inheritance from omnibase_core
5. Compliance validation

## 📊 Success Metrics

### Structure Compliance
- **Directory violations**: 0 forbidden patterns
- **Model organization**: 100% domain-based
- **Protocol centralization**: ≤3 protocols per non-SPI repository
- **Naming conventions**: 100% compliance across all file types

### Type Safety
- **Optional usage**: Business justification required for all optionals
- **Type annotations**: 100% coverage for public APIs
- **Any type usage**: 0 instances (strict typing enforcement)

### Quality Gates
- **Pre-commit hooks**: 100% pass rate
- **CI compliance**: 100% green builds
- **Structure validation**: 0 violations
- **Naming validation**: 0 violations

## 🛠️ Tools and Scripts

The framework includes comprehensive tooling for validation, migration, and enforcement:

- **validate_structure.py**: Repository structure validation
- **validate_naming.py**: Naming convention enforcement
- **audit_optional.py**: Optional type usage auditing
- **migrate_repository.py**: Smart repository migration
- **validate_protocols.py**: Protocol location validation
- **generate_compliance_report.py**: Live compliance monitoring

All tools support both individual repository validation and ecosystem-wide compliance checking.

---

**Framework Status**: ✅ Complete and Ready for Deployment
**Next Action**: Execute Phase 1 migration for omnibase_core
**Expected Timeline**: 2-4 weeks for full ecosystem compliance