# Model Domain Organization Mapping

## Domain Classification for 1,289 Model Files

### Primary Domains (8 core domains)

#### 1. **core/** - Fundamental Models
Core infrastructure models that everything else depends on
- Core actions, events, nodes, contracts
- Base types, metadata, schemas
- Fundamental ONEX components

**Subdirectories**:
- core/ (already exists - base models)

#### 2. **ai/** - AI and Machine Learning
All AI/ML related models and workflows
- ai/, ai_workflows/, llm/, embedding/
- intelligence/, omnimemory/, semantic/
- knowledge_graph/, knowledge_pipeline/

#### 3. **infrastructure/** - Infrastructure Services
Infrastructure components and service management
- infrastructure/, monitoring/, health/, metrics/
- service/, discovery/, registry/, consul/
- observability/, resource/, canary/

#### 4. **workflow/** - Workflow and Execution
Workflow orchestration, execution, and state management
- workflow/, workflow_testing/, execution/
- automation/, autonomous/, task/, task_queue/
- progress/, timeline/, snapshots/

#### 5. **agent/** - Agent Models
Agent capabilities, coordination, and metadata
- agent/, capabilities/, coordination/
- instance/, runtime/, sandbox/

#### 6. **security/** - Security and Authentication
Security models, policies, and authentication
- security/, policy/, validation/ (security aspects)

#### 7. **communication/** - Messaging and Events
Communication protocols and event handling
- communication/, events/, hook_events/, mcp/
- protocol/, endpoints/, gateway/, proxy/

#### 8. **validation/** - Testing and Quality Assurance
Validation, testing, and quality models
- validation/, precommit/, debug/, detection/
- conflicts/, refactor/, optimization/

### Secondary Classifications

#### **common/** - Shared Utilities
Cross-cutting concerns and shared models
- common/, types/, schema/, config/, configuration/
- memory/, metadata/, capture/, tool_capture/

### Migration Strategy

1. **Phase 1**: Migrate core domain (foundation models)
2. **Phase 2**: Migrate ai domain (complex dependencies)
3. **Phase 3**: Migrate infrastructure domain (service models)
4. **Phase 4**: Migrate workflow domain (execution models)
5. **Phase 5**: Migrate agent domain (agent models)
6. **Phase 6**: Migrate security domain (security models)
7. **Phase 7**: Migrate communication domain (event models)
8. **Phase 8**: Migrate validation domain (testing models)
9. **Phase 9**: Migrate common utilities (shared models)

### Critical Requirements

1. **Naming Convention**: All models MUST start with "model_" prefix
2. **Typing Enforcement**: Replace ALL string versions with ModelSemVer instances
3. **Import Updates**: Update all import statements to new domain structure
4. **Dependency Order**: Migrate in dependency order (core first)

### File Count by Domain (Estimated)

- core/: ~200 files (fundamental models)
- ai/: ~180 files (AI/ML models)
- infrastructure/: ~150 files (service models)
- workflow/: ~140 files (execution models)
- agent/: ~120 files (agent models)
- security/: ~100 files (security models)
- communication/: ~120 files (event models)
- validation/: ~110 files (testing models)
- common/: ~169 files (shared utilities)

**Total**: 1,289 files across 9 primary domains
