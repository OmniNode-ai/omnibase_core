# Protocol Migration Plan - Complete SPI Strategy

## 🎯 Vision: Zero Local Protocols

### **Strategic Goal**
Move ALL protocols to `omnibase_spi` to enable:
- ✅ **Pure interface architecture** - Complete separation of contracts and implementation
- ✅ **Third-party builders** - Anyone can implement our architecture without our code
- ✅ **Reference implementations** - Our services become examples, not requirements
- ✅ **Clean dependency management** - Clear interface boundaries

## 🚨 Migration Rules

### **RULE 1: NO protocols in service repositories**
```bash
# Target state for all repositories
find src/ -name "protocol_*.py" -o -name "*protocol*.py"
# Should return: NO RESULTS
```

### **RULE 2: ALL protocols migrate to omnibase_spi**
```text
../omnibase_spi/src/omnibase_spi/protocols/
├── core/                    # ONEX architecture protocols
├── agent/                   # Agent coordination protocols
├── workflow/                # Workflow management protocols
├── integration/             # Service integration protocols
├── monitoring/              # Observability protocols
└── file_handling/           # File system protocols
```

### **RULE 3: Services become pure implementers**
```python
# In any service repository
from omnibase_spi.protocols.agent import ProtocolAgentLifecycle
from omnibase_spi.protocols.workflow import ProtocolSmartResponder

class AgentService(ProtocolAgentLifecycle):
    """Pure implementation of agent lifecycle protocol."""

    def execute(self, request: AgentRequest) -> AgentResponse:
        # Implementation only - no protocol definition
        pass
```

## 📋 Repository Migration Checklist

### **Step 1: Audit Current Protocols**
```bash
# Run this in each repository
python scripts/validation/audit_protocols.py .

# Expected output:
# Found 3 protocols to migrate:
#   - src/repo/protocols/protocol_custom.py → omnibase_spi/protocols/workflow/
#   - src/repo/core/protocol_service.py → omnibase_spi/protocols/core/
```

### **Step 2: Plan Migration Destination**
For each protocol, determine omnibase_spi location:

| Protocol Type | Destination Directory | Examples |
|---------------|----------------------|----------|
| ONEX Architecture | `protocols/core/` | ProtocolReducer, ProtocolOrchestrator |
| Agent Coordination | `protocols/agent/` | ProtocolAgentLifecycle, ProtocolAgentRegistry |
| Workflow Management | `protocols/workflow/` | ProtocolWorkflowEngine, ProtocolTaskManager |
| Service Integration | `protocols/integration/` | ProtocolServiceBus, ProtocolHealthCheck |
| Data Processing | `protocols/data/` | ProtocolDataTransform, ProtocolValidation |
| File Operations | `protocols/file_handling/` | ProtocolFileReader, ProtocolFileProcessor |
| Monitoring | `protocols/monitoring/` | ProtocolMetrics, ProtocolTracing |

### **Step 3: Execute Migration**
```bash
# Use migration script
python scripts/migration/migrate_protocols.py \
  --source-repo . \
  --target-repo ../omnibase_spi \
  --dry-run

# Review migration plan, then execute:
python scripts/migration/migrate_protocols.py \
  --source-repo . \
  --target-repo ../omnibase_spi \
  --execute
```

### **Step 4: Update Imports**
```bash
# Automatic import updates
python scripts/migration/update_imports.py \
  --repository . \
  --protocol-map protocols_migration_map.json
```

### **Step 5: Validate Zero Protocols**
```bash
# Final validation
python scripts/validation/validate_zero_protocols.py .

# Expected output:
# ✅ Repository validation PASSED
# ✅ Zero local protocols found
# ✅ All imports from omnibase_spi
# ✅ Clean implementation-only repository
```

## 🛠️ Migration Tooling

### **audit_protocols.py**
Scans repository for existing protocols and recommends migration destinations.

### **migrate_protocols.py**
Safely moves protocols from service repository to omnibase_spi with proper organization.

### **update_imports.py**
Updates all import statements to reference omnibase_spi locations.

### **validate_zero_protocols.py**
Validates that repository contains zero protocols and only imports from omnibase_spi.

## 📊 Validation Scripts for Pre-commit

### **validate_no_local_protocols.py**
```python
"""
Pre-commit hook: Ensures no local protocols exist.

Fails if any Protocol* classes are defined locally.
Passes only if all protocols are imported from omnibase_spi.
"""
```

### **validate_protocol_imports.py**
```python
"""
Pre-commit hook: Validates protocol import patterns.

Ensures all protocol imports come from omnibase_spi.
Fails if protocols are imported from other sources.
"""
```

## 🎯 Implementation Strategy

### **Phase 1: Create Migration Tooling (Week 1)**
1. Build audit and migration scripts
2. Test on one repository (omniagent)
3. Refine tooling based on learnings

### **Phase 2: Repository-by-Repository Migration (Week 2-3)**
1. **omniagent** - Agent-specific protocols
2. **omnibase_core** - Core architecture protocols
3. **omnibase_infra** - Infrastructure protocols
4. **Additional repositories** - As needed

### **Phase 3: Validation and Enforcement (Week 4)**
1. Add pre-commit hooks to all repositories
2. Validate zero local protocols across ecosystem
3. Document pure SPI architecture

## 🔄 Ongoing Governance

### **New Protocol Development**
```bash
# Always create in omnibase_spi first
cd ../omnibase_spi
# Create protocol in appropriate directory
# Test in service repository via import
# Never create protocols locally
```

### **Protocol Evolution**
```bash
# Update protocol in omnibase_spi
# Version compatibility maintained
# Service repositories get updates via dependency management
```

## 📈 Benefits

### **For Builders**
- ✅ **Complete interface specification** in one place
- ✅ **No implementation dependencies** required
- ✅ **Custom implementation freedom**
- ✅ **Clear architecture boundaries**

### **For ONEX Ecosystem**
- ✅ **Consistent interfaces** across all services
- ✅ **Centralized protocol evolution**
- ✅ **Reduced duplication** and maintenance
- ✅ **Clear separation of concerns**

### **For Service Development**
- ✅ **Implementation focus** only
- ✅ **Clear protocol contracts**
- ✅ **Simplified testing** via protocol mocks
- ✅ **Reduced repository complexity**

---

**Target State**: Every omni* repository becomes a pure implementation of omnibase_spi protocols, enabling complete architectural flexibility for builders while maintaining consistency across the ecosystem.
