# v0.4.0 Release Gate Checklist (Hardened)

> **Version**: 0.4.0
> **Status**: Pre-release
> **Last Updated**: 2025-12-14
> **Linear Ticket**: [OMN-218](https://linear.app/omninode/issue/OMN-218)

This checklist defines **hard release gates** for v0.4.0.
All items are mandatory unless explicitly marked as informational.
All checks require **verifiable evidence**. No exceptions, no vibes.

---

## Evidence Storage Guidelines

### Primary Storage Location

All release evidence MUST be stored in the **release tracking issue** on Linear:
- Issue: [OMN-218](https://linear.app/omninode/issue/OMN-218) (or the corresponding release issue)
- Create a comment thread per section (e.g., "Section 1: Code Quality Evidence")
- Link to artifacts rather than embedding large outputs inline

### Evidence Types and Storage

| Evidence Type | Where to Store | Format |
|---------------|----------------|--------|
| **CI run links** | Release issue comment | Direct URL to GitHub Actions run |
| **Command output** (<50 lines) | Release issue comment | Code block with timestamp |
| **Command output** (>50 lines) | GitHub Gist | Link in release issue |
| **Screenshots** | Release issue attachment | PNG with descriptive filename |
| **Coverage reports** | CI artifacts + link | HTML report or term output |
| **Test logs** | CI artifacts | Link to specific job/step |
| **Contract fingerprint reports** | `artifacts/release/v0.4.0/` | JSON or text file |
| **Replay logs** | `artifacts/release/v0.4.0/` | Timestamped log files |
### ⚠️ PII and Secrets Redaction

**CRITICAL**: Before storing ANY evidence, you MUST redact sensitive information:

| ⚠️ REDACT THIS | Example | Replacement |
|---------------|---------|-------------|
| **API keys, tokens, passwords** | `Authorization: Bearer sk_live_abc123` | `Authorization: Bearer [REDACTED]` |
| **Internal hostnames/IPs** | `db.internal.omninode.ai:5432` | `db.[REDACTED]:5432` |
| **Personal identifiable information** | `user_email: john@example.com` | `user_email: [REDACTED]` |
| **Environment-specific secrets** | `DATABASE_URL=postgresql://...` | `DATABASE_URL=[REDACTED]` |
| **AWS/GCP credentials** | `AWS_SECRET_ACCESS_KEY=wJalr...` | `AWS_SECRET_ACCESS_KEY=[REDACTED]` |
| **Session tokens** | `session_id: 1a2b3c4d5e` | `session_id: [REDACTED]` |

**Redaction Patterns**:
- Use `[REDACTED]` for complete removal
- Use `***` for partial masking (e.g., `sk_***abc` for API keys)
- Use `user_<N>` for anonymized user references (e.g., `user_1`, `user_2`)

**Tools**:
- Manual: Search for patterns like `key`, `token`, `password`, `secret`, `@example.com`
- Automated: Use `sed` or text replacement before storing: `sed 's/Bearer [a-zA-Z0-9_-]*/Bearer [REDACTED]/g'`

**Remember**: Once evidence is posted to Linear or GitHub, it's permanent. Redact BEFORE posting.

---


### Directory Structure for Artifacts

```text
artifacts/
  release/
    v0.4.0/
      fingerprints/          # Contract fingerprint verification
      coverage/              # Coverage HTML reports
      replay-logs/           # Determinism replay outputs
      fuzz-reports/          # Adapter fuzz test results
      evidence-index.md      # Index of all evidence with links
```

### Naming Conventions

- **Files**: `{section}-{gate}-{timestamp}.{ext}`
  - Example: `01-code-quality-ast-check-20251214.txt`
- **Gists**: `v0.4.0-{section}-{gate}-evidence`
  - Example: `v0.4.0-testing-coverage-evidence`
- **Screenshots**: `{section}-{description}-{timestamp}.png`
  - Example: `02-testing-ci-splits-pass-20251214.png`

### Evidence Requirements

Each gate requires:
1. **Timestamp**: When the verification was performed
2. **Command/Action**: Exact command run or action taken
3. **Output**: Result (success/failure with details)
4. **Commit SHA**: Git commit at time of verification
5. **Verifier**: Who performed the check

### Example Evidence Reference

```markdown
### Gate: Strict type safety enforced
- **Timestamp**: 2025-12-14 14:30 UTC
- **Commit**: abc1234
- **Command**: `poetry run mypy src/omnibase_core/ --strict`
- **Result**: PASS (0 errors)
- **CI Link**: https://github.com/OmniNode-ai/omnibase_core/actions/runs/12345
- **Verifier**: @username
```

### Retention Policy

- **Release artifacts**: Retained permanently in `artifacts/release/`
- **CI logs**: Retained per GitHub Actions policy (90 days default)
- **Linear comments**: Permanent (part of issue history)
- **Gists**: Permanent unless manually deleted

### Toolchain Version Requirements

All evidence must include toolchain version information for reproducibility:

**Required Information**:
- **Python version**: `python --version` (e.g., Python 3.12.5)
- **Poetry version**: `poetry --version` (e.g., Poetry version 1.8.0)
- **OS/Platform**: For platform-specific tests (e.g., Linux 5.15.0, macOS 14.0, Windows 11)

**Example Evidence with Toolchain Versions**:

```markdown
### Gate: Strict type safety enforced
- **Timestamp**: 2025-12-14 14:30 UTC
- **Commit**: abc1234
- **Python**: 3.12.5
- **Poetry**: 1.8.0
- **Platform**: Linux 5.15.0-x86_64
- **Command**: `poetry run mypy src/omnibase_core/ --strict`
- **Result**: PASS (0 errors)
- **CI Link**: https://github.com/OmniNode-ai/omnibase_core/actions/runs/12345
- **Verifier**: @username
```

**Rationale**: Toolchain versions ensure evidence is reproducible and helps diagnose platform-specific issues.

### Pre-Release Evidence Checklist

Before marking a gate complete:
1. Evidence is stored in the correct location
2. Evidence includes all required fields (timestamp, commit, result, **toolchain versions**)
3. Links are accessible and not broken
4. Large outputs are in Gists or artifacts (not inline)
5. Evidence index is updated (`artifacts/release/v0.4.0/evidence-index.md`)

---

## 1. Code Quality

- [ ] **All nodes pure-checked (AST)**
  - Run AST validation checks on all node implementations
  - **Note**: No dedicated `ast_checker` CLI exists. Use existing validation framework:
  - Commands:
    ```bash
    # Run architecture validation (one-model-per-file, Pydantic patterns)
    poetry run pytest tests/unit/validation/ -v -k "ast or architecture or pattern"

    # Run naming convention and pattern checks
    poetry run python -c "
    from omnibase_core.validation.patterns import validate_directory
    from pathlib import Path
    results = validate_directory(Path('src/omnibase_core/nodes'))
    print(f'Validation complete: {len(results)} issues found')
    for r in results[:10]: print(f'  - {r}')
    "

    # Check for purity violation patterns in node implementations
    poetry run python -c "
    from pathlib import Path
    import ast

    violations = []
    for f in Path('src/omnibase_core/nodes').glob('*.py'):
        tree = ast.parse(f.read_text())
        # Check for global state access, I/O in compute nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                violations.append(f'{f.name}: global statement')
    print(f'Purity check: {len(violations)} potential violations')
    for v in violations: print(f'  - {v}')
    "
    ```
  - Expected: 0 violations in node implementations
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/01-code-quality-ast-check-YYYYMMDD.txt
  - **Future**: Consider creating `omnibase_core.tools.ast_checker` CLI (tracked in MVP_PLAN.md)

- [ ] **Strict type safety enforced**
  - Command: `poetry run mypy src/omnibase_core/ --strict`
  - Expected: 0 errors
  - Evidence: Release issue comment (OMN-218) with CI run link or artifacts/release/v0.4.0/01-code-quality-mypy-YYYYMMDD.txt

- [ ] **Pre-commit hooks pass**
  - Command: `pre-commit run --all-files`
  - Hooks: black, isort, ruff, mypy
  - Evidence: Release issue comment (OMN-218) with CI run link or screenshot attachment

---

## 2. Testing

- [ ] **CI passes all parallel test splits**
  - All splits succeed
  - No test flake retries allowed (pytest-rerunfailures disabled)
  - **Note**: Flaky tests must be fixed, not retried
  - Expected runtime: 2m30s-3m30s per split
  - Evidence: Release issue comment (OMN-218) with GitHub Actions run link

- [ ] **Adapter fuzz testing completed**
  - All adapters fuzzed with randomized inputs using Hypothesis
  - No crashes or undefined behavior
  - **Tool**: Hypothesis `^6.148` (installed in pyproject.toml)
  - **Status**: Adapter fuzz tests planned in MVP_PLAN.md Issue 3.8, minimal tests exist currently
  - Commands:
    ```bash
    # Run existing property-based tests
    poetry run pytest tests/unit/enums/test_enum_node_kind.py::TestEnumNodeKindPropertyBased -v

    # Run all Hypothesis-based tests (search for @given decorator usage)
    poetry run pytest tests/ -v -k "property" --hypothesis-show-statistics

    # Create adapter fuzz test evidence (example structure)
    poetry run python -c "
    from hypothesis import given, strategies as st, settings
    from omnibase_core.models.contracts.model_runtime_host_contract import ModelRuntimeHostContract
    import json

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=50)
    def test_contract_handles_invalid_input(invalid_data):
        try:
            # Attempt to parse malformed data
            ModelRuntimeHostContract.model_validate_json(json.dumps({'invalid': invalid_data}))
        except Exception as e:
            # Should raise ValidationError, not crash
            assert 'validation' in str(type(e).__name__).lower() or 'error' in str(type(e).__name__).lower()

    print('Fuzz test structure verified - implement in tests/unit/adapters/test_adapter_fuzz.py')
    "
    ```
  - Expected: All adapters handle malformed inputs gracefully (ValidationError, not crash)
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/fuzz-reports/adapter-fuzz-YYYYMMDD.txt
  - **Gap**: Full adapter fuzz tests need implementation per MVP_PLAN.md Issue 3.8

- [ ] **Coverage threshold met**
  - Minimum: 60% line coverage
  - Enforcement: Coverage is enforced in CI via pytest-cov fail-under
  - Command: `poetry run pytest tests/ --cov=src/omnibase_core --cov-fail-under=60 --cov-report=term-missing`
  - Evidence: Release issue comment (OMN-218) with CI artifacts link or artifacts/release/v0.4.0/coverage/index.html

- [ ] **Negative-path tests present**
  - At least one failure-mode test per contract class
  - Explicit assertions on error shape
  - Evidence: Release issue comment (OMN-218) with specific test file paths (e.g., tests/unit/test_negative_paths.py)

---

## 3. Determinism & Replayability

- [ ] **Deterministic execution verified**
  - Identical inputs produce identical outputs
  - Hash comparison of emitted ModelActions or events
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/replay-logs/determinism-hashes-YYYYMMDD.txt

- [ ] **Replay validation completed**
  - At least one representative workflow replayed end-to-end
  - Replay output matches original execution exactly
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/replay-logs/replay-comparison-YYYYMMDD.txt

---

## 4. Contracts & Architecture

- [ ] **All contracts have valid fingerprints**
  - Every RuntimeHostContract YAML includes a fingerprint
  - Fingerprints verified against contract content
  - **Note**: Use existing scripts (no `omnibase_core.tools.verify_fingerprints` CLI)
  - Commands:
    ```bash
    # Validate all runtime contract fingerprints match content
    poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/ --validate --recursive

    # Validate example contract fingerprints
    poetry run python scripts/compute_contract_fingerprint.py examples/contracts/ --validate --recursive

    # Check if any fingerprints need regeneration (dry-run)
    poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive --dry-run

    # Lint all contracts (includes fingerprint validation)
    poetry run python scripts/lint_contract.py contracts/runtime/ --recursive --verbose
    ```
  - Expected: All fingerprints valid (exit code 0), no regeneration needed
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/fingerprints/fingerprint-verification-YYYYMMDD.txt

- [ ] **Fingerprint enforcement validated**
  - Modified contract fails verification
  - No fallback or silent acceptance
  - Commands:
    ```bash
    # Test that modified contract fails validation
    poetry run python -c "
    from pathlib import Path
    from omnibase_core.contracts.hash_registry import compute_contract_fingerprint, detect_drift
    import yaml
    import tempfile

    # Load a real contract
    contract_path = Path('contracts/runtime/runtime_orchestrator.yaml')
    original = yaml.safe_load(contract_path.read_text())
    original_fp = original.get('fingerprint', '')

    # Modify content and verify drift detection
    original['description'] = 'MODIFIED FOR TEST'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(original, f)
        temp_path = Path(f.name)

    # Verify fingerprint validation fails
    from omnibase_core.models.contracts.model_runtime_host_contract import ModelRuntimeHostContract
    modified = ModelRuntimeHostContract.model_validate(original)
    new_fp = compute_contract_fingerprint(modified)
    print(f'Original fingerprint: {original_fp}')
    print(f'After modification:   {new_fp}')
    print(f'Drift detected: {original_fp != new_fp}')
    assert original_fp != new_fp, 'Fingerprint should change when contract modified'
    print('✅ Fingerprint enforcement working correctly')
    temp_path.unlink()
    "
    ```
  - Expected: Modification causes fingerprint mismatch (drift detected)
  - Evidence: Release issue comment (OMN-218) with test output showing fingerprint validation failure

- [ ] **All nodes are contract-driven**
  - No legacy node implementations remain
  - Command: `grep -rE "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/`
  - Alternative (ripgrep): `rg "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/`
  - Expected: Empty output
  - Evidence: Release issue comment (OMN-218) with command output

---

## 5. Registry & Discovery Integrity

- [ ] **Registry loads all contracts**
  - No orphaned or unreachable contracts
  - Commands:
    ```bash
    # Load all runtime contracts via FileRegistry
    poetry run python -c "
    from pathlib import Path
    from omnibase_core.runtime.file_registry import FileRegistry

    registry = FileRegistry()
    contracts_dir = Path('contracts/runtime')
    contracts = registry.load_all(contracts_dir)

    print(f'✅ Successfully loaded {len(contracts)} runtime contracts:')
    for contract in contracts:
        print(f'  - Event Bus Kind: {contract.event_bus.kind}')
        print(f'    Handlers: {len(contract.handlers)}')
        print(f'    Nodes: {len(contract.nodes)}')
    "

    # Load example contracts
    poetry run python -c "
    from pathlib import Path
    from omnibase_core.runtime.file_registry import FileRegistry

    registry = FileRegistry()
    for subdir in ['effect', 'compute', 'reducer', 'orchestrator']:
        dir_path = Path(f'examples/contracts/{subdir}')
        if dir_path.exists():
            contracts = registry.load_all(dir_path)
            print(f'✅ Loaded {len(contracts)} {subdir} example contracts')
    "

    # Run FileRegistry unit tests (37+ tests)
    poetry run pytest tests/unit/runtime/test_file_registry.py -v --tb=short
    ```
  - Expected: All contracts load without errors, all FileRegistry tests pass
  - Evidence: Release issue comment (OMN-218) with command output or test results

- [ ] **Contract-to-node resolution verified**
  - Every fingerprint resolves to a runnable node
  - Commands:
    ```bash
    # Run runtime contract tests (40+ tests covering node type, metadata, structure)
    poetry run pytest tests/unit/contracts/test_runtime_contracts.py -v --tb=short

    # Run service registry and resolution tests
    poetry run pytest tests/unit/container/test_service_registry.py tests/unit/container/test_container_service_resolver.py -v --tb=short

    # Verify contract-to-node type mapping
    poetry run python -c "
    from pathlib import Path
    from omnibase_core.runtime.file_registry import FileRegistry

    registry = FileRegistry()
    contracts = registry.load_all(Path('contracts/runtime'))

    print('Contract-to-Node Resolution Verification:')
    for contract in contracts:
        for node in contract.nodes:
            print(f'  ✅ {node.node_type} -> {node.implementation_class or \"(inline)\"}')
    print(f'\\n✅ All {sum(len(c.nodes) for c in contracts)} nodes resolve correctly')
    "

    # Run discovery tests
    poetry run pytest tests/unit/discovery/test_mixin_discovery.py -v --tb=short
    ```
  - Expected: All resolution tests pass, every node type maps to implementation
  - Evidence: Release issue comment (OMN-218) with test output showing resolution success

---

## 6. Versioning & Upgrade Safety

- [ ] **Semantic versioning enforced**
  - Version bump aligns with documented breaking changes
  - Evidence: CHANGELOG and tag comparison

- [ ] **Upgrade behavior verified**
  - v0.3.x -> v0.4.0 upgrade path documented and tested
  - Evidence: Migration test or documented failure mode

- [ ] **Downgrade behavior declared**
  - Either:
    - Downgrade tested and supported
    - Downgrade explicitly unsupported and fails fast
  - Evidence: Documentation or test

---

## 7. Dependency & Build Reproducibility

- [ ] **Dependency lock verified**
  - poetry.lock committed and intentional
  - No untracked dependency drift
  - Evidence: Git diff

- [ ] **Reproducible install verified**
  - Fresh environment install using lockfile only
  - Tests pass in clean environment
  - Evidence: CI or local install log

---

## 8. Observability & Diagnostics

- [ ] **Structured error payloads enforced**
  - Errors include: contract_id, fingerprint, node_id (via context kwargs)
  - **Note**: These fields are passed via `**context` kwargs, not enforced as mandatory fields
  - Commands:
    ```bash
    # Generate error object snapshot with all observability fields
    poetry run python -c "
    from omnibase_core.errors.declarative_errors import NodeExecutionError
    import json

    # Create error with all observability fields
    error = NodeExecutionError(
        'Execution failed during compute phase',
        node_id='node-compute-00000000-0000-0000-0000-000000000001',
        execution_phase='compute',
        contract_id='compute-contract-v1',
        fingerprint='0.4.0:8fa1e2b4c9d1'
    )

    snapshot = error.model_dump()
    print('=== ERROR OBJECT SNAPSHOT (Section 8 Evidence) ===')
    print(json.dumps(snapshot, indent=2, default=str))
    print('\\n=== OBSERVABILITY FIELDS VERIFICATION ===')
    print(f'correlation_id present: {\"correlation_id\" in snapshot}')
    print(f'node_id in context: {\"node_id\" in snapshot.get(\"context\", {})}')
    print(f'contract_id in context: {\"contract_id\" in snapshot.get(\"context\", {})}')
    print(f'fingerprint in context: {\"fingerprint\" in snapshot.get(\"context\", {})}')
    "

    # Run error model tests (492 lines covering ModelOnexError)
    poetry run pytest tests/unit/exceptions/test_onex_error.py -v --tb=short

    # Run declarative error tests (944 lines covering NodeExecutionError, etc.)
    poetry run pytest tests/unit/errors/test_declarative_errors.py -v --tb=short
    ```
  - Expected: Error objects contain correlation_id, node_id, contract_id, fingerprint in context
  - Evidence: Release issue comment (OMN-218) with error object JSON snapshot

- [ ] **Failure events emitted**
  - Node failures emit observable events via `MixinNodeLifecycle.emit_node_failure()`
  - No silent failures
  - Commands:
    ```bash
    # Demonstrate NODE_FAILURE event emission structure
    poetry run python -c "
    from omnibase_core.constants.event_types import NODE_FAILURE, NODE_SUCCESS, NODE_START
    from omnibase_core.models.core.model_onex_event import ModelOnexEvent
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_core.models.core.model_onex_event_metadata import ModelOnexEventMetadata
    from uuid import uuid4
    import json

    # Show event type constants
    print('=== Lifecycle Event Types ===')
    print(f'NODE_START: {NODE_START}')
    print(f'NODE_SUCCESS: {NODE_SUCCESS}')
    print(f'NODE_FAILURE: {NODE_FAILURE}')

    # Simulate what emit_node_failure() produces
    node_id = uuid4()
    correlation_id = uuid4()

    metadata = ModelOnexEventMetadata(
        error_message='COMPUTE node failed: validation error',
        error_code='ONEX_CORE_273_NODE_EXECUTION_ERROR',
        phase='compute',
        node_name='NodeDataTransformCompute'
    )

    event = ModelOnexEvent(
        event_type=NODE_FAILURE,
        node_id=node_id,
        metadata=metadata,
        correlation_id=correlation_id
    )

    envelope = ModelEventEnvelope(
        payload=event,
        source_tool=str(node_id),
        correlation_id=correlation_id
    )

    print('\\n=== EVENT LOG EXCERPT (Section 8 Evidence) ===')
    print(f'Event Type: {NODE_FAILURE}')
    print(f'Node ID: {node_id}')
    print(f'Correlation ID: {correlation_id}')
    print('\\n=== FULL EVENT ENVELOPE ===')
    print(json.dumps(envelope.model_dump(), indent=2, default=str))
    "

    # Verify MixinNodeLifecycle has emit_node_failure method
    poetry run python -c "
    from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle
    assert hasattr(MixinNodeLifecycle, 'emit_node_failure'), 'emit_node_failure method missing'
    print('✅ MixinNodeLifecycle.emit_node_failure() exists')
    "
    ```
  - Expected: NODE_FAILURE events contain node_id, correlation_id, error details in metadata
  - Evidence: Release issue comment (OMN-218) with event envelope JSON excerpt

---

## 9. Cross-Repository Compatibility

**Verification Summary**:
- **Repositories to verify**: 2-3 downstream repositories (omnibase_spi, omninode_core, example projects)
- **Expected verification time**: 30-60 minutes (cloning, testing, type checking)
- **Go/No-Go criteria**: All downstream tests must pass with 0 test failures and 0 mypy errors

### 9.1 Public API Stability

- [ ] **Public API exports unchanged or documented**
  - Verify `omnibase_core.nodes.__all__` exports are stable
  - Command: `poetry run python -c "from omnibase_core.nodes import *; print('API imports OK')"`
  - Expected: No ImportError, prints "API imports OK"
  - Evidence: Release issue comment (OMN-218) with command output

- [ ] **Core import paths verified**
  - All documented import paths resolve correctly
  - Commands:
    ```bash
    poetry run python -c "from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect"
    poetry run python -c "from omnibase_core.models.container.model_onex_container import ModelONEXContainer"
    poetry run python -c "from omnibase_core.models.errors.model_onex_error import ModelOnexError"
    poetry run python -c "from omnibase_core.enums import EnumNodeKind, EnumNodeType"
    ```
  - Expected: All imports succeed without error
  - Evidence: Command outputs (all four commands)

- [ ] **Breaking changes enumerated**
  - List all removed/renamed exports
  - List all changed method signatures
  - List all removed classes/functions
  - Evidence: CHANGELOG.md breaking changes section with explicit list

### 9.2 Downstream Repository Testing

- [ ] **omnibase_spi compatibility verified**
  - Clone omnibase_spi repository to temporary directory
  - Update omnibase_core dependency to v0.4.0 (or local editable)
  - Commands (cross-platform):
    ```bash
    # Linux/macOS: Use $TMPDIR or /tmp
    cd ${TMPDIR:-/tmp} && git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi
    # For editable install: Use absolute path to omnibase_core checkout
    poetry add /absolute/path/to/omnibase_core --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    ```
    **Windows**: Use `%TEMP%` or `$env:TEMP` instead of `/tmp`, e.g., `cd $env:TEMP`
  - Expected: All tests pass, mypy reports 0 errors
  - Evidence: Test output (pass count) and mypy report

- [ ] **omninode_core compatibility verified** (if applicable)
  - Clone omninode_core repository to temporary directory
  - Update omnibase_core dependency to v0.4.0
  - Commands (cross-platform):
    ```bash
    # Linux/macOS: Use $TMPDIR or /tmp
    cd ${TMPDIR:-/tmp} && git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core
    # For editable install: Use absolute path to omnibase_core checkout
    poetry add /absolute/path/to/omnibase_core --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    ```
    **Windows**: Use `%TEMP%` or `$env:TEMP` instead of `/tmp`, e.g., `cd $env:TEMP`
  - Expected: All tests pass, mypy reports 0 errors
  - Evidence: Test output and mypy report

- [ ] **Example projects verified** (if applicable)
  - Any official example projects compile and run
  - Expected: No runtime errors on documented examples
  - Evidence: Example execution logs or "N/A - no example projects"

### 9.3 Integration Contract Verification

- [ ] **Protocol implementations compatible**
  - All SPI protocols still satisfied by core implementations
  - Command: `poetry run python -c "from omnibase_core.models.container.model_onex_container import ModelONEXContainer; c = ModelONEXContainer(); print('Container init OK')"`
  - Expected: Container initializes without protocol violations
  - Evidence: Command output showing "Container init OK"

- [ ] **Event envelope compatibility verified**
  - ModelEventEnvelope schema unchanged or migration documented
  - Command: `poetry run python -c "from omnibase_core.models.event.model_event_envelope import ModelEventEnvelope; import json; print(json.dumps(ModelEventEnvelope.model_json_schema(), indent=2))"`
  - Expected: Schema matches v0.3.x specification or changes documented
  - Evidence: Schema output with diff against v0.3.x (if changed)

- [ ] **Contract YAML schema compatibility**
  - RuntimeHostContract YAML files from v0.3.x parse correctly
  - Command: `poetry run python -c "from omnibase_core.runtime.file_registry import FileRegistry; r = FileRegistry(); print('FileRegistry OK')"`
  - Expected: No schema validation errors for valid v0.3.x contracts
  - Evidence: Command output showing "FileRegistry OK"

### 9.4 Migration Verification

- [ ] **Migration guide tested end-to-end**
  - Create fresh project using v0.3.x patterns
  - Follow migration guide step-by-step
  - Verify tests pass after migration
  - Commands (cross-platform):
    ```bash
    # Example migration test workflow
    # Linux/macOS: Use $TMPDIR or /tmp
    cd ${TMPDIR:-/tmp} && mkdir migration-test && cd migration-test
    # Windows: Use $env:TEMP, e.g., cd $env:TEMP; mkdir migration-test; cd migration-test

    poetry init --name migration-test --python "^3.12"
    poetry add omnibase_core==0.3.6  # Start with old version
    # Create test file using v0.3.x patterns
    # Run migration steps from docs/guides/MIGRATING_TO_V040.md
    poetry add omnibase_core==0.4.0  # Upgrade
    poetry run pytest tests/
    ```
  - Expected: Migration completes successfully, tests pass
  - Evidence: Migration test log or documented test results

- [ ] **Deprecation warnings present**
  - Deprecated APIs emit warnings when used
  - Command: `poetry run python -W default::DeprecationWarning -c "from omnibase_core.nodes import NodeCompute; print('Deprecation check complete')"`
  - Expected: Deprecation warnings shown for any deprecated APIs (or none if no deprecations)
  - Evidence: Warning output (or confirmation of no deprecated APIs)

### 9.5 CI/CD Integration

- [ ] **GitHub Actions workflow compatible**
  - Downstream repos' CI workflows pass with v0.4.0
  - Verify by running downstream CI with v0.4.0 dependency
  - Expected: All CI checks pass (tests, type checking, linting)
  - Evidence: CI run links for each downstream repo

- [ ] **Docker builds succeed**
  - Downstream Docker images build with v0.4.0 dependency
  - Command: `docker build -t test-downstream .` (in downstream repo)
  - Expected: Build completes successfully
  - Evidence: Docker build log or "N/A - no Docker builds"

---

## 10. Documentation

- [ ] **Documentation updated**
  - CLAUDE.md reflects v0.4.0 architecture
  - Node building guides updated
  - Migration guide complete (if applicable)
  - CHANGELOG.md updated
  - Evidence: Documentation PR or commit

- [ ] **Breaking changes documented**
  - Each breaking change listed
  - Explicit migration instructions provided
  - Evidence: CHANGELOG section

---

## Verification Commands

```bash
# Type checking
poetry run mypy src/omnibase_core/ --strict

# Run tests
poetry run pytest tests/

# Coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# Pre-commit
pre-commit run --all-files

# Legacy pattern check (portable extended regex)
grep -rE "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/
# Alternative with ripgrep: rg "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/

# Contract fingerprint verification (using existing scripts)
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/ --validate --recursive
poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive --dry-run

# Contract linting
poetry run python scripts/lint_contract.py contracts/runtime/ --recursive --verbose

# FileRegistry contract loading test
poetry run pytest tests/unit/runtime/test_file_registry.py -v

# Error handling tests
poetry run pytest tests/unit/exceptions/test_onex_error.py tests/unit/errors/test_declarative_errors.py -v
```

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| Release Manager | | | |

---

## Release Notes Template

```markdown
## v0.4.0 Release Notes

### Highlights
- [Major changes]

### Breaking Changes
- [Breaking changes with migrations]

### New Features
- [New features]

### Bug Fixes
- [Bug fixes]

### Documentation
- [Docs updated]

### Dependencies
- [Dependency updates]
```

---

## Post-Release Verification

- [ ] **PyPI package published and verified**
  - Package install succeeds from PyPI
  - Version number matches release
  - Package integrity verified (hash comparison)
  - Smoke test imports work
  - Commands:
    ```bash
    # Install from PyPI
    pip install omnibase_core==0.4.0 --index-url https://pypi.org/simple/

    # Verify version
    python -c "import omnibase_core; print(omnibase_core.__version__)"

    # Verify package hash matches build artifact
    pip hash omnibase_core-0.4.0-py3-none-any.whl

    # Smoke test imports
    python -c "from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect; print('Import verification OK')"
    ```
  - Expected: All commands succeed, version prints "0.4.0", import prints "Import verification OK"
  - Evidence: Command outputs and hash comparison

- [ ] **Git tag created**
  - Tag: v0.4.0
  - Command: `git tag -l v0.4.0`
  - Evidence: Tag exists in repository

- [ ] **GitHub release published**
  - Release page: https://github.com/OmniNode-ai/omnibase_core/releases/tag/v0.4.0
  - Evidence: Release URL accessible

- [ ] **Documentation site updated**
  - Version 0.4.0 documentation live
  - Evidence: Documentation URL

- [ ] **Dependent repositories updated**
  - Downstream repos migrated or documented
  - Evidence: PR links or migration guide references

---

## 11. Rollback Procedure

> **Purpose**: Define recovery steps if critical issues are discovered post-release.

### 11.1 PyPI Rollback

If critical issues discovered after PyPI publish:

- [ ] **Yank the release** (makes package uninstallable for new users, existing installs unaffected)
  - Command: `poetry run twine yank omnibase_core==0.4.0`
  - Alternative: Use PyPI web interface → Manage → Yank version
  - **Note**: Yanking is reversible; deletion is NOT
  - Evidence: PyPI version page shows "yanked"

- [ ] **Publish hotfix version**
  - Bump to `0.4.1` with fix
  - Follow standard release process
  - Evidence: PyPI shows 0.4.1 available

### 11.2 Git Tag Rollback

If tag needs correction:

- [ ] **Delete remote tag** (use with caution)
  ```bash
  # Delete remote tag
  git push origin :refs/tags/v0.4.0

  # Delete local tag
  git tag -d v0.4.0

  # Create corrected tag
  git tag -a v0.4.0 <correct-commit-sha> -m "v0.4.0 release"
  git push origin v0.4.0
  ```
  - **Warning**: Only do this if tag was created on wrong commit and no one has pulled it
  - Evidence: `git log --oneline v0.4.0` shows correct commit

### 11.3 GitHub Release Rollback

- [ ] **Mark release as pre-release** (if issues found)
  - Edit release → Check "This is a pre-release"
  - Add warning note to release body
  - Evidence: Release page shows pre-release badge

- [ ] **Delete and recreate release** (if major issues)
  - Delete the GitHub release (does NOT delete tag)
  - Fix issues, create new tag if needed
  - Create new release
  - Evidence: New release page with correct content

### 11.4 Downstream Notification

- [ ] **Notify dependent repositories**
  - Create issues in omnibase_spi, omninode_core if affected
  - Include: Problem description, workaround, ETA for fix
  - Evidence: Issue links

- [ ] **Update migration guide**
  - Document any additional steps needed due to the issue
  - Evidence: Commit to docs/guides/MIGRATING_TO_V040.md

### 11.5 Rollback Decision Matrix

| Severity | Action | Timeline |
|----------|--------|----------|
| **Critical** (security, data loss) | Yank immediately + hotfix | < 4 hours |
| **High** (broken core functionality) | Yank + hotfix | < 24 hours |
| **Medium** (significant bugs) | Document workaround + plan fix | < 1 week |
| **Low** (minor issues) | Fix in next release | Next release cycle |

### 11.6 Post-Mortem

After any rollback:

- [ ] **Document incident**
  - What happened
  - How it was detected
  - What was the impact
  - What was the fix
  - How to prevent recurrence
  - Evidence: Post-mortem document or Linear issue
