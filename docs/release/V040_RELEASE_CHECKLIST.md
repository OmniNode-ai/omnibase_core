# v0.4.0 Release Gate Checklist (Hardened)

> **Version**: 0.4.0
> **Status**: Pre-release
> **Last Updated**: 2025-12-14
> **Linear Ticket**: [OMN-218](https://linear.app/omninode/issue/OMN-218)

This checklist defines **hard release gates** for v0.4.0.
All items are mandatory unless explicitly marked as informational.
All checks require **verifiable evidence**. No exceptions, no vibes.

---

## Gate Severity Definitions

| Severity | Meaning | Consequence |
|----------|---------|-------------|
| **🚫 BLOCKER** | Release cannot proceed | Must be resolved before ANY release artifacts are created |
| **✅ REQUIRED** | Must pass before release | Can be worked in parallel, but all must pass before sign-off |
| **📋 INFORMATIONAL** | Documented state | No pass/fail, just recorded for audit |

**Enforcement Rule**: A single BLOCKER failure stops the entire release process. REQUIRED gates must all pass before the release manager can sign off.

---

## Evidence Storage Guidelines

### Primary Storage Location

All release evidence MUST be stored in the **release tracking issue** on Linear:
- Issue: [OMN-218](https://linear.app/omninode/issue/OMN-218) (or the corresponding release issue)
- Create a comment thread per section (e.g., "Section 1: Code Quality Evidence")
- Link to artifacts rather than embedding large outputs inline

> **ENFORCEMENT RULE**: Evidence without a canonical storage location is NOT valid evidence.
> Before marking ANY gate complete, verify the evidence is stored in one of the three locations below.
> "I ran the command locally" is NOT evidence. "Here is the output stored in OMN-218 comment #42" IS evidence.

### Evidence Types and Storage

**CRITICAL RULE**: Evidence MUST be stored in one of three canonical locations:
1. **Release issue comment** ([OMN-218](https://linear.app/omninode/issue/OMN-218)) - for command outputs, CI links, and inline evidence
2. **GitHub Gist** - for large outputs (>50 lines) with link posted to release issue
3. **`artifacts/release/v0.4.0/`** - for versioned files (fingerprints, coverage, logs)

**"Attached output" Standardization**: When this checklist says "Evidence: Attached output", it means:
- Post the command output as a code block in the release issue comment
- Include timestamp, commit SHA, and toolchain versions
- For outputs >50 lines, create a GitHub Gist and link it

| Evidence Type | Where to Store | Format |
|---------------|----------------|--------|
| **CI run links** | Release issue comment | Direct URL to GitHub Actions run |
| **Command output** (<50 lines) | Release issue comment | Code block with timestamp |
| **Command output** (>50 lines) | GitHub Gist | Link in release issue |
| **Screenshots** | Release issue attachment | PNG with descriptive filename (see note below) |
| **Coverage reports** | CI artifacts + link | HTML report or term output |
| **Test logs** | CI artifacts | Link to specific job/step |
| **Contract fingerprint reports** | `artifacts/release/v0.4.0/` | JSON or text file |
| **Replay logs** | `artifacts/release/v0.4.0/` | Timestamped log files |

### ⚠️ Text Evidence Preferred

**Terminal output MUST be stored as text unless impossible.**

Screenshots should be explicitly discouraged for evidence that can be captured as text:
- ❌ Screenshot of terminal output → ✅ Copy/paste text into code block
- ❌ Screenshot of test results → ✅ Raw pytest output as text
- ❌ Screenshot of mypy output → ✅ Plain text mypy output

**Why text over screenshots:**
- Diffable for regression detection
- Searchable in audits
- Version-controllable
- Not subject to rendering differences
- Machine-parseable for automation

**Acceptable screenshot use cases:**
- GUI-only artifacts (browser rendering, visual regression)
- Diagrams that cannot be represented as text
- External tool outputs that cannot be copied

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

> **CRITICAL WARNING FOR EVIDENCE STORAGE**: Logs, screenshots, gists, and any other evidence
> artifacts MUST be scrubbed for PII and secrets BEFORE posting. This applies to:
>
> - Terminal output logs (may contain environment variables, paths with usernames)
> - Screenshots (may show sensitive data in editor tabs, terminal history)
> - GitHub Gists (publicly accessible by default)
> - CI/CD logs (may contain build secrets, API tokens)
>
> **Review every artifact before posting. There is no "undo" for published secrets.**

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

Each gate requires the following **MANDATORY** fields:

1. **Timestamp**: When the verification was performed (ISO-8601 UTC format)
2. **Command/Action**: Exact command run or action taken (copy-pasteable)
3. **Output**: Result (success/failure with details)
4. **Commit SHA**: Git commit at time of verification (`git rev-parse HEAD`)
5. **Verifier**: Who performed the check (@username or email)
6. **Toolchain Versions**: Python, Poetry, and tool-specific versions (see below)

**Toolchain Version Requirement**: Every evidence submission MUST include:
- Python version (`python --version`)
- Poetry version (`poetry --version`)
- Tool-specific version (e.g., `poetry run mypy --version` for type checks)

This ensures evidence is reproducible. "Works on my machine" is meaningless without version context.

### Example Evidence Reference

```markdown
### Gate: Strict type safety enforced
- **Timestamp**: 2025-12-14T14:30:00Z
- **Commit**: abc1234def5678 (full SHA preferred)
- **Toolchain**:
  - Python: 3.12.5
  - Poetry: 1.8.4
  - mypy: 1.11.0
- **Command**: `poetry run mypy src/omnibase_core/ --strict`
- **Result**: PASS (0 errors, 1865 source files checked)
- **CI Link**: <https://github.com/OmniNode-ai/omnibase_core/actions/runs/12345>
- **Verifier**: @username
```

> **NOTE**: The example above shows all required fields. Missing any field makes the evidence INVALID.

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
- **Tool-specific versions**: Capture version of verification tools (mypy, pytest, ruff, etc.)

**Toolchain Version Capture Script**:

Run this before any verification to establish baseline versions:

```bash
# =============================================================================
# Toolchain Version Capture (run before verification)
# =============================================================================
echo "=== Toolchain Versions for Evidence ===" | tee artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "Commit: $(git rev-parse HEAD)" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "Python: $(python --version)" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "Poetry: $(poetry --version)" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "Platform: $(uname -srm)" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "=== Tool Versions ===" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
poetry run mypy --version | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
poetry run pytest --version | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
poetry run ruff --version | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
poetry run black --version | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
poetry run isort --version | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
echo "=== Dependency Lock Hash ===" | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
sha256sum poetry.lock | tee -a artifacts/release/v0.4.0/00-toolchain-versions.txt
```

**Rationale**: Tool versions drift over time. Capturing exact versions ensures evidence is reproducible and helps diagnose issues where "it worked on my machine" but fails in CI or production.

**Example Evidence with Toolchain Versions**:

```markdown
### Gate: Strict type safety enforced
- **Timestamp**: 2025-12-14T14:30:00Z
- **Commit**: abc1234def56789012345678901234567890abcd
- **Toolchain**:
  - Python: 3.12.5
  - Poetry: 1.8.4
  - mypy: 1.11.0
  - Platform: Linux 5.15.0-x86_64
- **Command**: `poetry run mypy src/omnibase_core/ --strict`
- **Result**: PASS (0 errors, 1865 source files checked)
- **CI Link**: <https://github.com/OmniNode-ai/omnibase_core/actions/runs/12345>
- **Verifier**: @username
```

**Rationale**: Toolchain versions ensure evidence is reproducible and helps diagnose platform-specific issues. The tool-specific version (mypy in this example) is REQUIRED because different mypy versions can produce different results.

### Pre-Release Evidence Checklist

Before marking a gate complete:
1. Evidence is stored in the correct location
2. Evidence includes all required fields (timestamp, commit, result, **toolchain versions**)
3. Links are accessible and not broken
4. Large outputs are in Gists or artifacts (not inline)
5. Evidence index is updated (`artifacts/release/v0.4.0/evidence-index.md`)

---

## 1. Code Quality

- [ ] **All nodes pure-checked (AST)** `✅ REQUIRED`
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
  - **⚠️ IMPORTANT**: These commands MUST be executed explicitly. Test pass status does NOT constitute evidence.
  - **Future**: Consider creating `omnibase_core.tools.ast_checker` CLI (tracked in MVP_PLAN.md, Beta scope)

- [ ] **Strict type safety enforced** `🚫 BLOCKER`
  - Command: `poetry run mypy src/omnibase_core/ --strict`
  - Expected: 0 errors
  - **⚠️ Version Lock**: Mypy version MUST be captured in evidence to prevent tool drift
  - Commands:
    ```bash
    # Capture mypy version for reproducibility
    poetry run mypy --version >> artifacts/release/v0.4.0/01-code-quality-mypy-version.txt

    # Run type checking
    poetry run mypy src/omnibase_core/ --strict
    ```
  - Evidence: Release issue comment (OMN-218) with CI run link AND mypy version or artifacts/release/v0.4.0/01-code-quality-mypy-YYYYMMDD.txt

- [ ] **Pre-commit hooks pass** `✅ REQUIRED`
  - Command: `pre-commit run --all-files`
  - Hooks: black, isort, ruff, mypy
  - Evidence: Release issue comment (OMN-218) with CI run link or text output (NOT screenshot)

---

## 2. Testing

- [ ] **CI passes all parallel test splits** `🚫 BLOCKER`
  - All splits succeed
  - No test flakiness retries allowed (pytest-rerunfailures disabled for test execution)
  - **Scope**: This prohibition applies specifically to masking flaky tests with automatic retries. Application-level retry patterns (e.g., network retries, circuit breakers) are unaffected and remain appropriate.
  - **Rationale**: Flaky tests indicate non-deterministic behavior that must be fixed at the source. Retries mask real bugs and create false confidence. Tests must be deterministic.
  - **Note**: Expect pressure to weaken this later. Do not.
  - Expected runtime: 2m30s-3m30s per split
  - Evidence: Release issue comment (OMN-218) with GitHub Actions run link

- [ ] **Adapter fuzz testing completed** `✅ REQUIRED (MVP minimal)` / `🚫 BLOCKER (Beta full)`
  - All adapters fuzzed with randomized inputs using Hypothesis
  - No crashes or undefined behavior
  - **Tool**: Hypothesis `^6.148` (installed in pyproject.toml)
  - **Status**: Adapter fuzz tests planned in MVP_PLAN.md Issue 3.8, minimal tests exist currently
  - **MVP Scope (v0.4.0)**: Minimum 3 adapter types fuzzed with 50+ examples each
  - **Beta Scope (v0.5.0+)**: All adapters fuzzed with 200+ examples, crash recovery verified
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
  - **⚠️ WARNING**: Without explicit MVP/Beta scope, someone will later claim fuzzing was "done" when it was not. The scopes above are enforceable bounds.

- [ ] **Coverage threshold met** `✅ REQUIRED`
  - Minimum: 60% **line coverage** (not branch coverage)
  - **Enforcement mechanism**: pytest-cov with `--cov-fail-under=60` flag causes CI to fail if threshold not met
  - **Measurement**: Line coverage counts executed lines / total lines; branch coverage (not required) would count executed branches / total branches
  - Command: `poetry run pytest tests/ --cov=src/omnibase_core --cov-fail-under=60 --cov-report=term-missing`
  - **Note**: Coverage is not correctness. This metric prevents metric worship—60% is a floor, not a goal.
  - Evidence: Release issue comment (OMN-218) with CI artifacts link or artifacts/release/v0.4.0/coverage/index.html

- [ ] **Negative-path tests present** `✅ REQUIRED`
  - At least one failure-mode test per contract class
  - Explicit assertions on error shape
  - Evidence: Release issue comment (OMN-218) with specific test file paths (e.g., tests/unit/test_negative_paths.py)

---

## 3. Determinism & Replayability

- [ ] **Deterministic execution verified** `🚫 BLOCKER`
  - Identical inputs produce identical outputs
  - Hash comparison of emitted ModelActions or events
  - **Hash Scope Definition**: Hashes are computed over **canonicalized outputs**. The following are EXCLUDED from hash computation:
    - Timestamps (creation time, modification time, execution time)
    - UUIDs generated at runtime (correlation_id, trace_id)
    - Dict ordering noise (canonicalize with sorted keys)
    - Floating-point precision beyond 6 decimal places
  - **Hash Inclusion**: The following MUST be included in hashes:
    - All business logic outputs (computed values, transformed data)
    - State transitions (FSM states, workflow phases)
    - Error codes and error messages
    - Contract fingerprints
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/replay-logs/determinism-hashes-YYYYMMDD.txt

- [ ] **Replay validation completed** `✅ REQUIRED`
  - At least one representative workflow replayed end-to-end
  - Replay output matches original execution exactly
  - **⚠️ REQUIRED**: At least ONE orchestrator-heavy replay (not just compute-only)
    - Must include: Multiple node transitions, state reduction, at least one retry/recovery path
    - Compute-only replays are the easy case and do not catch real bugs
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/replay-logs/replay-comparison-YYYYMMDD.txt

---

## 4. Contracts & Architecture

- [ ] **All contracts have valid fingerprints** `✅ REQUIRED`
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

- [ ] **Fingerprint enforcement validated** `🚫 BLOCKER`
  - Modified contract fails verification
  - No fallback or silent acceptance
  - **🚫 PROHIBITION**: Runtime fingerprint regeneration is FORBIDDEN. Future contributors will try to be "helpful" by auto-regenerating fingerprints. This defeats the purpose of fingerprints as drift detection.
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

- [ ] **All nodes are contract-driven** `✅ REQUIRED`
  - No legacy node implementations remain
  - **Preferred** (ripgrep): `rg "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/`
  - **Alternative** (portable grep with extended regex): `grep -rE "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/`
  - **Note**: The `-E` flag enables extended regex (required for `|` alternation). Basic `grep -r` without `-E` will not match correctly.
  - Expected: Empty output (exit code 1 for grep/rg when no matches)
  - Evidence: Release issue comment (OMN-218) with command output
  - **Future**: Automate this check in CI before Beta (currently grep-based is acceptable for MVP)

---

## 5. Registry & Discovery Integrity

- [ ] **Registry loads all contracts** `🚫 BLOCKER`
  - No orphaned or unreachable contracts
  - **⚠️ FAILURE SEMANTICS**: Registry load failure MUST be fatal. Partial loads are NOT allowed.
    - If any contract fails to load, the entire registry initialization MUST fail
    - Silent fallback to partial state is forbidden
    - This ensures "all-or-nothing" contract loading
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

- [ ] **Contract-to-node resolution verified** `✅ REQUIRED`
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

- [ ] **Semantic versioning enforced** `✅ REQUIRED`
  - Version bump aligns with documented breaking changes
  - Evidence: CHANGELOG and tag comparison

- [ ] **Upgrade behavior verified** `✅ REQUIRED`
  - v0.3.x -> v0.4.0 upgrade path documented and tested
  - Evidence: Migration test or documented failure mode

- [ ] **Downgrade behavior declared** `✅ REQUIRED`
  - **EXPLICIT DECLARATION REQUIRED**: Either:
    - Downgrade tested and supported (with evidence), OR
    - Downgrade explicitly unsupported and fails fast (documented)
  - Silence here will be misinterpreted as support. State the policy clearly.
  - Evidence: Documentation or test

---

## 7. Dependency & Build Reproducibility

- [ ] **Dependency lock verified** `✅ REQUIRED`
  - poetry.lock committed and intentional
  - No untracked dependency drift
  - **⚠️ Lock Hash Capture**: Capture poetry.lock hash in evidence to prevent silent re-lock drift
  - Commands:
    ```bash
    # Verify lock file is committed
    git status poetry.lock

    # Capture lock file hash for evidence
    sha256sum poetry.lock >> artifacts/release/v0.4.0/07-dependencies-lock-hash.txt

    # Verify no pending dependency changes
    poetry lock --check
    ```
  - Evidence: Git diff AND lock file hash

- [ ] **Reproducible install verified** `✅ REQUIRED`
  - **⚠️ REQUIRED**: Fresh virtualenv smoke install (pip installs can lie)
  - Fresh environment install using lockfile only
  - Tests pass in clean environment
  - Commands:
    ```bash
    # Create fresh virtualenv for verification
    python -m venv /tmp/v040-verify-env
    source /tmp/v040-verify-env/bin/activate  # Linux/macOS
    # Windows: /tmp/v040-verify-env/Scripts/activate

    # Install from lock file only
    pip install poetry
    poetry install --no-root

    # Run smoke tests
    python -c "from omnibase_core.nodes import NodeCompute; print('Smoke OK')"
    poetry run pytest tests/unit/ -x --tb=short -q

    # Cleanup
    deactivate
    rm -rf /tmp/v040-verify-env
    ```
  - Evidence: CI or local install log from fresh environment

---

## 8. Observability & Diagnostics

- [ ] **Structured error payloads enforced** `✅ REQUIRED (MVP)` / `🚫 BLOCKER (Beta)`
  - Errors include: contract_id, fingerprint, node_id (via context kwargs)
  - **MVP Note**: These fields are passed via `**context` kwargs, not enforced as mandatory fields
  - **Beta Requirement**: Mandatory structured fields at model level (schema-enforced, not kwargs)
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

- [ ] **Failure events emitted** `✅ REQUIRED`
  - Node failures emit observable events via `MixinNodeLifecycle.emit_node_failure()`
  - No silent failures
  - **Emission Guarantees** (document in evidence):
    - Synchronous vs buffered: State which applies
    - Delivery guarantees: Best-effort vs guaranteed (at-least-once)
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

### Verification Summary

**Purpose**: Ensure v0.4.0 does not break downstream consumers.

| Repository | Priority | Test Scope | Time Estimate |
|------------|----------|------------|---------------|
| `omnibase_spi` | BLOCKER | Full test suite + mypy | 15-20 min |
| `omninode_core` | REQUIRED | Full test suite + mypy | 15-20 min |
| Example projects | INFORMATIONAL | Smoke tests only | 5-10 min |

**Total Expected Time**: 30-60 minutes (including clone/setup overhead)

**Go/No-Go Criteria**:
- **MUST PASS** (hard requirements):
  - All downstream test suites pass with **0 test failures**
  - All downstream mypy checks pass with **0 errors**
  - All documented import paths resolve without ImportError
  - Migration guide steps complete without manual intervention
- **SHOULD PASS** (soft requirements):
  - No new deprecation warnings introduced without documentation
  - Docker builds succeed (if applicable)
  - Example projects run without modification

**Failure Handling**:
- Any BLOCKER failure: Stop release, fix issue, restart verification
- Any REQUIRED failure: Document issue, assess impact, decide proceed/stop
- INFORMATIONAL failures: Document for release notes, proceed with release

### Cross-Platform Temporary Directory Note

> **IMPORTANT**: Commands in this section use temporary directories for isolated testing.
> Choose the appropriate approach for your platform:
>
> | Platform | Temporary Directory | Example |
> |----------|---------------------|---------|
> | Linux | `${TMPDIR:-/tmp}` | `cd ${TMPDIR:-/tmp}` |
> | macOS | `${TMPDIR:-/tmp}` | `cd ${TMPDIR:-/tmp}` |
> | Windows (PowerShell) | `$env:TEMP` | `cd $env:TEMP` |
> | Windows (CMD) | `%TEMP%` | `cd %TEMP%` |
> | Project-local (any OS) | `./tmp` or `../_downstream_test` | `mkdir -p ../_downstream_test && cd ../_downstream_test` |
>
> **Recommendation**: Use project-local directories (e.g., `../_downstream_test`) for better reproducibility
> and easier cleanup. These directories should be added to `.gitignore`.

### 9.1 Public API Stability

- [ ] **Public API exports unchanged or documented** `✅ REQUIRED`
  - Verify `omnibase_core.nodes.__all__` exports are stable
  - **⚠️ Capture `__all__` diff automatically** as evidence
  - Commands:
    ```bash
    # Capture current __all__ exports for evidence
    poetry run python -c "from omnibase_core.nodes import __all__; print('\\n'.join(sorted(__all__)))" > artifacts/release/v0.4.0/09-api-exports.txt

    # Verify wildcard import works
    poetry run python -c "from omnibase_core.nodes import *; print('API imports OK')"
    ```
  - Expected: No ImportError, prints "API imports OK"
  - Evidence: Release issue comment (OMN-218) with `__all__` export list AND command output

- [ ] **Core import paths verified** `✅ REQUIRED`
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

- [ ] **Breaking changes enumerated** `✅ REQUIRED`
  - List all removed/renamed exports
  - List all changed method signatures
  - List all removed classes/functions
  - Evidence: CHANGELOG.md breaking changes section with explicit list

### 9.2 Downstream Repository Testing

- [ ] **omnibase_spi compatibility verified** `🚫 BLOCKER`
  - Clone omnibase_spi repository to temporary directory
  - Update omnibase_core dependency to v0.4.0 (or local editable)
  - Commands:

    **Option A: Project-local directory (Recommended - works on all platforms)**
    ```bash
    # From omnibase_core root directory
    mkdir -p ../_downstream_test && cd ../_downstream_test
    git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi
    # Use absolute path to omnibase_core for editable install
    poetry add "$(cd ../../omnibase_core && pwd)" --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    # Cleanup when done: rm -rf ../_downstream_test
    ```

    **Option B: Linux/macOS system temp**
    ```bash
    cd ${TMPDIR:-/tmp} && git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi
    poetry add /absolute/path/to/omnibase_core --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    ```

    **Option C: Windows PowerShell**
    ```powershell
    cd $env:TEMP
    git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi
    poetry add C:\path\to\omnibase_core --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    ```

  - Expected: All tests pass, mypy reports 0 errors
  - Evidence: Test output (pass count) and mypy report

- [ ] **omninode_core compatibility verified** (if applicable) `✅ REQUIRED`
  - Clone omninode_core repository to temporary directory
  - Update omnibase_core dependency to v0.4.0
  - Commands:

    **Option A: Project-local directory (Recommended - works on all platforms)**
    ```bash
    # From omnibase_core root directory
    mkdir -p ../_downstream_test && cd ../_downstream_test
    git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core
    # Use absolute path to omnibase_core for editable install
    poetry add "$(cd ../../omnibase_core && pwd)" --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    # Cleanup when done: rm -rf ../_downstream_test
    ```

    **Option B: Linux/macOS system temp**
    ```bash
    cd ${TMPDIR:-/tmp} && git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core
    poetry add /absolute/path/to/omnibase_core --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    ```

    **Option C: Windows PowerShell**
    ```powershell
    cd $env:TEMP
    git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core
    poetry add C:\path\to\omnibase_core --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    poetry run mypy src/
    ```

  - Expected: All tests pass, mypy reports 0 errors
  - Evidence: Test output and mypy report

- [ ] **Example projects verified** (if applicable) `📋 INFORMATIONAL`
  - Any official example projects compile and run
  - Expected: No runtime errors on documented examples
  - Evidence: Example execution logs or "N/A - no example projects"

### 9.3 Integration Contract Verification

- [ ] **Protocol implementations compatible** `✅ REQUIRED`
  - All SPI protocols still satisfied by core implementations
  - Command: `poetry run python -c "from omnibase_core.models.container.model_onex_container import ModelONEXContainer; c = ModelONEXContainer(); print('Container init OK')"`
  - Expected: Container initializes without protocol violations
  - Evidence: Command output showing "Container init OK"

- [ ] **Event envelope compatibility verified** `✅ REQUIRED`
  - ModelEventEnvelope schema unchanged or migration documented
  - Command: `poetry run python -c "from omnibase_core.models.event.model_event_envelope import ModelEventEnvelope; import json; print(json.dumps(ModelEventEnvelope.model_json_schema(), indent=2))"`
  - Expected: Schema matches v0.3.x specification or changes documented
  - Evidence: Schema output with diff against v0.3.x (if changed)

- [ ] **Contract YAML schema compatibility** `✅ REQUIRED`
  - RuntimeHostContract YAML files from v0.3.x parse correctly
  - Command: `poetry run python -c "from omnibase_core.runtime.file_registry import FileRegistry; r = FileRegistry(); print('FileRegistry OK')"`
  - Expected: No schema validation errors for valid v0.3.x contracts
  - Evidence: Command output showing "FileRegistry OK"

### 9.4 Migration Verification

- [ ] **Migration guide tested end-to-end** `✅ REQUIRED`
  - Create fresh project using v0.3.x patterns
  - Follow migration guide step-by-step
  - Verify tests pass after migration
  - Commands:

    **Option A: Project-local directory (Recommended - works on all platforms)**
    ```bash
    # From omnibase_core root directory
    mkdir -p ../_migration_test && cd ../_migration_test
    poetry init --name migration-test --python "^3.12"
    poetry add omnibase_core==0.3.6  # Start with old version
    # Create test file using v0.3.x patterns
    # Run migration steps from docs/guides/MIGRATING_TO_V040.md
    poetry add omnibase_core==0.4.0  # Upgrade
    poetry run pytest tests/
    # Cleanup when done: rm -rf ../_migration_test
    ```

    **Option B: Linux/macOS system temp**
    ```bash
    cd ${TMPDIR:-/tmp} && mkdir migration-test && cd migration-test
    poetry init --name migration-test --python "^3.12"
    poetry add omnibase_core==0.3.6  # Start with old version
    # Create test file using v0.3.x patterns
    # Run migration steps from docs/guides/MIGRATING_TO_V040.md
    poetry add omnibase_core==0.4.0  # Upgrade
    poetry run pytest tests/
    ```

    **Option C: Windows PowerShell**
    ```powershell
    cd $env:TEMP
    mkdir migration-test
    cd migration-test
    poetry init --name migration-test --python "^3.12"
    poetry add omnibase_core==0.3.6  # Start with old version
    # Create test file using v0.3.x patterns
    # Run migration steps from docs/guides/MIGRATING_TO_V040.md
    poetry add omnibase_core==0.4.0  # Upgrade
    poetry run pytest tests/
    ```

  - Expected: Migration completes successfully, tests pass
  - Evidence: Migration test log or documented test results

- [ ] **Deprecation warnings present** `📋 INFORMATIONAL`
  - Deprecated APIs emit warnings when used
  - Command: `poetry run python -W default::DeprecationWarning -c "from omnibase_core.nodes import NodeCompute; print('Deprecation check complete')"`
  - Expected: Deprecation warnings shown for any deprecated APIs (or none if no deprecations)
  - Evidence: Warning output (or confirmation of no deprecated APIs)

### 9.5 CI/CD Integration

- [ ] **GitHub Actions workflow compatible** `✅ REQUIRED`
  - Downstream repos' CI workflows pass with v0.4.0
  - Verify by running downstream CI with v0.4.0 dependency
  - Expected: All CI checks pass (tests, type checking, linting)
  - Evidence: CI run links for each downstream repo

- [ ] **Docker builds succeed** `📋 INFORMATIONAL`
  - Downstream Docker images build with v0.4.0 dependency
  - Command: `docker build -t test-downstream .` (in downstream repo)
  - Expected: Build completes successfully
  - Evidence: Docker build log or "N/A - no Docker builds"

---

## 10. Documentation

- [ ] **Documentation updated** `✅ REQUIRED`
  - CLAUDE.md reflects v0.4.0 architecture
  - Node building guides updated
  - Migration guide complete (if applicable)
  - CHANGELOG.md updated
  - **⚠️ Doc Commit SHA**: Record the commit SHA of documentation freeze to prevent freeze-era doc drift
  - Evidence: Documentation PR or commit SHA

- [ ] **Breaking changes documented** `🚫 BLOCKER`
  - Each breaking change listed
  - Explicit migration instructions provided
  - Evidence: CHANGELOG section

---

## Verification Commands

Commands grouped by section for faster evidence mapping during audits:

> **CRITICAL**: Run the **Toolchain Version Capture Script** (see Section "Toolchain Version Requirements")
> BEFORE running ANY verification commands. This establishes baseline versions for reproducibility.
> Store output in `artifacts/release/v0.4.0/00-toolchain-versions.txt` as your first evidence artifact.

```bash
# =============================================================================
# STEP 0: TOOLCHAIN VERSION CAPTURE (MANDATORY FIRST STEP)
# =============================================================================
# Create artifacts directory if it doesn't exist
mkdir -p artifacts/release/v0.4.0

# Run the toolchain version capture script from "Toolchain Version Requirements"
# This captures: Python, Poetry, Platform, mypy, pytest, ruff, black, isort, poetry.lock hash
# Store output as first evidence artifact: artifacts/release/v0.4.0/00-toolchain-versions.txt

# =============================================================================
# Section 1: Code Quality
# =============================================================================
# NOTE: Version already captured in Step 0, but inline capture for CI logs:
echo "=== mypy version ===" && poetry run mypy --version
poetry run mypy src/omnibase_core/ --strict
echo "=== ruff version ===" && poetry run ruff --version
pre-commit run --all-files

# =============================================================================
# Section 2: Testing
# =============================================================================
echo "=== pytest version ===" && poetry run pytest --version
poetry run pytest tests/
poetry run pytest tests/ --cov=src/omnibase_core --cov-fail-under=60 --cov-report=term-missing

# =============================================================================
# Section 4: Contracts & Architecture
# =============================================================================
# Contract fingerprint verification (using existing scripts)
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/ --validate --recursive
poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive --dry-run

# Contract linting
poetry run python scripts/lint_contract.py contracts/runtime/ --recursive --verbose

# Legacy pattern check
# Preferred (ripgrep - faster, better defaults):
rg "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/
# Alternative (portable grep with -E for extended regex - required for | alternation):
grep -rE "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/

# =============================================================================
# Section 5: Registry & Discovery
# =============================================================================
# FileRegistry contract loading test
poetry run pytest tests/unit/runtime/test_file_registry.py -v

# =============================================================================
# Section 7: Dependencies
# =============================================================================
sha256sum poetry.lock  # Capture lock hash
poetry lock --check

# =============================================================================
# Section 8: Observability
# =============================================================================
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

### Post-Release Integrity Checks

These checks verify that the published package is correct, complete, and functional.

- [ ] **PyPI package published and installable** `🚫 BLOCKER`
  - Package install succeeds from PyPI in a fresh environment
  - Version number matches release
  - Package integrity verified (hash comparison against build artifact)
  - All documented imports work
  - Commands:
    ```bash
    # =============================================================================
    # Step 1: Create isolated verification environment
    # =============================================================================
    python -m venv /tmp/v040-pypi-verify
    source /tmp/v040-pypi-verify/bin/activate  # Linux/macOS
    # Windows: /tmp/v040-pypi-verify/Scripts/activate

    # =============================================================================
    # Step 2: Install from PyPI (NOT from local source)
    # =============================================================================
    pip install omnibase_core==0.4.0 --index-url https://pypi.org/simple/

    # Verify installation succeeded
    pip show omnibase_core

    # =============================================================================
    # Step 3: Version verification
    # =============================================================================
    python -c "import omnibase_core; print(f'Version: {omnibase_core.__version__}')"
    # Expected output: "Version: 0.4.0"

    # =============================================================================
    # Step 4: Package hash verification (CRITICAL for supply chain security)
    # =============================================================================
    # Download wheel to verify hash
    pip download omnibase_core==0.4.0 --no-deps -d /tmp/v040-wheel-verify/

    # Compute hash of downloaded wheel
    PYPI_HASH=$(sha256sum /tmp/v040-wheel-verify/omnibase_core-0.4.0-py3-none-any.whl | cut -d' ' -f1)
    echo "PyPI wheel SHA256: ${PYPI_HASH}"

    # Compare against build artifact hash from CI
    # The canonical hash is stored in:
    #   1. GitHub Actions artifact: "release-artifacts/wheel-sha256.txt"
    #   2. GitHub Release attachment: "omnibase_core-0.4.0.sha256"
    #   3. Release notes body: SHA256 checksum section
    #
    # Retrieve expected hash (example using GitHub CLI):
    # gh release download v0.4.0 --pattern "*.sha256" --output /tmp/expected-hash.txt
    # EXPECTED_HASH=$(cat /tmp/expected-hash.txt | grep ".whl" | cut -d' ' -f1)
    #
    # Verify match (MUST be exact):
    # if [ "${PYPI_HASH}" = "${EXPECTED_HASH}" ]; then
    #   echo "Hash verification: PASS"
    # else
    #   echo "Hash verification: FAIL - Supply chain compromise possible!"
    #   exit 1
    # fi

    # =============================================================================
    # Step 5: Smoke test imports (ALL core imports)
    # =============================================================================
    python -c "
    # Core node imports
    from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect
    print('Core nodes: OK')

    # Container import
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    print('Container: OK')

    # Error handling import
    from omnibase_core.models.errors.model_onex_error import ModelOnexError
    print('Errors: OK')

    # Enum imports
    from omnibase_core.enums import EnumNodeKind, EnumNodeType
    print('Enums: OK')

    # Event envelope import
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    print('Events: OK')

    # Mixin imports
    from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle
    print('Mixins: OK')

    print('\\nAll smoke test imports: PASS')
    "

    # =============================================================================
    # Step 6: Functional smoke test (actually instantiate objects)
    # =============================================================================
    python -c "
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.errors.model_onex_error import ModelOnexError
    from omnibase_core.enums import EnumNodeKind

    # Test container instantiation
    container = ModelONEXContainer()
    print(f'Container instantiated: {type(container).__name__}')

    # Test error instantiation
    error = ModelOnexError(message='Test error', error_code='TEST_001')
    print(f'Error instantiated: {error.error_code}')

    # Test enum access
    print(f'EnumNodeKind.COMPUTE: {EnumNodeKind.COMPUTE}')

    print('\\nFunctional smoke test: PASS')
    "

    # =============================================================================
    # Step 7: Cleanup
    # =============================================================================
    deactivate
    rm -rf /tmp/v040-pypi-verify /tmp/v040-wheel-verify
    ```
  - **Expected Results**:
    - `pip install` completes without errors
    - Version prints exactly "0.4.0"
    - Package hash matches build artifact from CI
    - All import statements succeed
    - Object instantiation works without errors
  - **Evidence**: Full command output with all steps, hash comparison result
  - **Failure Handling**: If ANY step fails, DO NOT proceed with downstream notifications. Investigate and fix first.

- [ ] **Git tag created** `✅ REQUIRED`
  - Tag: v0.4.0
  - Command: `git tag -l v0.4.0`
  - Evidence: Tag exists in repository

- [ ] **GitHub release published**
  - Release page: <https://github.com/OmniNode-ai/omnibase_core/releases/tag/v0.4.0>
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
