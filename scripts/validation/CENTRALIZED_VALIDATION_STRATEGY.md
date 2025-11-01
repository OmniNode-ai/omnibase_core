# Centralized Protocol Validation Strategy

## 🎯 Architecture: omnibase_core as Validation Hub

### **Core Principle**
Since omnibase_core is a dependency for all repositories except omnibase_spi, we centralize all protocol validation logic here and other repositories import it.

## 📦 Repository Roles

### **omnibase_core (Validation Hub)**
```text
src/omnibase_core/validation/
├── __init__.py                          # Export validation functions
├── protocol_auditor.py                  # Core audit logic (importable)
├── protocol_migrator.py                 # Migration logic (importable)
├── validation_utils.py                  # Shared utilities
└── repository_scanner.py                # Multi-repo scanning logic
```

### **Other Service Repositories (Importers)**
```bash
# In their pre-commit-config.yaml or validation scripts
from omnibase_core.validation import audit_protocols, migrate_protocols

# Simple usage:
audit_protocols(repository_path=".", spi_path="../omnibase_spi")
```

### **omnibase_spi (Special Case)**
```bash
# Gets a COPY of validation scripts (can't import omnibase_core)
scripts/validation/
├── audit_protocol_duplicates.py        # Copied from omnibase_core
├── migrate_protocols_safe.py           # Copied from omnibase_core
└── spi_specific_validation.py          # SPI-only validation
```

## 🔧 Implementation Strategy

### **1. Refactor Scripts to Importable Modules**

Transform standalone scripts into importable modules:

```python
# src/omnibase_core/validation/protocol_auditor.py
class ProtocolAuditor:
    """Centralized protocol auditing for omni* ecosystem."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path.cwd()

    def audit_current_repository(self) -> AuditResult:
        """Audit protocols in current repository only."""
        pass

    def audit_ecosystem(self, omni_root: Path) -> AuditResult:
        """Audit protocols across all omni* repositories."""
        pass

    def check_against_spi(self, spi_path: Path) -> DuplicationReport:
        """Check current repo protocols against SPI for duplicates."""
        pass

# Easy import in other repositories:
from omnibase_core.validation import ProtocolAuditor
auditor = ProtocolAuditor()
result = auditor.check_against_spi("../omnibase_spi")
```

### **2. Repository-Specific Pre-commit Hooks**

Each repository gets simple hooks that import from omnibase_core:

```yaml
# In omniagent/.pre-commit-config.yaml
- id: validate-no-protocol-duplicates
  name: Protocol Duplication Check
  entry: python -c "
from omnibase_core.validation import audit_protocols;
import sys;
result = audit_protocols('.');
sys.exit(0 if result.success else 1)
"
  language: system
  always_run: true
  stages: [commit]
```

### **3. Validation Modes**

Support different validation scopes:

```python
# Mode 1: Current repository only (fast)
auditor.audit_current_repository()

# Mode 2: Current repository vs SPI (medium)
auditor.check_against_spi("../omnibase_spi")

# Mode 3: Full ecosystem scan (comprehensive, slower)
auditor.audit_ecosystem("/path/to/omni/repos")
```

## 📋 Benefits

### **For omnibase_core**
- ✅ **Single source of truth** for all validation logic
- ✅ **Consistent updates** propagate to all repositories
- ✅ **Comprehensive testing** in one place
- ✅ **Version-controlled validation rules**

### **For Service Repositories**
- ✅ **Simple imports** instead of copying scripts
- ✅ **Always up-to-date** validation logic
- ✅ **Minimal maintenance** overhead
- ✅ **Consistent behavior** across ecosystem

### **For omnibase_spi**
- ✅ **Independence** with copied scripts
- ✅ **SPI-specific validation** capabilities
- ✅ **No circular dependencies**
- ✅ **Self-contained validation**

## 🚀 Migration Plan

### **Phase 1: Refactor to Modules (This Week)**
1. Convert existing scripts to importable classes
2. Create `src/omnibase_core/validation/` module
3. Maintain backward compatibility with CLI scripts
4. Test with omnibase_core first

### **Phase 2: Repository Integration (Next Week)**
1. Update other repositories to import from omnibase_core
2. Copy scripts to omnibase_spi (special case)
3. Update all pre-commit configurations
4. Test across ecosystem

### **Phase 3: Advanced Features (Following Week)**
1. Add repository-specific validation rules
2. Create validation dashboards/reports
3. Implement automated fixing capabilities
4. Add CI/CD integration

## 📊 Usage Examples

### **Simple Repository Check**
```python
# In any omni* repository (except SPI)
from omnibase_core.validation import ProtocolAuditor

auditor = ProtocolAuditor()
if not auditor.check_protocols_clean():
    print("❌ Protocol violations found!")
    auditor.print_violations()
    exit(1)
```

### **Pre-Migration Audit**
```python
# Before migrating protocols to SPI
from omnibase_core.validation import ProtocolMigrator

migrator = ProtocolMigrator(source=".", target="../omnibase_spi")
plan = migrator.create_migration_plan()
if plan.has_conflicts():
    print("⚠️ Migration conflicts detected")
    plan.print_conflicts()
```

### **Ecosystem Health Check**
```python
# For comprehensive ecosystem analysis
from omnibase_core.validation import EcosystemAuditor

auditor = EcosystemAuditor("/path/to/omni/repos")
health = auditor.check_ecosystem_health()
health.generate_report("protocol_health_report.json")
```

## 🎯 Decision Points

### **Repository Scope Options:**

**Option A: Repository-Only Validation (Recommended)**
- Each repository validates only its own protocols
- Checks against SPI for duplicates
- Fast, focused validation
- Simple to implement and maintain

**Option B: Ecosystem-Wide Validation**
- Full cross-repository duplicate detection
- Comprehensive conflict analysis
- Slower but more thorough
- Better for migration planning

**Recommendation**: Start with Option A, add Option B as an advanced feature.

### **SPI Handling Options:**

**Option A: Copy Scripts to SPI (Recommended)**
- SPI gets static copies of validation scripts
- Independent validation capability
- No dependency on omnibase_core
- Manual sync required for updates

**Option B: SPI-Specific Validation Only**
- SPI has minimal, specialized validation
- Relies on other repositories for full validation
- Simpler but less comprehensive

**Recommendation**: Option A for complete SPI independence.

---

**Result**: Centralized validation in omnibase_core with ecosystem-wide consistency and SPI independence.
