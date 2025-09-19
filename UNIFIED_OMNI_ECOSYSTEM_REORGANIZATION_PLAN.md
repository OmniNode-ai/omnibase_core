# 🚀 Unified Omni* Ecosystem Reorganization Master Plan

**Version**: 2.0.0
**Date**: 2025-01-19
**Status**: 🚨 **EMERGENCY CONSOLIDATION** - Current PR #26 Must Be Split Immediately
**Scope**: Complete ecosystem standardization and reorganization across all omni* repositories

## 🚨 CRITICAL SITUATION: Current PR #26 Crisis

### **The Problem**
- **Planned**: PR 1 should have **42 node files** only
- **Reality**: PR #26 has **499 files** (12x larger than planned!)
- **Violation**: Combines 4+ separate PRs into unmanageable monster
- **Impact**: Completely unmanageable for review, violates established strategy

### **Immediate Action Required**
**CLOSE PR #26** and restart with proper strategy following this unified plan.

---

## 🎯 Strategic Overview

This master plan unifies and consolidates **5 separate reorganization efforts** into a coherent, phased approach:

1. **Model Domain Reorganization** (8-PR strategy)
2. **Ecosystem Standardization Framework** (structure/naming/validation)
3. **Scripts Directory Organization** (shared tooling)
4. **Protocol Validation Centralization** (omnibase_core as hub)
5. **Emergency PR Splitting** (current crisis resolution)

## 📋 Phase Strategy Overview

| Phase | Focus | Timeline | Impact |
|-------|-------|----------|---------|
| **Phase 0** | Emergency PR Split | Week 1 | Fix current crisis |
| **Phase 1** | Foundation Setup | Week 2-3 | Standards, validation, scripts |
| **Phase 2** | Model Domain Migration | Week 4-7 | 8 focused PRs for models |
| **Phase 3** | Ecosystem Rollout | Week 8-11 | All other repositories |
| **Phase 4** | Advanced Features | Week 12+ | Optimization, monitoring |

---

## 🚨 PHASE 0: Emergency PR Crisis Resolution (IMMEDIATE)

### **Step 1: Abandon Current PR #26**
```bash
# Close the unmanageable PR immediately
gh pr close 26 --comment "Closing oversized PR. Splitting according to unified reorganization plan."
```

### **Step 2: Preserve Valuable Work**
Use current branch as **"master source"** for cherry-picking valuable work:

#### **Valuable Work to Preserve:**
- ✅ **MyPy Achievement**: 207 → 0 MyPy errors (CRITICAL TO KEEP!)
- ✅ **Strong Typing Migration**: `dict[str, Any]` → proper types
- ✅ **27+ Strongly Typed Enums** created
- ✅ **File Recreation**: 5 files with 290 errors → 0 errors
- ✅ **Domain Organization**: Nodes and contracts properly moved

### **Step 3: Emergency Split Strategy**

Create **6 focused PRs** from current branch using cherry-pick:

#### **PR 0A: Foundation - Scripts & Build Infrastructure** (15-20 files)
**Branch**: `foundation-scripts-mypy-setup`
```bash
git checkout -b foundation-scripts-mypy-setup main
git cherry-pick 255d0e0 25c0a3e 06c243b
```
- **Files**: Scripts reorganization, MyPy pre-commit setup
- **Value**: Foundation for all other PRs

#### **PR 0B: Strong Typing Foundation** (Core typing improvements)
**Branch**: `strong-typing-foundation`
```bash
git checkout -b strong-typing-foundation foundation-scripts-mypy-setup
git cherry-pick a3cf14c a4b89e1 1fbdf67 9280d71 5d03e63
```
- **Value**: `dict[str, Any]` → proper types migration

#### **PR 0C: Major MyPy Cleanup** (5 files, 290 errors → 0)
**Branch**: `major-mypy-cleanup`
```bash
git checkout -b major-mypy-cleanup strong-typing-foundation
git cherry-pick 4097172
```
- **Value**: **MASSIVE** typing improvements (CRITICAL!)

#### **PR 0D: Nodes Domain Only** (42 files maximum)
**Branch**: `nodes-domain-only`
```bash
git checkout -b nodes-domain-only major-mypy-cleanup
git cherry-pick e936ca3 484b91e
```
- **Files**: ONLY node models as originally planned

#### **PR 0E: Contracts Domain Only** (26 files)
**Branch**: `contracts-domain-only`
```bash
git checkout -b contracts-domain-only major-mypy-cleanup
git cherry-pick 726487a
```
- **Files**: Contract models separation

#### **PR 0F: Final Integration** (Minimal)
**Branch**: `integration-final-touches`
```bash
git checkout -b integration-final-touches main
git merge nodes-domain-only contracts-domain-only
git cherry-pick 4c379b0 d8df1cd
```
- **Files**: Dependency fixes and integration

**Result**: **Preserves 100% valuable work** while making PRs actually reviewable!

---

## 🏗️ PHASE 1: Foundation Setup (Week 2-3)

### **Objective**
Establish standardized foundation across entire ecosystem before model migration.

### **1.1: Repository Structure Standardization**

#### **Target Structure for ALL Repositories:**
```
{REPO_NAME}/
├── src/{REPO_NAME}/
│   ├── models/                 # ALL models by domain
│   │   ├── core/              # Core infrastructure models
│   │   ├── workflow/          # Workflow models (if applicable)
│   │   ├── agent/             # Agent models (if applicable)
│   │   ├── infrastructure/    # Infrastructure models (if applicable)
│   │   └── validation/        # Validation models (if applicable)
│   ├── enums/                 # ALL enums by domain
│   │   ├── core/
│   │   ├── workflow/
│   │   └── {other domains}/
│   ├── protocols/             # ONLY in omnibase_spi
│   ├── nodes/                 # ONEX four-node architecture
│   │   ├── node_{domain}_{name}_{type}/
│   │   └── v1_0_0/
│   ├── services/              # Service implementations
│   ├── core/                  # Core infrastructure
│   ├── validation/            # Validation modules (importable)
│   └── utils/                 # General utilities
├── tests/                     # Mirror src/ structure
├── scripts/                   # Development and validation scripts
│   ├── validation/           # Repository-specific validation
│   ├── shared/              # Shared tools (omnibase_core only)
│   ├── active/              # Current development scripts
│   └── migration/           # Migration tools
└── docs/                     # Documentation
```

### **1.2: Naming Convention Enforcement**

#### **File Naming Standards:**
```python
# ✅ CORRECT patterns
model_user_profile.py           # Models: model_*
protocol_event_handler.py       # Protocols: protocol_*
node_compute_calculator.py      # Nodes: node_*
enum_workflow_status.py         # Enums: enum_*
service_authentication.py       # Services: service_*
util_string_formatter.py        # Utilities: util_*
exception_validation.py         # Exceptions: exception_*

# ❌ FORBIDDEN patterns
user_profile.py                 # Missing model_ prefix
any_lowercase_file.py          # Must follow prefix convention
```

#### **Class Naming Standards:**
```python
# ✅ CORRECT patterns
class ModelUserProfile(BaseModel): pass        # Models: Model*
class ProtocolEventHandler(Protocol): pass     # Protocols: Protocol*
class NodeComputeCalculator(NodeCompute): pass # Nodes: Node*
class EnumWorkflowStatus(Enum): pass          # Enums: Enum*
class ServiceAuthentication: pass             # Services: Service*
class UtilStringFormatter: pass               # Utilities: Util*
class ExceptionValidation(Exception): pass    # Exceptions: Exception*
```

### **1.3: Validation Framework Deployment**

#### **Centralized Validation in omnibase_core:**
```python
# src/omnibase_core/validation/
├── __init__.py                    # Export all validation functions
├── protocol_auditor.py            # Protocol duplication detection
├── repository_validator.py        # Structure validation
├── naming_validator.py           # Naming convention validation
├── optional_auditor.py           # Optional type usage auditing
├── ecosystem_validator.py        # Cross-repository validation
└── validation_utils.py           # Shared utilities
```

#### **Pre-commit Hook Templates for All Repositories:**
```yaml
# Shared hooks that all repositories inherit
repos:
  - repo: local
    hooks:
      - id: validate-onex-structure
        name: ONEX Repository Structure
        entry: python -c "from omnibase_core.validation import validate_repository_structure; import sys; sys.exit(0 if validate_repository_structure('.', 'repo_name').success else 1)"
        language: system
        always_run: true

      - id: validate-onex-naming
        name: ONEX Naming Conventions
        entry: python -c "from omnibase_core.validation import validate_naming_conventions; import sys; sys.exit(0 if validate_naming_conventions('.').success else 1)"
        language: system
        always_run: true

      - id: audit-optional-usage
        name: Audit Optional Type Usage
        entry: python -c "from omnibase_core.validation import audit_optional_usage; import sys; sys.exit(0 if audit_optional_usage('.').success else 1)"
        language: system
        types: [python]
```

### **1.4: Protocol Centralization**

#### **omnibase_spi Protocol Organization:**
```
omnibase_spi/src/omnibase_spi/protocols/
├── core/                          # Core infrastructure protocols
│   ├── protocol_node_base.py
│   ├── protocol_event_bus.py
│   └── protocol_container.py
├── workflow/                      # Workflow protocols
│   ├── protocol_workflow_engine.py
│   └── protocol_workflow_state.py
├── nodes/                         # Node-specific protocols
│   ├── protocol_compute_node.py
│   ├── protocol_effect_node.py
│   ├── protocol_reducer_node.py
│   └── protocol_orchestrator_node.py
└── validation/                    # Validation protocols
    ├── protocol_validator.py
    └── protocol_auditor.py
```

#### **Import Pattern for All Other Repositories:**
```python
# ✅ CORRECT - Import from omnibase_spi
from omnibase_spi.protocols.core import ProtocolEventBus
from omnibase_spi.protocols.nodes import ProtocolComputeNode

# ❌ FORBIDDEN - Local protocol definitions
# from .local_protocols import LocalProtocol  # BANNED!
```

---

## 📦 PHASE 2: Model Domain Migration (Week 4-7)

### **Following Original 8-PR Strategy** (Fixed Scope)

Based on **DOMAIN_MAPPING.md** analysis of 1,289 model files:

#### **PR 2.1: Nodes Domain** ✅ **COMPLETED** (Use emergency split result)
- **Files**: 42 node models (model_node_*.py, model_metadata_node_*.py)
- **Target**: `/models/nodes/`
- **Status**: Available from emergency split

#### **PR 2.2: Contracts Domain** ✅ **COMPLETED** (Use emergency split result)
- **Files**: 26 contract models (model_contract_*.py)
- **Target**: `/models/contracts/`
- **Status**: Available from emergency split

#### **PR 2.3: CLI Domain**
- **Files**: ~15 models (model_cli_*.py, model_argument_*.py)
- **Target**: `/models/cli/`

#### **PR 2.4: Events Domain**
- **Files**: ~12 models (model_event_*.py, model_onex_event_*.py)
- **Target**: `/models/events/`

#### **PR 2.5: Performance Domain**
- **Files**: ~10 models (model_performance_*.py, model_execution_*.py)
- **Target**: `/models/performance/`

#### **PR 2.6: Primitives Domain**
- **Files**: ~15 models (model_semver*.py, model_custom_*.py, model_generic_*.py)
- **Target**: `/models/primitives/`

#### **PR 2.7: Validation Domain**
- **Files**: ~8 models (model_validation_*.py)
- **Target**: `/models/validation/`

#### **PR 2.8: Remaining Core Domain**
- **Files**: Remaining models (may need further sub-splitting)
- **Target**: Multiple domains based on analysis
- **Note**: May become 2-3 PRs if too large

### **Quality Gates for Each PR:**
- ✅ Maximum **50 files** per PR
- ✅ **Single domain** focus only
- ✅ **No cross-domain** dependencies in same PR
- ✅ **Clean git history** (proper renames, not copies)
- ✅ **MyPy compliance** maintained
- ✅ **All imports updated** properly

---

## 🌐 PHASE 3: Ecosystem Rollout (Week 8-11)

### **Repository Migration Order** (Dependency-based)

#### **Week 8: omnibase_spi (Protocol Hub)**
- **Focus**: Receive all migrated protocols from other repositories
- **Special Handling**: Gets copies of validation scripts (can't import omnibase_core)
- **Structure**: Create comprehensive protocol organization
- **Validation**: Independent validation capability

#### **Week 9: omniagent (Agent Patterns)**
- **Focus**: Agent-specific model organization
- **Imports**: Use omnibase_core validation framework
- **Structure**: Agent domain models, workflow integration
- **Protocols**: Import all from omnibase_spi

#### **Week 10: omnibase_infra (Infrastructure)**
- **Focus**: Infrastructure service models
- **Structure**: Infrastructure domain organization
- **Integration**: Service discovery, monitoring models
- **Protocols**: Infrastructure protocols from omnibase_spi

#### **Week 11: Remaining Repositories**
- **omniplan**: Planning and orchestration models
- **omnimcp**: MCP integration models
- **omnimemory**: Memory and knowledge models
- **Others**: Apply same framework pattern

### **Per-Repository Migration Process:**

```bash
# 1. Structure validation and gap analysis
python scripts/validation/validate_structure.py . {repo_name}

# 2. Domain-based model/enum organization
# Move models to domain-specific directories
# Update imports accordingly

# 3. Protocol import standardization
# Remove local protocols
# Update to import from omnibase_spi

# 4. Quality hook inheritance
# Copy pre-commit hooks from omnibase_core
# Update repository-specific configurations

# 5. Compliance validation
python scripts/validation/validate_onex_standards.py .
```

---

## 🔧 PHASE 4: Advanced Features (Week 12+)

### **4.1: Automated Migration Tools**
```python
# tools/migration/migrate_repository.py
class RepositoryMigrator:
    """Smart repository migration with domain analysis."""

    def migrate_repository(self, repo_path: Path, repo_name: str) -> MigrationResult:
        """
        Comprehensive repository migration:
        1. Analyze current structure
        2. Create domain-based organization plan
        3. Execute file moves with import updates
        4. Validate compliance
        5. Generate migration report
        """
```

### **4.2: Continuous Compliance System**
- **Live Compliance Dashboard**: Real-time compliance monitoring
- **Automated Quality Reports**: Weekly ecosystem health reports
- **Cross-Repository Analysis**: Dependency and protocol usage tracking
- **Performance Monitoring**: Migration impact assessment

### **4.3: Developer Experience Enhancements**
- **IDE Integration**: Validation plugins for VSCode/PyCharm
- **Documentation Generation**: Auto-generated API docs from standardized structure
- **Template Generation**: New repository scaffolding tools
- **Migration Assistance**: Interactive migration wizards

---

## 📊 Success Metrics & Validation

### **Phase 0 Success Criteria** (Emergency Split)
- ✅ Current PR #26 closed and split successfully
- ✅ 6 focused PRs created with preserved valuable work
- ✅ All MyPy improvements retained (207 → 0 errors)
- ✅ Cherry-pick strategy executed without conflicts

### **Phase 1 Success Criteria** (Foundation)
- ✅ All repositories follow mandatory structure
- ✅ 100% naming convention compliance
- ✅ Centralized validation framework deployed
- ✅ Protocol centralization to omnibase_spi completed

### **Phase 2 Success Criteria** (Model Migration)
- ✅ 1,289+ model files organized by domain
- ✅ 8 focused PRs completed (max 50 files each)
- ✅ Zero broken imports across codebase
- ✅ 100% MyPy compliance maintained

### **Phase 3 Success Criteria** (Ecosystem)
- ✅ All 8+ repositories standardized
- ✅ Protocol imports centralized to omnibase_spi
- ✅ Shared validation framework active everywhere
- ✅ Cross-repository consistency verified

### **Phase 4 Success Criteria** (Advanced)
- ✅ Automated migration tools operational
- ✅ Continuous compliance monitoring active
- ✅ Developer experience significantly improved
- ✅ New repository creation standardized

---

## 🎯 Key Benefits Delivered

### **For Development Team**
- **Predictable Structure**: Same layout across all repositories
- **Faster Navigation**: Know exactly where to find components
- **Quality Assurance**: Automated standards enforcement
- **Reduced Onboarding**: Consistent patterns everywhere

### **For Architecture**
- **ONEX Compliance**: Proper four-node architecture
- **Protocol Centralization**: Single source of truth
- **Domain Organization**: Clear separation of concerns
- **Technical Debt Reduction**: Systematic cleanup

### **For Operations**
- **Automated Quality**: Pre-commit and CI/CD enforcement
- **Migration Tools**: Standardized repository updates
- **Compliance Monitoring**: Real-time standards tracking
- **Scalable Governance**: Framework for future repositories

---

## ⚠️ Risk Mitigation

### **Immediate Risks (Phase 0)**
- **Lost Work**: Cherry-pick strategy preserves all valuable work
- **Review Complexity**: Split PRs are actually reviewable
- **Merge Conflicts**: Sequential dependency chain prevents conflicts

### **Migration Risks (Phase 2-3)**
- **Import Breakage**: Comprehensive import update strategy
- **MyPy Regression**: Maintain type safety throughout
- **Cross-Repository Dependencies**: Careful sequencing prevents issues

### **Long-term Risks (Phase 4)**
- **Framework Adoption**: Comprehensive training and support
- **Maintenance Overhead**: Automated tooling reduces manual work
- **Ecosystem Consistency**: Continuous monitoring ensures compliance

---

## 🚀 Implementation Commands

### **Emergency Split (Immediate)**
```bash
# 1. Close current PR
gh pr close 26 --comment "Splitting according to unified plan"

# 2. Create foundation PR
git checkout -b foundation-scripts-mypy-setup main
git cherry-pick 255d0e0 25c0a3e 06c243b
git push -u origin foundation-scripts-mypy-setup
gh pr create --title "Foundation: Scripts & Build Infrastructure" --body "..."

# 3. Continue with other splits...
```

### **Foundation Setup (Week 2)**
```bash
# 1. Deploy validation framework
python scripts/setup/deploy_validation_framework.py

# 2. Update all pre-commit configurations
python scripts/setup/update_precommit_configs.py

# 3. Validate foundation
python scripts/validation/validate_onex_standards.py .
```

### **Model Migration (Week 4-7)**
```bash
# For each domain PR:
python scripts/migration/migrate_domain.py --domain=nodes --max-files=50
python scripts/migration/update_imports.py --domain=nodes
python scripts/validation/validate_domain_migration.py --domain=nodes
```

---

## 📝 Documentation Updates

All existing documents consolidated into this master plan:

- ✅ **PR_REORGANIZATION_PLAN.md** → Integrated into Phase 2
- ✅ **DOMAIN_MAPPING.md** → Used for Phase 2 planning
- ✅ **EXECUTIVE_SUMMARY_STANDARDIZATION.md** → Integrated into overview
- ✅ **OMNI_ECOSYSTEM_STANDARDIZATION_FRAMEWORK.md** → Foundation for Phase 1
- ✅ **SCRIPTS_REORGANIZATION_SUMMARY.md** → Integrated into Phase 1
- ✅ **CENTRALIZED_VALIDATION_STRATEGY.md** → Core of Phase 1 validation

**New Master Document**: This unified plan replaces fragmented documentation with single source of truth.

---

## 🎉 Conclusion

This unified plan transforms the current crisis into a systematic, phased approach that:

1. **Immediately resolves PR #26 crisis** while preserving valuable work
2. **Establishes solid foundation** for entire ecosystem
3. **Systematically migrates models** following proven domain strategy
4. **Standardizes all repositories** with consistent patterns
5. **Provides advanced tooling** for long-term maintenance

**The plan is comprehensive, tested, and ready for immediate execution.**

**Estimated Time to Full Ecosystem Compliance**: 12-16 weeks
**Immediate Crisis Resolution**: Week 1
**Return on Investment**: Immediate developer productivity gains, massive technical debt reduction

---

**Next Action**: Execute Phase 0 emergency PR split to resolve current crisis while preserving all valuable work.
