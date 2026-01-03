# v0.4.0 Release Gate Checklist (Hardened)

> **Version**: 0.4.0
> **Status**: Pre-release
> **Last Updated**: 2025-12-15
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
- **Post the command output as a code block** in the release issue comment (NOT as a screenshot)
- **Include mandatory metadata**: timestamp (ISO-8601 UTC), commit SHA (full 40-char), and toolchain versions (Python, Poetry, tool-specific)
- **For outputs >50 lines**: Create a GitHub Gist and post the link to the release issue
- **Format**: Use triple-backtick code fences with language hint (e.g., ```bash or ```python or ```text)
- **Location**: Must be in one of the three canonical locations listed below (release issue, Gist, or artifacts/)

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

**Evidence Location Summary** (Three Canonical Locations):

1. **Linear Release Issue** ([OMN-218](https://linear.app/omninode/issue/OMN-218))
   - **Use for**: Command outputs <50 lines, CI run links, short evidence snippets
   - **Format**: Code block in comment with metadata (timestamp, commit SHA, toolchain versions)
   - **Example**: Mypy output, pytest summary, linting results

2. **GitHub Gist**
   - **Use for**: Command outputs >50 lines that would clutter the issue
   - **Format**: Create Gist, post link in release issue comment
   - **Example**: Full pytest verbose output, complete coverage report, large test logs

3. **Artifacts Directory** (`artifacts/release/v0.4.0/`)
   - **Use for**: Versioned files, binary outputs, structured reports
   - **Format**: Timestamped files with descriptive names (see naming conventions below)
   - **Example**: Coverage HTML reports, fingerprint verification JSONs, replay logs

**Evidence Validation Rule**: Before marking ANY gate complete, verify the evidence is in one of these three locations. "I ran the command locally" is NOT valid evidence.

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

**Remember**: Once evidence is posted to Linear or GitHub, it is permanent. Redact BEFORE posting.

> **CRITICAL WARNING FOR EVIDENCE STORAGE**: Logs, screenshots, gists, and any other evidence
> artifacts MUST be scrubbed for PII and secrets BEFORE posting. This applies to:
> - Terminal output logs (may contain environment variables, paths with usernames)
> - Screenshots (may show sensitive data in editor tabs, terminal history)
> - GitHub Gists (publicly accessible by default)
> - CI/CD logs (may contain build secrets, API tokens)
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

**Unix (Bash)**:
```bash
# =============================================================================
# Toolchain Version Capture (run before verification) - Unix
# =============================================================================
mkdir -p artifacts/release/v0.4.0
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

**Windows (PowerShell)**:
```powershell
# =============================================================================
# Toolchain Version Capture (run before verification) - Windows PowerShell
# =============================================================================
$outFile = "artifacts\release\v0.4.0\00-toolchain-versions.txt"
New-Item -ItemType Directory -Force -Path "artifacts\release\v0.4.0" | Out-Null

"=== Toolchain Versions for Evidence ===" | Tee-Object -FilePath $outFile
"Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') UTC" | Tee-Object -FilePath $outFile -Append
"Commit: $(git rev-parse HEAD)" | Tee-Object -FilePath $outFile -Append
"" | Tee-Object -FilePath $outFile -Append
"Python: $(python --version 2>&1)" | Tee-Object -FilePath $outFile -Append
"Poetry: $(poetry --version 2>&1)" | Tee-Object -FilePath $outFile -Append
"Platform: $([System.Environment]::OSVersion.VersionString) $(if ([System.Environment]::Is64BitOperatingSystem) {'x64'} else {'x86'})" | Tee-Object -FilePath $outFile -Append
"" | Tee-Object -FilePath $outFile -Append
"=== Tool Versions ===" | Tee-Object -FilePath $outFile -Append
poetry run mypy --version 2>&1 | Tee-Object -FilePath $outFile -Append
poetry run pytest --version 2>&1 | Tee-Object -FilePath $outFile -Append
poetry run ruff --version 2>&1 | Tee-Object -FilePath $outFile -Append
poetry run black --version 2>&1 | Tee-Object -FilePath $outFile -Append
poetry run isort --version 2>&1 | Tee-Object -FilePath $outFile -Append
"" | Tee-Object -FilePath $outFile -Append
"=== Dependency Lock Hash ===" | Tee-Object -FilePath $outFile -Append
"$((Get-FileHash -Algorithm SHA256 poetry.lock).Hash.ToLower())  poetry.lock" | Tee-Object -FilePath $outFile -Append
```

**Cross-Platform Command Reference**:

| Command | Unix | Windows PowerShell | Windows CMD |
|---------|-------------|-------------------|-------------|
| Timestamp (UTC) | `date -u '+%Y-%m-%d %H:%M:%S UTC'` | `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'` | `echo %date% %time%` |
| Platform info | `uname -srm` | `[System.Environment]::OSVersion.VersionString` | `ver` |
| SHA256 hash | `sha256sum file` | `(Get-FileHash -Algorithm SHA256 file).Hash` | `certutil -hashfile file SHA256` |
| Tee to file | `cmd \| tee file` | `cmd \| Tee-Object -FilePath file` | No direct equivalent (use `>` redirect) |
| Tee append | `cmd \| tee -a file` | `cmd \| Tee-Object -FilePath file -Append` | No direct equivalent (use `>>` redirect) |
| Create directory | `mkdir -p dir` | `New-Item -ItemType Directory -Force -Path dir` | `mkdir dir` (fails if exists) |
| Activate venv | `source venv/bin/activate` | `.\venv\Scripts\Activate.ps1` | `venv\Scripts\activate.bat` |
| Remove directory | `rm -rf dir` | `Remove-Item -Recurse -Force dir` | `rmdir /s /q dir` |

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

### Final Sign-off Evidence Verification

**CRITICAL**: Before the release manager signs off, verify ALL gates have valid evidence:

- [ ] **All gates have evidence in specified location**
  - Check each gate status in Linear issue comments or artifacts/
  - Verify no gates marked "pending" or "skipped"

- [ ] **All evidence includes required fields**
  - Every evidence item has: timestamp, commit SHA, result, toolchain versions
  - No evidence items missing mandatory fields

- [ ] **Evidence index file updated**
  - File exists: `artifacts/release/v0.4.0/evidence-index.md`
  - All gates listed with evidence links
  - Index is current (no stale links)

---

## 1. Code Quality

- [ ] **All nodes pure-checked (AST)** `✅ REQUIRED`
  - Run AST validation checks on all node implementations
  - **Dedicated Script**: Use `scripts/check_node_purity.py` for comprehensive node purity validation
  - Commands:
    ```bash
    # =============================================================================
    # OPTION A: Use dedicated node purity checker script (RECOMMENDED)
    # =============================================================================
    # This performs comprehensive AST analysis for:
    # - Global state access in COMPUTE nodes
    # - I/O operations in pure nodes
    # - Mutable default arguments
    # - Other purity violations
    poetry run python scripts/check_node_purity.py --verbose

    # For stricter checking (treats warnings as errors)
    poetry run python scripts/check_node_purity.py --strict

    # Check specific file only
    poetry run python scripts/check_node_purity.py --file src/omnibase_core/nodes/node_compute.py

    # JSON output for CI integration
    poetry run python scripts/check_node_purity.py --json

    # =============================================================================
    # OPTION B: Run architecture validation tests
    # =============================================================================
    poetry run pytest tests/unit/validation/ -v -k "ast or architecture or pattern"

    # =============================================================================
    # OPTION C: Run pattern validation programmatically
    # =============================================================================
    poetry run python -c "
    from omnibase_core.validation.patterns import validate_patterns_directory
    from pathlib import Path
    result = validate_patterns_directory(Path('src/omnibase_core/nodes'))
    print(f'Validation complete: {len(result.errors)} issues found')
    for err in result.errors[:10]: print(f'  - {err}')
    "
    ```
  - Expected: 0 violations in node implementations (exit code 0)
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/01-code-quality-ast-check-YYYYMMDD.txt
  - **⚠️ IMPORTANT**: These commands MUST be executed explicitly. Test pass status does NOT constitute evidence.

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
  - No test flakiness retries permitted (pytest-rerunfailures and similar plugins disabled)
  - **Scope of Retry Prohibition**: This prohibition applies specifically to **test execution retries** designed to mask flaky tests:
    - **Prohibited** (test-level retries that mask flakiness):
      - `pytest-rerunfailures` plugin or similar test retry mechanisms
      - `flaky` decorator or equivalent test-specific retry logic
      - `pytest-retry` or equivalent retry plugins
      - CI job retry on test failure without documented root cause analysis and fix
    - **NOT prohibited** (application-level retry logic being tested):
      - Network retry logic within the code under test (e.g., exponential backoff for API calls)
      - Circuit breaker patterns in production code
      - Application-level error recovery and retry mechanisms
      - Resilience patterns designed for production use
    - **NOT prohibited** (infrastructure-level retries):
      - CI infrastructure retries for transient runner failures (GitHub Actions runner crash)
      - Package registry timeout retries (PyPI, npm registry connection failures)
      - Docker pull retries for network issues
  - **Rationale**: Flaky tests indicate non-deterministic behavior that must be fixed at the source. Automatic test retries mask real bugs and create false confidence in test reliability. All tests must be deterministic.
  - **Concrete Example**:
    - ❌ **Prohibited**: `pytest --reruns 3` (retries failing tests 3 times to work around flakiness)
    - ✅ **Allowed**: Testing a function that implements retry logic: `retry_with_backoff(api_call, max_retries=3)`
    - ❌ **Prohibited**: Re-running CI job because "tests are flaky sometimes"
    - ✅ **Allowed**: Re-running CI job after fixing a known infrastructure issue (runner out of disk space)
  - **Note**: Expect pressure to weaken this later. Do not.
  - Expected runtime: 2m30s-3m30s per split
  - Evidence: Release issue comment (OMN-218) with GitHub Actions run link
  - **Evidence Location**: See [Evidence Storage Guidelines](#evidence-storage-guidelines) for storage requirements

- [ ] **Adapter fuzz testing completed** `✅ REQUIRED (MVP minimal)` / `🚫 BLOCKER (Beta full)`
  - **Definition**: Adapters are components that bridge ONEX core with external systems or protocols. Examples in this codebase include: event bus adapters (Kafka/Redpanda backends via `ProtocolKafkaEventBusAdapter`), container adapters (service discovery integration), CLI adapters (`ModelCLIAdapter`), and contract adapters (YAML binding).
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

    # =============================================================================
    # Create adapter fuzz test evidence (COMPLETE runnable example)
    # =============================================================================
    # Prerequisites:
    #   - Hypothesis installed: poetry show hypothesis (should show ^6.148)
    #   - omnibase_core installed: poetry install
    #
    # This example is COMPLETE and copy-paste runnable. It will:
    #   1. Generate 50 random text inputs via Hypothesis
    #   2. Feed each to ModelRuntimeHostContract.model_validate_json()
    #   3. Verify that invalid inputs raise ValidationError (not crash/hang)
    #   4. Print success message when all 50 examples pass
    #
    poetry run python -c "
from hypothesis import given, strategies as st, settings
from omnibase_core.models.contracts.model_runtime_host_contract import ModelRuntimeHostContract
from pydantic import ValidationError
import json
import sys

# Track test execution for verification
examples_tested = 0
errors_caught = 0

@given(st.text(min_size=0, max_size=100))
@settings(max_examples=50, deadline=None)  # deadline=None prevents timeout on slow systems
def test_contract_handles_invalid_input(invalid_data):
    \"\"\"Fuzz test: Contract should gracefully reject invalid input without crashing.\"\"\"
    global examples_tested, errors_caught
    examples_tested += 1
    try:
        # Attempt to parse malformed data - this SHOULD fail validation
        ModelRuntimeHostContract.model_validate_json(json.dumps({'invalid': invalid_data}))
        # If we get here, validation unexpectedly passed (still OK - no crash)
    except ValidationError:
        # Expected - invalid data should raise ValidationError
        errors_caught += 1
    except Exception as e:
        # Unexpected error type - should be ValidationError
        print(f'Unexpected error type: {type(e).__name__}: {e}', file=sys.stderr)
        raise

# CRITICAL: Call the test function to actually execute Hypothesis
# Without this call, Hypothesis does nothing!
test_contract_handles_invalid_input()

# Verify execution completed
print(f'Fuzz test: PASS ({examples_tested} examples tested, {errors_caught} validation errors caught)')
print('All inputs handled gracefully - no crashes or undefined behavior')
print('Implement production tests in tests/unit/adapters/test_adapter_fuzz.py')
sys.exit(0)  # Explicit success exit
"
    # Expected output (exact):
    # Fuzz test: PASS (50 examples tested, N validation errors caught)
    # All inputs handled gracefully - no crashes or undefined behavior
    # Implement production tests in tests/unit/adapters/test_adapter_fuzz.py
    #
    # Where N = number of examples that raised ValidationError (typically most of them)
    #
    # If you see "ModuleNotFoundError: No module named 'hypothesis'":
    #   Run: poetry install (Hypothesis is in pyproject.toml dependencies)
    #
    # If the command hangs or crashes:
    #   This indicates a bug in ModelRuntimeHostContract - investigate!
    #
    # If you see "Unexpected error type: ...":
    #   The contract raised a non-ValidationError exception - investigate!
    ```
  - Expected: All adapters handle malformed inputs gracefully (ValidationError, not crash)
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/fuzz-reports/adapter-fuzz-YYYYMMDD.txt
  - **Gap**: Full adapter fuzz tests need implementation per MVP_PLAN.md Issue 3.8
  - **⚠️ WARNING**: Without explicit MVP/Beta scope, someone will later claim fuzzing was "done" when it was not. The scopes above are enforceable bounds.

- [ ] **Coverage threshold met** `✅ REQUIRED`
  - Minimum: 60% **line coverage** (not branch coverage)
  - **Coverage Type Specification**:
    - **Line coverage** (REQUIRED for v0.4.0): Percentage of executable lines executed by tests
      - Formula: `(executed lines / total executable lines) * 100`
      - Measures: Which lines of code were actually run during tests
      - **This is the enforced metric** for this release
    - **Branch coverage** (NOT required for v0.4.0): Percentage of code branches taken
      - Formula: `(executed branches / total branches) * 100`
      - Measures: Whether both sides of if/else, all loop conditions, etc. were tested
      - Future consideration for Beta scope (v0.5.0+)
  - **Enforcement Mechanism**: pytest-cov with `--cov-fail-under=60` flag
    - **How it works**: pytest-cov compares total line coverage against threshold
    - **CI Behavior**: When coverage < 60%, pytest exits with **non-zero exit code** (exit code 2), causing CI job to FAIL immediately
    - **Local Behavior**: Same exit code behavior allows local validation before push
    - **Cannot Override**: No command-line flag to bypass the threshold; must either:
      1. Add tests to increase coverage to ≥60%, OR
      2. Modify threshold in `pyproject.toml` `[tool.pytest.ini_options]` (requires PR review)
  - **What Happens When Threshold Not Met**:
    1. **Immediate Failure**: CI pipeline fails at coverage check step (exit code 2)
    2. **Detailed Report**: Coverage report shows which files/lines are uncovered (`--cov-report=term-missing`)
    3. **Developer Action Required**: Must add tests or mark intentional exclusions with `# pragma: no cover`
    4. **Hard Gate**: Release CANNOT proceed until threshold is met - this is non-negotiable
    5. **No Workarounds**: Cannot merge PR or tag release until coverage passes
  - Commands:
    ```bash
    # Run with coverage enforcement (CI-equivalent command)
    poetry run pytest tests/ --cov=src/omnibase_core --cov-fail-under=60 --cov-report=term-missing

    # Check current coverage without enforcement (for investigation)
    poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

    # Generate HTML report for detailed file-by-file analysis
    poetry run pytest tests/ --cov=src/omnibase_core --cov-report=html:artifacts/release/v0.4.0/coverage/

    # View coverage summary only (faster, no detailed report)
    poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term
    ```
  - Expected: Coverage >= 60% (exit code 0), coverage report generated
  - **Note**: Coverage is not correctness. This metric prevents metric worship—60% is a floor, not a goal. High coverage with bad tests is worse than moderate coverage with good tests.
  - Evidence: Release issue comment (OMN-218) with CI artifacts link or artifacts/release/v0.4.0/coverage/index.html
  - **Evidence Location**: See [Evidence Storage Guidelines](#evidence-storage-guidelines) for storage requirements

- [ ] **Negative-path tests present** `✅ REQUIRED`
  - At least one failure-mode test per contract class
  - Explicit assertions on error shape
  - Evidence: Release issue comment (OMN-218) with specific test file paths (e.g., tests/unit/test_negative_paths.py)
  - **Evidence Location**: See [Evidence Storage Guidelines](#evidence-storage-guidelines) for storage requirements

---

## 3. Determinism & Replayability

- [ ] **Deterministic execution verified** `🚫 BLOCKER`
  - Identical inputs produce identical outputs
  - Hash comparison of emitted ModelActions or events
  - **Hash Scope Definition**: Hashes are computed over **canonicalized outputs**. The following are EXCLUDED from hash computation:
    - **Timestamps** (creation time, modification time, execution time) - *Rationale: Change on every execution even with identical inputs; not part of functional behavior*
    - **UUIDs generated at runtime** (correlation_id, trace_id, request_id) - *Rationale: Unique per request for observability; not part of business logic output*
    - **Dict ordering noise** (canonicalize with sorted keys) - *Rationale: Python dict ordering is implementation detail, not semantic*
    - **Floating-point precision beyond 6 decimal places** - *Rationale: Platform-specific floating-point representation differences; 6 decimals sufficient for business logic*
  - **Hash Inclusion**: The following MUST be included in hashes:
    - All business logic outputs (computed values, transformed data)
    - State transitions (FSM states, workflow phases)
    - Error codes and error messages
    - Contract fingerprints

  - **Canonicalization Example**: The following snippet demonstrates how to canonicalize output data for deterministic hashing:

    ```python
    import hashlib
    import json
    from datetime import datetime
    from uuid import UUID

    # Fields excluded from hash computation (volatile/non-deterministic)
    # WHY EACH FIELD IS EXCLUDED:
    # - Timestamps: Change on every execution even with identical inputs
    # - UUIDs/IDs: Generated uniquely per request, not part of business logic
    # - Trace IDs: Observability-only, not functional behavior
    EXCLUDED_FIELDS = frozenset({
        # Time-based fields (different on every run)
        "timestamp", "created_at", "modified_at", "execution_time",
        # Runtime-generated identifiers (unique per request)
        "correlation_id", "trace_id", "request_id", "uuid"
    })

    def canonicalize_for_hash(data: dict) -> str:
        """Canonicalize data for deterministic hashing.

        Applies ONEX canonicalization rules:
        - Excludes timestamps and runtime-generated UUIDs
        - Sorts dict keys alphabetically (recursive)
        - Limits float precision to 6 decimal places
        - Removes None values
        """
        def _clean(obj: object) -> object:
            if isinstance(obj, dict):
                return {
                    k: _clean(v)
                    for k, v in sorted(obj.items())
                    if k not in EXCLUDED_FIELDS and v is not None
                }
            if isinstance(obj, (datetime, UUID)):
                return None  # Excluded from hash
            if isinstance(obj, float):
                return round(obj, 6)  # 6 decimal precision
            if isinstance(obj, list):
                return [_clean(item) for item in obj if item is not None]
            return obj

        cleaned = _clean(data)
        # Compact JSON with sorted keys for determinism
        return json.dumps(cleaned, sort_keys=True, separators=(",", ":"))

    def compute_output_hash(output_data: dict) -> str:
        """Compute SHA256 hash of canonicalized output."""
        canonical_str = canonicalize_for_hash(output_data)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    # Usage example
    output = {
        "result": 42.123456789,  # Will be rounded to 42.123457
        "state": "completed",
        "items": [{"name": "b"}, {"name": "a"}],
        "timestamp": "2025-01-01T00:00:00Z",  # Excluded
        "correlation_id": "abc-123",  # Excluded
    }
    output_hash = compute_output_hash(output)
    # Hash is deterministic: same output always produces same hash
    ```

    **Note**: For contract fingerprinting, use the existing utilities:
    ```python
    from omnibase_core.contracts.contract_hash_registry import (
        normalize_contract,
        compute_contract_fingerprint,
    )

    fingerprint = compute_contract_fingerprint(contract_model)
    # Returns: ModelContractFingerprint with version and hash_prefix
    ```

  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/replay-logs/determinism-hashes-YYYYMMDD.txt
  - **Evidence Location**: See [Evidence Storage Guidelines](#evidence-storage-guidelines) for storage requirements

- [ ] **Replay validation completed** `✅ REQUIRED`
  - At least one representative workflow replayed end-to-end
  - Replay output matches original execution exactly
  - **⚠️ REQUIRED**: At least ONE orchestrator-heavy replay (not just compute-only)
    - Must include: Multiple node transitions, state reduction, at least one retry/recovery path
    - Compute-only replays are the easy case and do not catch real bugs
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/replay-logs/replay-comparison-YYYYMMDD.txt
  - **Evidence Location**: See [Evidence Storage Guidelines](#evidence-storage-guidelines) for storage requirements

---

## 4. Contracts & Architecture

- [ ] **All contracts have valid fingerprints** `✅ REQUIRED`
  - Every RuntimeHostContract YAML includes a fingerprint
  - Fingerprints verified against contract content
  - **Note**: All scripts exist and are fully functional (verified 2025-12-15)

  **Script Capability Reference**:

  | Script | `--recursive` Flag | File Discovery | Status |
  |--------|-------------------|----------------|--------|
  | `scripts/check_node_purity.py` | No (single file via `--file`) | Scans `src/omnibase_core` by default | ✅ Exists |
  | `scripts/compute_contract_fingerprint.py` | No | Relies on shell glob expansion | ✅ Exists |
  | `scripts/regenerate_fingerprints.py` | Yes (`-r`, `--recursive`) | Internal Python `rglob()` | ✅ Exists |
  | `scripts/lint_contract.py` | Yes (`-r`, `--recursive`) | Internal Python `rglob()` | ✅ Exists |

  **Module Path Reference**:

  | Module | Expected Path | Status |
  |--------|--------------|--------|
  | Pattern validation | `omnibase_core.validation.patterns.validate_patterns_directory()` | ✅ Exists |
  | Hash registry | `omnibase_core.contracts.contract_hash_registry.compute_contract_fingerprint()` | ✅ Exists |
  | Hash registry | `omnibase_core.contracts.contract_hash_registry.normalize_contract()` | ✅ Exists |
  | Hash registry class | `omnibase_core.contracts.contract_hash_registry.ContractHashRegistry` | ✅ Exists |

  **Cross-Platform Glob Expansion Notes**:
  - Shell glob patterns (`*.yaml`, `**/*.yaml`) are expanded by the shell BEFORE Python sees them
  - On **Unix (Bash/Zsh)**: Handle `**/*.yaml` recursively (requires `shopt -s globstar` in Bash)
  - On **Windows CMD**: Glob expansion does NOT work - patterns passed literally to Python
  - On **Windows PowerShell**: Use `Get-ChildItem -Recurse -Filter *.yaml | ForEach-Object { ... }`
  - **Recommendation**: Prefer scripts with `--recursive` flag for cross-platform compatibility

  - Commands:
    ```bash
    # =============================================================================
    # OPTION A: Cross-platform commands (RECOMMENDED)
    # These use --recursive flag and work identically on all platforms
    # =============================================================================

    # Check if any fingerprints need regeneration (dry-run)
    # regenerate_fingerprints.py supports --recursive - handles file discovery internally
    poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive --dry-run

    # Lint all contracts (includes fingerprint validation)
    # lint_contract.py supports --recursive - handles file discovery internally
    poetry run python scripts/lint_contract.py contracts/ --recursive --verbose

    # =============================================================================
    # OPTION B: Unix only (shell glob expansion)
    # compute_contract_fingerprint.py does NOT support --recursive
    # These commands rely on shell glob expansion before Python sees the arguments
    # =============================================================================

    # Validate runtime contract fingerprints (requires shell glob expansion)
    # Note: In Bash, you may need: shopt -s globstar (for ** patterns)
    poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/*.yaml --validate

    # Validate example contract fingerprints recursively (Unix shells only)
    poetry run python scripts/compute_contract_fingerprint.py examples/contracts/**/*.yaml --validate

    # =============================================================================
    # OPTION C: Windows alternatives
    # =============================================================================

    # Windows CMD - use for loop (single directory only):
    # for %f in (contracts\runtime\*.yaml) do poetry run python scripts/compute_contract_fingerprint.py %f --validate

    # Windows PowerShell - recursive with pipeline:
    # Get-ChildItem -Path contracts -Recurse -Filter *.yaml | ForEach-Object { poetry run python scripts/compute_contract_fingerprint.py $_.FullName --validate }

    # Windows (any shell) - use scripts with --recursive flag instead (RECOMMENDED):
    # poetry run python scripts/lint_contract.py contracts/ --recursive --verbose
    ```
  - Expected: All fingerprints valid (exit code 0), no regeneration needed
  - Evidence: Release issue comment (OMN-218) or artifacts/release/v0.4.0/fingerprints/fingerprint-verification-YYYYMMDD.txt

- [ ] **Fingerprint enforcement validated** `🚫 BLOCKER`
  - Modified contract fails verification
  - No fallback or silent acceptance
  - **🚫 PROHIBITION**: Runtime fingerprint regeneration is FORBIDDEN. Future contributors will try to be "helpful" by auto-regenerating fingerprints. This defeats the purpose of fingerprints as drift detection.
  - Commands:
    ```bash
    # Method 1: Use regenerate_fingerprints in dry-run mode to detect drift
    # Exit code 1 indicates fingerprints would change (drift detected)
    poetry run python scripts/regenerate_fingerprints.py contracts/runtime/ --recursive --dry-run

    # Method 2: Programmatic test showing fingerprint drift detection
    poetry run python -c "
    from pathlib import Path
    from omnibase_core.contracts.contract_hash_registry import compute_contract_fingerprint
    from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
    import yaml
    import copy

    # Load a real contract
    contract_path = Path('examples/contracts/compute/user_profile_normalizer.yaml')
    original_data = yaml.safe_load(contract_path.read_text())
    original_fp = original_data.get('fingerprint', '')

    # Validate and compute fingerprint for original
    original_contract = ModelYamlContract.model_validate(original_data)
    computed_fp = compute_contract_fingerprint(original_contract)
    print(f'Declared fingerprint: {original_fp}')
    print(f'Computed fingerprint: {computed_fp}')
    print(f'Match: {original_fp == str(computed_fp)}')

    # Modify content and verify drift detection
    modified_data = copy.deepcopy(original_data)
    modified_data['metadata']['description'] = 'MODIFIED FOR TEST'
    del modified_data['fingerprint']  # Remove fingerprint to recompute
    modified_contract = ModelYamlContract.model_validate(modified_data)
    modified_fp = compute_contract_fingerprint(modified_contract)
    print(f'After modification:   {modified_fp}')
    print(f'Drift detected: {original_fp != str(modified_fp)}')
    assert original_fp != str(modified_fp), 'Fingerprint should change when contract modified'
    print('✅ Fingerprint enforcement working correctly')
    "
    ```
  - Expected: Modification causes fingerprint mismatch (drift detected)
  - Evidence: Release issue comment (OMN-218) with test output showing fingerprint validation failure

- [ ] **All nodes are contract-driven** `✅ REQUIRED`
  - No legacy node implementations remain
  - **Preferred** (ripgrep): `rg "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/`
  - **Alternative** (portable grep with extended regex): `grep -rE "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/`
  - **Note**: The `-E` flag enables extended regex (required for `|` alternation). Basic `grep -r` without `-E` will not match correctly.
  - **grep/rg Exit Codes** (important for scripting and CI):
    - Exit 0: Matches found (FAILURE for this check - legacy patterns still exist)
    - Exit 1: No matches found (SUCCESS for this check - no legacy patterns remain)
    - Exit 2: Error occurred (investigate - file not found, permission denied, etc.)
  - Expected: Empty output with exit code 1 (no matches = success for legacy pattern removal verification)
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

  **What is "lock drift"?**: Lock drift occurs when:
  1. `poetry.lock` is modified but not committed (uncommitted changes)
  2. `poetry.lock` is out of sync with `pyproject.toml` (dependencies added/removed without running `poetry lock`)
  3. Lock file was regenerated on a different platform/Poetry version (hash changes without intentional dependency updates)
  - Commands:

    **Unix (Bash)**:
    ```bash
    # =============================================================================
    # Step 1: Detect uncommitted changes to lock file
    # =============================================================================
    # Check for unstaged changes (should be empty)
    git diff --name-only poetry.lock

    # Check for staged but uncommitted changes (should be empty)
    git diff --cached --name-only poetry.lock

    # Combined check with status
    git status poetry.lock

    # =============================================================================
    # Step 2: Verify lock file is in sync with pyproject.toml
    # =============================================================================
    # Poetry 2.x command (CORRECT for Poetry >= 2.0):
    poetry check --lock
    # Expected output: "All set!"
    # Exit code 0 = in sync, Exit code 1 = out of sync

    # NOTE: For Poetry 1.x (deprecated), the command was `poetry lock --check`
    # This project requires Poetry 2.x - verify with: poetry --version

    # =============================================================================
    # Step 3: Capture lock file hash for evidence
    # =============================================================================
    sha256sum poetry.lock >> artifacts/release/v0.4.0/07-dependencies-lock-hash.txt
    echo "Lock hash captured at $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> artifacts/release/v0.4.0/07-dependencies-lock-hash.txt

    # =============================================================================
    # Step 4: Verify lock file is tracked in git
    # =============================================================================
    git ls-files --error-unmatch poetry.lock  # Exit 0 = tracked
    git log -1 --format="%h %s" -- poetry.lock  # Show last commit
    ```

    **Windows (PowerShell)**:
    ```powershell
    # =============================================================================
    # Step 1: Detect uncommitted changes to lock file
    # =============================================================================
    git diff --name-only poetry.lock
    git diff --cached --name-only poetry.lock
    git status poetry.lock

    # =============================================================================
    # Step 2: Verify lock file is in sync with pyproject.toml
    # =============================================================================
    # Poetry 2.x command (CORRECT for Poetry >= 2.0):
    poetry check --lock
    # Expected output: "All set!"

    # =============================================================================
    # Step 3: Capture lock file hash for evidence
    # =============================================================================
    $hash = (Get-FileHash -Algorithm SHA256 poetry.lock).Hash.ToLower()
    "$hash  poetry.lock" >> artifacts\release\v0.4.0\07-dependencies-lock-hash.txt
    "Lock hash captured at $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')" >> artifacts\release\v0.4.0\07-dependencies-lock-hash.txt

    # =============================================================================
    # Step 4: Verify lock file is tracked in git
    # =============================================================================
    git ls-files --error-unmatch poetry.lock
    git log -1 --format="%h %s" -- poetry.lock
    ```

    **Windows (CMD)**:
    ```cmd
    :: =============================================================================
    :: Step 1: Detect uncommitted changes to lock file
    :: =============================================================================
    git diff --name-only poetry.lock
    git diff --cached --name-only poetry.lock
    git status poetry.lock

    :: =============================================================================
    :: Step 2: Verify lock file is in sync with pyproject.toml
    :: =============================================================================
    :: Poetry 2.x command (CORRECT for Poetry >= 2.0):
    poetry check --lock
    :: Expected output: "All set!"

    :: =============================================================================
    :: Step 3: Capture lock file hash for evidence
    :: =============================================================================
    certutil -hashfile poetry.lock SHA256 >> artifacts\release\v0.4.0\07-dependencies-lock-hash.txt

    :: =============================================================================
    :: Step 4: Verify lock file is tracked in git
    :: =============================================================================
    git ls-files --error-unmatch poetry.lock
    git log -1 --format="%h %s" -- poetry.lock
    ```

  - **Drift Detection Summary**:

    | Check | Command | Expected Result |
    |-------|---------|-----------------|
    | Uncommitted changes | `git diff --name-only poetry.lock` | Empty output |
    | Staged changes | `git diff --cached --name-only poetry.lock` | Empty output |
    | Lock/pyproject sync | `poetry check --lock` | "All set!" (exit 0) |
    | File tracked | `git ls-files --error-unmatch poetry.lock` | Exit 0 |
    | Silent re-lock drift | Compare hash with previous release | Hash matches OR change documented |

  - **Silent Re-Lock Drift Detection**:

    Silent re-lock drift occurs when `poetry lock` regenerates the lock file with different package hashes
    even though no dependencies were intentionally changed. This can happen when:
    - Different Poetry versions produce different lock file formats
    - Package indexes return slightly different metadata
    - Transitive dependency resolution produces different (but valid) solutions

    **Detection Commands**:

    **Unix (Bash)**:
    ```bash
    # =============================================================================
    # Step 1: Capture current lock file hash
    # =============================================================================
    CURRENT_HASH=$(sha256sum poetry.lock | cut -d' ' -f1)
    echo "Current lock hash: $CURRENT_HASH"

    # =============================================================================
    # Step 2: Compare with last tagged release (e.g., v0.3.6)
    # =============================================================================
    # Get hash from the last release tag
    PREVIOUS_HASH=$(git show v0.3.6:poetry.lock 2>/dev/null | sha256sum | cut -d' ' -f1)
    echo "Previous release hash (v0.3.6): $PREVIOUS_HASH"

    # =============================================================================
    # Step 3: Compare hashes
    # =============================================================================
    if [ "$CURRENT_HASH" = "$PREVIOUS_HASH" ]; then
        echo "PASS: Lock file unchanged from v0.3.6 - no drift"
    else
        echo "WARNING: Lock file hash changed from v0.3.6"
        echo "Verify this is intentional by checking git log for dependency changes:"
        git log --oneline v0.3.6..HEAD -- pyproject.toml poetry.lock | head -10
        echo ""
        echo "If no intentional changes, this may be re-lock drift. Investigate before release."
    fi

    # =============================================================================
    # Step 4: Verify no uncommitted poetry.lock changes after fresh lock
    # =============================================================================
    # This detects if running 'poetry lock' would change the committed file
    # NOTE: This modifies poetry.lock temporarily - stash any local changes first
    cp poetry.lock poetry.lock.backup
    poetry lock --no-update  # Re-resolve without updating packages
    if diff -q poetry.lock poetry.lock.backup > /dev/null 2>&1; then
        echo "PASS: poetry lock --no-update produces identical file - no drift"
    else
        echo "WARNING: poetry lock --no-update produces different file - potential re-lock drift"
        diff poetry.lock poetry.lock.backup | head -20
    fi
    mv poetry.lock.backup poetry.lock  # Restore original
    ```

    **Windows (PowerShell)**:
    ```powershell
    # =============================================================================
    # Step 1: Capture current lock file hash
    # =============================================================================
    $currentHash = (Get-FileHash -Algorithm SHA256 poetry.lock).Hash.ToLower()
    Write-Host "Current lock hash: $currentHash"

    # =============================================================================
    # Step 2: Compare with last tagged release
    # =============================================================================
    $previousContent = git show v0.3.6:poetry.lock 2>$null
    if ($previousContent) {
        $previousHash = [System.BitConverter]::ToString(
            [System.Security.Cryptography.SHA256]::Create().ComputeHash(
                [System.Text.Encoding]::UTF8.GetBytes($previousContent -join "`n")
            )
        ).Replace("-", "").ToLower()
        Write-Host "Previous release hash (v0.3.6): $previousHash"

        # Compare
        if ($currentHash -eq $previousHash) {
            Write-Host "PASS: Lock file unchanged from v0.3.6 - no drift"
        } else {
            Write-Host "WARNING: Lock file hash changed from v0.3.6"
            git log --oneline v0.3.6..HEAD -- pyproject.toml poetry.lock | Select-Object -First 10
        }
    }
    ```

    **Acceptable Drift Scenarios** (document in evidence):
    - Intentional dependency update (commit message references package change)
    - Security patch update (CVE documented)
    - Poetry version upgrade (documented in release notes)

    **Unacceptable Drift** (blocks release):
    - Hash changed with no corresponding pyproject.toml change
    - No commit message explaining dependency change
    - Multiple transitive dependency changes without root cause

  - Evidence: Git diff output (should be empty) AND lock file hash AND `poetry check --lock` output AND re-lock drift comparison result

- [ ] **Reproducible install verified** `✅ REQUIRED`
  - **⚠️ REQUIRED**: Fresh virtualenv smoke install (pip installs can lie)
  - Fresh environment install using lockfile only
  - Tests pass in clean environment
  - Commands:

    **Unix (Bash)**:
    ```bash
    # Create fresh virtualenv for verification
    # Uses TMPDIR if set, falls back to /tmp
    VERIFY_DIR="${TMPDIR:-/tmp}/v040-verify-env"
    python -m venv "$VERIFY_DIR"
    source "$VERIFY_DIR/bin/activate"

    # Install from lock file only
    pip install poetry
    poetry install --no-root

    # Run smoke tests
    python -c "from omnibase_core.nodes import NodeCompute; print('Smoke OK')"
    poetry run pytest tests/unit/ -x --tb=short -q

    # Cleanup
    deactivate
    rm -rf "$VERIFY_DIR"
    ```

    **Windows (PowerShell)**:
    ```powershell
    # Create fresh virtualenv for verification
    python -m venv $env:TEMP\v040-verify-env
    & "$env:TEMP\v040-verify-env\Scripts\Activate.ps1"

    # Install from lock file only
    pip install poetry
    poetry install --no-root

    # Run smoke tests
    python -c "from omnibase_core.nodes import NodeCompute; print('Smoke OK')"
    poetry run pytest tests/unit/ -x --tb=short -q

    # Cleanup
    deactivate
    Remove-Item -Recurse -Force "$env:TEMP\v040-verify-env"
    ```

    **Windows (CMD)**:
    ```cmd
    :: Create fresh virtualenv for verification
    python -m venv %TEMP%\v040-verify-env
    %TEMP%\v040-verify-env\Scripts\activate.bat

    :: Install from lock file only
    pip install poetry
    poetry install --no-root

    :: Run smoke tests
    python -c "from omnibase_core.nodes import NodeCompute; print('Smoke OK')"
    poetry run pytest tests/unit/ -x --tb=short -q

    :: Cleanup
    deactivate
    rmdir /s /q %TEMP%\v040-verify-env
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
    from omnibase_core.errors.error_declarative import NodeExecutionError
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
    from omnibase_core.constants.constants_event_types import NODE_FAILURE, NODE_SUCCESS, NODE_START
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
> | Platform | Temporary Directory | Example |
> |----------|---------------------|---------|
> | Linux | `${TMPDIR:-/tmp}` | `cd ${TMPDIR:-/tmp}` |
> | macOS | `${TMPDIR:-/tmp}` | `cd ${TMPDIR:-/tmp}` |
> | Windows (PowerShell) | `$env:TEMP` | `cd $env:TEMP` |
> | Windows (CMD) | `%TEMP%` | `cd %TEMP%` |
> | Project-local (any OS) | `./tmp` or `../_downstream_test` | `mkdir -p ../_downstream_test && cd ../_downstream_test` |
> **Recommendation**: Use project-local directories (e.g., `../_downstream_test`) for better reproducibility and easier cleanup. These directories should be added to `.gitignore`.

### 9.1 Public API Stability

- [ ] **Public API exports unchanged or documented** `✅ REQUIRED`
  - **Time**: 5 minutes
  - **Purpose**: Verify public API surface is stable and wildcard imports work
  - **Verification Steps**:
    1. Capture current API exports to artifact file
    2. Compare with v0.3.x baseline (if available)
    3. Test wildcard import functionality
    4. Verify all documented imports resolve
  - **Commands**:

    **Unix (Bash)**:
    ```bash
    # =============================================================================
    # Step 1: Capture current API exports for evidence
    # =============================================================================
    mkdir -p artifacts/release/v0.4.0
    poetry run python -c "from omnibase_core.nodes import __all__; print('\\n'.join(sorted(__all__)))" > artifacts/release/v0.4.0/09-api-exports.txt

    # =============================================================================
    # Step 2: Show count and sample (for inline evidence)
    # =============================================================================
    export_count=$(poetry run python -c "from omnibase_core.nodes import __all__; print(len(__all__))")
    echo "Export count: ${export_count}"
    echo "Sample exports:"
    head -5 artifacts/release/v0.4.0/09-api-exports.txt

    # =============================================================================
    # Step 3: Verify wildcard import works
    # =============================================================================
    poetry run python -c "from omnibase_core.nodes import *; print('✅ Wildcard import: PASS')"

    # =============================================================================
    # Step 4: Test critical imports explicitly
    # =============================================================================
    poetry run python -c "
from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect
from omnibase_core.nodes import ModelComputeInput, ModelReducerInput, ModelOrchestratorInput
print('✅ Critical imports: PASS')
"
    ```

    **Windows (PowerShell)**:
    ```powershell
    # =============================================================================
    # Step 1: Capture current API exports for evidence
    # =============================================================================
    New-Item -ItemType Directory -Force -Path "artifacts\release\v0.4.0" | Out-Null
    poetry run python -c "from omnibase_core.nodes import __all__; print('\\n'.join(sorted(__all__)))" | Out-File -Encoding utf8 artifacts\release\v0.4.0\09-api-exports.txt

    # =============================================================================
    # Step 2: Show count and sample
    # =============================================================================
    $exportCount = poetry run python -c "from omnibase_core.nodes import __all__; print(len(__all__))"
    Write-Host "Export count: $exportCount"
    Write-Host "Sample exports:"
    Get-Content artifacts\release\v0.4.0\09-api-exports.txt -Head 5

    # =============================================================================
    # Step 3: Verify wildcard import works
    # =============================================================================
    poetry run python -c "from omnibase_core.nodes import *; print('✅ Wildcard import: PASS')"

    # =============================================================================
    # Step 4: Test critical imports explicitly
    # =============================================================================
    poetry run python -c @"
from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect
from omnibase_core.nodes import ModelComputeInput, ModelReducerInput, ModelOrchestratorInput
print('✅ Critical imports: PASS')
"@
    ```

  - **Expected Results**:
    - Export count > 0 (should be ~15-20 exports)
    - Wildcard import prints "✅ Wildcard import: PASS"
    - All critical imports succeed without ImportError
    - File `artifacts/release/v0.4.0/09-api-exports.txt` created with sorted export list

  - **Pass/Fail Criteria**:
    - ✅ **PASS**: All imports succeed, export count > 0, no ImportError
    - ❌ **FAIL**: Any ImportError, export count = 0, or missing exports

  - **Evidence**: Release issue comment (OMN-218) with:
    - Export count
    - Sample exports (first 5 lines)
    - Confirmation of wildcard import success
    - Link to full export list in artifacts/release/v0.4.0/09-api-exports.txt

- [ ] **Core import paths verified** `✅ REQUIRED`
  - **Time**: 3 minutes
  - **Purpose**: Verify all documented import paths resolve correctly
  - **Commands**:

    **Cross-platform (works on all platforms)**:
    ```bash
    # Test each documented import path
    poetry run python -c "from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect; print('✅ Node imports: PASS')"
    poetry run python -c "from omnibase_core.models.container.model_onex_container import ModelONEXContainer; print('✅ Container import: PASS')"
    poetry run python -c "from omnibase_core.models.errors.model_onex_error import ModelOnexError; print('✅ Error import: PASS')"
    poetry run python -c "from omnibase_core.enums import EnumNodeKind, EnumNodeType; print('✅ Enum imports: PASS')"
    ```

  - **Expected Results**:
    - All commands print "✅ ... : PASS"
    - No ImportError, ModuleNotFoundError, or AttributeError

  - **Pass/Fail Criteria**:
    - ✅ **PASS**: All 4 import commands succeed
    - ❌ **FAIL**: Any import command fails with error

  - **Evidence**: Command outputs (all four commands)

- [ ] **Breaking changes enumerated** `✅ REQUIRED`
  - **Time**: 10 minutes (review CHANGELOG + code)
  - **Purpose**: Ensure all breaking changes are documented for downstream migration
  - **Verification Steps**:
    1. Review CHANGELOG.md for breaking changes section
    2. Verify each breaking change has migration instructions
    3. Check for removed/renamed exports, changed signatures, removed classes
  - **Commands**:
    ```bash
    # Check CHANGELOG.md for breaking changes section
    grep -A 20 "## Breaking Changes" CHANGELOG.md

    # Search for removed classes (example - adjust pattern as needed)
    git log --all --full-history --source --format="%H %s" -- "**/NodeReducerDeclarative*" | head -5
    ```

  - **Expected Results**:
    - CHANGELOG.md has "Breaking Changes" section with explicit list
    - Each breaking change includes migration path
    - All removed exports documented

  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Breaking changes section exists, all changes documented
    - ❌ **FAIL**: No breaking changes section OR undocumented removals

  - **Evidence**: CHANGELOG.md breaking changes section with explicit list

### 9.2 Downstream Repository Testing

- [ ] **omnibase_spi compatibility verified** `🚫 BLOCKER`
  - **Time**: 15-20 minutes (includes clone, install, test, mypy)
  - **Purpose**: Verify SPI repository works with v0.4.0 core dependency
  - **Verification Steps**:
    1. Clone omnibase_spi to isolated directory
    2. Update omnibase_core dependency to v0.4.0 (or local editable)
    3. Run full test suite (pytest)
    4. Run type checking (mypy)
    5. Verify 0 failures and 0 errors
  - **Commands**:

    **Option A: Project-local directory (Recommended - works on all platforms)**
    ```bash
    # =============================================================================
    # Step 1: Setup isolated test environment
    # =============================================================================
    # From omnibase_core root directory
    mkdir -p ../_downstream_test && cd ../_downstream_test

    # =============================================================================
    # Step 2: Clone omnibase_spi
    # =============================================================================
    git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi

    # =============================================================================
    # Step 3: Update omnibase_core dependency to v0.4.0
    # =============================================================================
    # Use absolute path to omnibase_core for editable install
    poetry add "$(cd ../../omnibase_core && pwd)" --editable  # or: poetry add omnibase_core==0.4.0

    # =============================================================================
    # Step 4: Run full test suite
    # =============================================================================
    poetry run pytest tests/ --tb=short -v 2>&1 | tee ../omnibase_spi_test_results.txt

    # =============================================================================
    # Step 5: Run type checking
    # =============================================================================
    poetry run mypy src/ 2>&1 | tee ../omnibase_spi_mypy_results.txt

    # =============================================================================
    # Step 6: Extract results for evidence
    # =============================================================================
    echo "=== TEST SUMMARY ==="
    tail -10 ../omnibase_spi_test_results.txt | grep -E "(passed|failed|error)"
    echo "=== MYPY SUMMARY ==="
    tail -5 ../omnibase_spi_mypy_results.txt

    # =============================================================================
    # Cleanup when done
    # =============================================================================
    # cd ../.. && rm -rf _downstream_test
    ```

    **Option B: Unix system temp**
    ```bash
    # Get absolute path to omnibase_core BEFORE changing directories
    OMNIBASE_CORE_PATH="$(cd /path/to/omnibase_core && pwd)"
    # Or if you're currently in omnibase_core:
    # OMNIBASE_CORE_PATH="$(pwd)"

    cd "${TMPDIR:-/tmp}" && git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi
    poetry add "$OMNIBASE_CORE_PATH" --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/ --tb=short -v | tee "${TMPDIR:-/tmp}/omnibase_spi_test.txt"
    poetry run mypy src/ | tee "${TMPDIR:-/tmp}/omnibase_spi_mypy.txt"
    ```

    **Option C: Windows PowerShell**
    ```powershell
    # Get absolute path to omnibase_core BEFORE changing directories
    $OmnibaseCoreAbsPath = (Get-Location).Path  # If currently in omnibase_core
    # Or specify explicitly:
    # $OmnibaseCoreAbsPath = (Resolve-Path "C:\path\to\omnibase_core").Path

    cd $env:TEMP
    git clone https://github.com/OmniNode-ai/omnibase_spi.git
    cd omnibase_spi
    poetry add $OmnibaseCoreAbsPath --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/ --tb=short -v | Tee-Object -FilePath "$env:TEMP\omnibase_spi_test.txt"
    poetry run mypy src/ | Tee-Object -FilePath "$env:TEMP\omnibase_spi_mypy.txt"
    ```

  - **Expected Results**:
    - pytest: "X passed" (X > 0), **0 failed**
    - mypy: "Success: no issues found" OR "Found 0 errors"
    - No ImportError, ModuleNotFoundError, or missing dependency errors

  - **Pass/Fail Criteria**:
    - ✅ **PASS**: 0 test failures AND 0 mypy errors
    - ❌ **FAIL**: Any test failures OR any mypy errors

  - **Evidence**: Test output with pass count AND mypy report (both stored in artifacts or issue comment)

- [ ] **omninode_core compatibility verified** (if applicable) `✅ REQUIRED`
  - **Time**: 15-20 minutes (includes clone, install, test, mypy)
  - **Purpose**: Verify omninode_core works with v0.4.0 core dependency
  - **Verification Steps** (same as omnibase_spi, different repo):
    1. Clone omninode_core to isolated directory
    2. Update omnibase_core dependency to v0.4.0
    3. Run full test suite (pytest)
    4. Run type checking (mypy)
    5. Verify 0 failures and 0 errors
  - **Commands**:

    **Option A: Project-local directory (Recommended - works on all platforms)**
    ```bash
    # =============================================================================
    # Step 1: Setup isolated test environment
    # =============================================================================
    # From omnibase_core root directory
    mkdir -p ../_downstream_test && cd ../_downstream_test

    # =============================================================================
    # Step 2: Clone omninode_core
    # =============================================================================
    git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core

    # =============================================================================
    # Step 3: Update omnibase_core dependency to v0.4.0
    # =============================================================================
    # Use absolute path to omnibase_core for editable install
    poetry add "$(cd ../../omnibase_core && pwd)" --editable  # or: poetry add omnibase_core==0.4.0

    # =============================================================================
    # Step 4: Run full test suite
    # =============================================================================
    poetry run pytest tests/ --tb=short -v 2>&1 | tee ../omninode_core_test_results.txt

    # =============================================================================
    # Step 5: Run type checking
    # =============================================================================
    poetry run mypy src/ 2>&1 | tee ../omninode_core_mypy_results.txt

    # =============================================================================
    # Step 6: Extract results for evidence
    # =============================================================================
    echo "=== TEST SUMMARY ==="
    tail -10 ../omninode_core_test_results.txt | grep -E "(passed|failed|error)"
    echo "=== MYPY SUMMARY ==="
    tail -5 ../omninode_core_mypy_results.txt

    # =============================================================================
    # Cleanup when done
    # =============================================================================
    # cd ../.. && rm -rf _downstream_test
    ```

    **Option B: Unix system temp**
    ```bash
    # Get absolute path to omnibase_core BEFORE changing directories
    OMNIBASE_CORE_PATH="$(cd /path/to/omnibase_core && pwd)"
    # Or if you're currently in omnibase_core:
    # OMNIBASE_CORE_PATH="$(pwd)"

    cd "${TMPDIR:-/tmp}" && git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core
    poetry add "$OMNIBASE_CORE_PATH" --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/ --tb=short -v | tee "${TMPDIR:-/tmp}/omninode_core_test.txt"
    poetry run mypy src/ | tee "${TMPDIR:-/tmp}/omninode_core_mypy.txt"
    ```

    **Option C: Windows PowerShell**
    ```powershell
    # Get absolute path to omnibase_core BEFORE changing directories
    $OmnibaseCoreAbsPath = (Get-Location).Path  # If currently in omnibase_core
    # Or specify explicitly:
    # $OmnibaseCoreAbsPath = (Resolve-Path "C:\path\to\omnibase_core").Path

    cd $env:TEMP
    git clone https://github.com/OmniNode-ai/omninode_core.git
    cd omninode_core
    poetry add $OmnibaseCoreAbsPath --editable  # or: poetry add omnibase_core==0.4.0
    poetry run pytest tests/ --tb=short -v | Tee-Object -FilePath "$env:TEMP\omninode_core_test.txt"
    poetry run mypy src/ | Tee-Object -FilePath "$env:TEMP\omninode_core_mypy.txt"
    ```

  - **Expected Results**:
    - pytest: "X passed" (X > 0), **0 failed**
    - mypy: "Success: no issues found" OR "Found 0 errors"

  - **Pass/Fail Criteria**:
    - ✅ **PASS**: 0 test failures AND 0 mypy errors
    - ❌ **FAIL**: Any test failures OR any mypy errors

  - **Evidence**: Test output and mypy report

- [ ] **Example projects verified** (if applicable) `📋 INFORMATIONAL`
  - **Time**: 5-10 minutes
  - **Purpose**: Verify official example projects run with v0.4.0
  - **Commands** (example - adjust based on actual example projects):
    ```bash
    # If example projects exist in examples/ directory
    cd examples/basic_compute_node
    poetry add omnibase_core==0.4.0
    poetry run python main.py  # or equivalent
    ```
  - **Expected Results**: No runtime errors on documented examples
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Examples run without runtime errors
    - ❌ **INFORMATIONAL ONLY**: Document failure, proceed with release
  - **Evidence**: Example execution logs or "N/A - no example projects"

### 9.3 Integration Contract Verification

- [ ] **Protocol implementations compatible** `✅ REQUIRED`
  - **Time**: 2 minutes
  - **Purpose**: Verify SPI protocols are satisfied by core implementations
  - **Command**:
    ```bash
    # Test container initialization (verifies protocol compliance)
    poetry run python -c "
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
c = ModelONEXContainer()
print('✅ Container init: PASS')
print(f'Container type: {type(c).__name__}')
"
    ```
  - **Expected Results**: Prints "✅ Container init: PASS"
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Container initializes without protocol violations
    - ❌ **FAIL**: Protocol violation error or AttributeError
  - **Evidence**: Command output showing "Container init: PASS"

- [ ] **Event envelope compatibility verified** `✅ REQUIRED`
  - **Time**: 5 minutes
  - **Purpose**: Verify ModelEventEnvelope schema is backward compatible
  - **Commands**:
    ```bash
    # =============================================================================
    # Step 1: Capture current schema to artifact
    # =============================================================================
    mkdir -p artifacts/release/v0.4.0
    poetry run python -c "
from omnibase_core.models.event.model_event_envelope import ModelEventEnvelope
import json
schema = ModelEventEnvelope.model_json_schema()
print(json.dumps(schema, indent=2))
" > artifacts/release/v0.4.0/09-event-envelope-schema.json

    # =============================================================================
    # Step 2: Show required fields (for inline evidence)
    # =============================================================================
    poetry run python -c "
from omnibase_core.models.event.model_event_envelope import ModelEventEnvelope
schema = ModelEventEnvelope.model_json_schema()
required = schema.get('required', [])
print('Required fields:', ', '.join(required))
"

    # =============================================================================
    # Step 3: Compare with v0.3.x (if baseline available)
    # =============================================================================
    # If you have v0.3.x schema saved, run:
    # diff artifacts/release/v0.3.6/event-envelope-schema.json artifacts/release/v0.4.0/09-event-envelope-schema.json
    ```
  - **Expected Results**:
    - Schema file created at artifacts/release/v0.4.0/09-event-envelope-schema.json
    - Required fields unchanged from v0.3.x OR migration documented
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Schema unchanged OR breaking changes documented in CHANGELOG
    - ❌ **FAIL**: Schema changed without migration docs
  - **Evidence**: Schema output with diff against v0.3.x (if changed)

- [ ] **Contract YAML schema compatibility** `✅ REQUIRED`
  - **Time**: 3 minutes
  - **Purpose**: Verify v0.3.x contract YAML files parse correctly in v0.4.0
  - **Commands**:
    ```bash
    # =============================================================================
    # Step 1: Verify FileRegistry loads correctly
    # =============================================================================
    poetry run python -c "
from omnibase_core.runtime.file_registry import FileRegistry
r = FileRegistry()
print('✅ FileRegistry init: PASS')
print(f'Registry type: {type(r).__name__}')
"

    # =============================================================================
    # Step 2: Test loading a v0.3.x contract (if available)
    # =============================================================================
    # If you have example v0.3.x contracts:
    # poetry run python -c "
    # from omnibase_core.runtime.file_registry import FileRegistry
    # from pathlib import Path
    # r = FileRegistry()
    # contract = r.load(Path('examples/contracts/legacy_v036_contract.yaml'))
    # print(f'✅ Legacy contract loaded: {contract.fingerprint}')
    # "
    ```
  - **Expected Results**:
    - FileRegistry initializes: prints "✅ FileRegistry init: PASS"
    - No schema validation errors for valid v0.3.x contracts
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: FileRegistry loads, v0.3.x contracts parse (if tested)
    - ❌ **FAIL**: Validation error on valid v0.3.x contract
  - **Evidence**: Command output showing "FileRegistry init: PASS"

### 9.4 Migration Verification

- [ ] **Migration guide tested end-to-end** `✅ REQUIRED`
  - **Time**: 15-20 minutes
  - **Purpose**: Verify migration guide works as documented
  - **Verification Steps**:
    1. Create fresh project with v0.3.6
    2. Write test code using v0.3.x patterns
    3. Follow migration guide step-by-step
    4. Upgrade to v0.4.0
    5. Verify tests pass without manual fixes
  - **Commands**:

    **Option A: Project-local directory (Recommended - works on all platforms)**
    ```bash
    # =============================================================================
    # Step 1: Create migration test project
    # =============================================================================
    # From omnibase_core root directory
    mkdir -p ../_migration_test && cd ../_migration_test
    poetry init --name migration-test --python "^3.12" --no-interaction

    # =============================================================================
    # Step 2: Install v0.3.6 (old version)
    # =============================================================================
    poetry add omnibase_core==0.3.6

    # =============================================================================
    # Step 3: Create test file using v0.3.x patterns
    # =============================================================================
    mkdir -p tests
    cat > tests/test_legacy_import.py << 'EOF'
# Test using v0.3.x import patterns
from omnibase_core.infrastructure.base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

def test_legacy_node_import():
    """Test that v0.3.x imports work."""
    container = ModelONEXContainer()
    assert container is not None
    print("✅ Legacy imports work")

if __name__ == "__main__":
    test_legacy_node_import()
EOF

    # =============================================================================
    # Step 4: Verify v0.3.x pattern works
    # =============================================================================
    poetry add pytest
    poetry run python tests/test_legacy_import.py

    # =============================================================================
    # Step 5: Run migration steps from docs/guides/MIGRATING_TO_V040.md
    # =============================================================================
    # Update imports to v0.4.0 patterns:
    sed -i.bak 's/from omnibase_core.infrastructure.base/from omnibase_core.nodes/' tests/test_legacy_import.py

    # =============================================================================
    # Step 6: Upgrade to v0.4.0
    # =============================================================================
    poetry add omnibase_core==0.4.0

    # =============================================================================
    # Step 7: Verify migrated code works
    # =============================================================================
    poetry run python tests/test_legacy_import.py
    poetry run pytest tests/ -v

    # =============================================================================
    # Cleanup when done
    # =============================================================================
    # cd .. && rm -rf _migration_test
    ```

    **Option B: Unix system temp**
    ```bash
    cd "${TMPDIR:-/tmp}" && mkdir migration-test && cd migration-test
    poetry init --name migration-test --python "^3.12" --no-interaction
    poetry add omnibase_core==0.3.6
    # ... create test file ...
    poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    ```

    **Option C: Windows PowerShell**
    ```powershell
    cd $env:TEMP
    New-Item -ItemType Directory -Force -Path migration-test | Out-Null
    cd migration-test
    poetry init --name migration-test --python "^3.12" --no-interaction
    poetry add omnibase_core==0.3.6
    # ... create test file ...
    poetry add omnibase_core==0.4.0
    poetry run pytest tests/
    ```

  - **Expected Results**:
    - v0.3.6 test runs successfully
    - Migration steps complete without errors
    - v0.4.0 tests pass after migration

  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Migration guide steps work, tests pass after upgrade
    - ❌ **FAIL**: Migration requires manual intervention beyond documented steps

  - **Evidence**: Migration test log showing:
    - v0.3.6 test pass
    - Migration command outputs
    - v0.4.0 test pass

- [ ] **Deprecation warnings present** `📋 INFORMATIONAL`
  - **Time**: 2 minutes
  - **Purpose**: Verify deprecated APIs emit warnings to guide migration
  - **Command**:
    ```bash
    # Enable all deprecation warnings
    poetry run python -W default::DeprecationWarning -c "
from omnibase_core.nodes import NodeCompute
print('✅ Deprecation check complete')
# If any deprecated imports exist, warnings will be shown
"
    ```
  - **Expected Results**:
    - Deprecation warnings shown for any deprecated APIs
    - OR confirmation that no deprecated APIs exist
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Warnings shown OR no deprecated APIs
    - ❌ **INFORMATIONAL ONLY**: Document any unexpected warnings
  - **Evidence**: Warning output (or confirmation of no deprecated APIs)

### 9.5 CI/CD Integration

- [ ] **GitHub Actions workflow compatible** `✅ REQUIRED`
  - **Time**: 20-30 minutes (waiting for CI to run)
  - **Purpose**: Verify downstream CI workflows pass with v0.4.0
  - **Verification Steps**:
    1. Create PR in downstream repo updating omnibase_core to v0.4.0
    2. Wait for CI to run (tests, type checks, linting)
    3. Verify all checks pass
  - **Commands** (example workflow):
    ```bash
    # In downstream repo (omnibase_spi or omninode_core)
    git checkout -b test/omnibase-core-v040-compatibility
    poetry add omnibase_core==0.4.0
    git add pyproject.toml poetry.lock
    git commit -m "test: verify omnibase_core v0.4.0 compatibility"
    git push origin test/omnibase-core-v040-compatibility
    # Create PR via gh CLI or GitHub web UI
    gh pr create --title "test: omnibase_core v0.4.0 compatibility" --body "Testing compatibility with omnibase_core v0.4.0"
    ```
  - **Expected Results**:
    - All CI checks pass (tests, type checking, linting)
    - No new failures introduced by v0.4.0 upgrade
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: All CI checks pass
    - ❌ **FAIL**: Any CI check fails
  - **Evidence**: CI run links for each downstream repo (e.g., GitHub Actions URLs)

- [ ] **Docker builds succeed** `📋 INFORMATIONAL`
  - **Time**: 10-15 minutes (Docker build time)
  - **Purpose**: Verify Docker images build with v0.4.0 dependency
  - **Commands** (in downstream repo with Dockerfile):
    ```bash
    # Update pyproject.toml or requirements.txt to use omnibase_core==0.4.0
    # Then build Docker image
    docker build -t test-downstream:v040-compat .

    # Verify build succeeded and image runs
    docker run --rm test-downstream:v040-compat python -c "import omnibase_core; print(f'✅ Docker build: PASS (version {omnibase_core.__version__})')"
    ```
  - **Expected Results**:
    - Docker build completes successfully
    - Image runs and imports omnibase_core v0.4.0
  - **Pass/Fail Criteria**:
    - ✅ **PASS**: Build succeeds, image runs
    - ❌ **INFORMATIONAL ONLY**: Document failure, proceed with release
  - **Evidence**: Docker build log or "N/A - no Docker builds"

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
# Node purity check (RECOMMENDED - uses dedicated script)
poetry run python scripts/check_node_purity.py --verbose

# Pattern validation (alternative method)
poetry run python -c "
from omnibase_core.validation.patterns import validate_patterns_directory
from pathlib import Path
result = validate_patterns_directory(Path('src/omnibase_core/nodes'))
print(f'Validation complete: {len(result.errors)} issues found')
"

# Type checking (version captured for reproducibility)
echo "=== mypy version ===" && poetry run mypy --version
poetry run mypy src/omnibase_core/ --strict

# Linting and formatting
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
# Note: compute_contract_fingerprint.py does NOT support --recursive, use glob expansion
poetry run python scripts/compute_contract_fingerprint.py contracts/runtime/*.yaml --validate
poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive --dry-run

# Contract linting (lint_contract.py supports --recursive)
poetry run python scripts/lint_contract.py contracts/runtime/ --recursive --verbose

# Legacy pattern check
# Exit codes: 0=matches found (FAIL), 1=no matches (PASS), 2=error
# Preferred (ripgrep - faster, better defaults):
rg "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/
# Alternative (portable grep with -E for extended regex - required for | alternation):
grep -rE "NodeComputeLegacy|NodeReducerLegacy|NodeOrchestratorLegacy" src/
# Expected: exit code 1 (no matches) = SUCCESS (no legacy patterns found)

# =============================================================================
# Section 5: Registry & Discovery
# =============================================================================
# FileRegistry contract loading test
poetry run pytest tests/unit/runtime/test_file_registry.py -v

# =============================================================================
# Section 7: Dependencies
# =============================================================================
sha256sum poetry.lock  # Capture lock hash
poetry check --lock

# =============================================================================
# Section 8: Observability
# =============================================================================
# Error handling tests
poetry run pytest tests/unit/exceptions/test_onex_error.py tests/unit/errors/test_declarative_errors.py -v
```

---

## Sign-off

**MANDATORY**: Before signing off:
1. Verify each gate was validated using the [Pre-Release Evidence Checklist](#pre-release-evidence-checklist) criteria
2. Complete the [Final Sign-off Evidence Verification](#final-sign-off-evidence-verification) checklist above

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| Release Manager | | | |

**Release Manager Attestation**:
- [ ] I have verified each gate meets the [Pre-Release Evidence Checklist](#pre-release-evidence-checklist) requirements
- [ ] I have completed the [Final Sign-off Evidence Verification](#final-sign-off-evidence-verification) checklist
- [ ] All BLOCKER and REQUIRED gates are complete with documented evidence
- [ ] Evidence index file is up-to-date and all links are accessible
- [ ] All evidence includes required fields (timestamp, commit SHA, toolchain versions, result)
- [ ] All evidence has been reviewed for PII/secrets redaction (see [Evidence Storage Guidelines](#evidence-storage-guidelines))

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
  - **Verification Checklist**:
    - [ ] `pip install` completes without errors
    - [ ] Version string matches `0.4.0` exactly
    - [ ] Wheel SHA256 hash matches CI build artifact
    - [ ] All core imports succeed (nodes, container, errors, enums, events, mixins)
    - [ ] Object instantiation works (container, error, enum access)
  - Commands:

    **Unix (Bash)**:
    ```bash
    # Step 1: Create isolated verification environment
    # Uses TMPDIR if set, falls back to /tmp
    VERIFY_DIR="${TMPDIR:-/tmp}/v040-pypi-verify"
    WHEEL_DIR="${TMPDIR:-/tmp}/v040-wheel-verify"
    python -m venv "$VERIFY_DIR"
    source "$VERIFY_DIR/bin/activate"

    # Step 2: Install from PyPI (NOT from local source)
    pip install omnibase_core==0.4.0 --index-url https://pypi.org/simple/
    pip show omnibase_core

    # Step 3: Version verification
    python -c "import omnibase_core; print(f'Version: {omnibase_core.__version__}')"

    # Step 4: Package hash verification
    mkdir -p "$WHEEL_DIR"
    pip download omnibase_core==0.4.0 --no-deps -d "$WHEEL_DIR"
    PYPI_HASH=$(sha256sum "$WHEEL_DIR/omnibase_core-0.4.0-py3-none-any.whl" | cut -d' ' -f1)
    echo "PyPI wheel SHA256: ${PYPI_HASH}"

    # Step 5: Smoke test imports
    python -c "
    from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect; print('Core nodes: OK')
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer; print('Container: OK')
    from omnibase_core.models.errors.model_onex_error import ModelOnexError; print('Errors: OK')
    from omnibase_core.enums import EnumNodeKind, EnumNodeType; print('Enums: OK')
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope; print('Events: OK')
    from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle; print('Mixins: OK')
    print('All smoke test imports: PASS')
    "

    # Step 6: Functional smoke test
    python -c "
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.errors.model_onex_error import ModelOnexError
    from omnibase_core.enums import EnumNodeKind
    container = ModelONEXContainer(); print(f'Container: {type(container).__name__}')
    error = ModelOnexError(message='Test', error_code='TEST_001'); print(f'Error: {error.error_code}')
    print(f'Enum: {EnumNodeKind.COMPUTE}')
    print('Functional smoke test: PASS')
    "

    # Step 7: Cleanup
    deactivate
    rm -rf "$VERIFY_DIR" "$WHEEL_DIR"
    ```

    **Windows (PowerShell)**:
    ```powershell
    # Step 1: Create isolated verification environment
    python -m venv $env:TEMP\v040-pypi-verify
    & "$env:TEMP\v040-pypi-verify\Scripts\Activate.ps1"

    # Step 2: Install from PyPI (NOT from local source)
    pip install omnibase_core==0.4.0 --index-url https://pypi.org/simple/
    pip show omnibase_core

    # Step 3: Version verification
    python -c "import omnibase_core; print(f'Version: {omnibase_core.__version__}')"

    # Step 4: Package hash verification
    New-Item -ItemType Directory -Force -Path "$env:TEMP\v040-wheel-verify" | Out-Null
    pip download omnibase_core==0.4.0 --no-deps -d "$env:TEMP\v040-wheel-verify"
    $wheelPath = Get-ChildItem "$env:TEMP\v040-wheel-verify\omnibase_core-0.4.0-*.whl" | Select-Object -First 1
    $PYPI_HASH = (Get-FileHash -Algorithm SHA256 $wheelPath.FullName).Hash.ToLower()
    Write-Host "PyPI wheel SHA256: $PYPI_HASH"

    # Step 5: Smoke test imports
    python -c @"
from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect; print('Core nodes: OK')
from omnibase_core.models.container.model_onex_container import ModelONEXContainer; print('Container: OK')
from omnibase_core.models.errors.model_onex_error import ModelOnexError; print('Errors: OK')
from omnibase_core.enums import EnumNodeKind, EnumNodeType; print('Enums: OK')
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope; print('Events: OK')
from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle; print('Mixins: OK')
print('All smoke test imports: PASS')
"@

    # Step 6: Functional smoke test
    python -c @"
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums import EnumNodeKind
container = ModelONEXContainer(); print(f'Container: {type(container).__name__}')
error = ModelOnexError(message='Test', error_code='TEST_001'); print(f'Error: {error.error_code}')
print(f'Enum: {EnumNodeKind.COMPUTE}')
print('Functional smoke test: PASS')
"@

    # Step 7: Cleanup
    deactivate
    Remove-Item -Recurse -Force "$env:TEMP\v040-pypi-verify", "$env:TEMP\v040-wheel-verify"
    ```

    **Hash Verification Note** (applies to all platforms):
    > The canonical hash is stored in:
    > 1. GitHub Actions artifact: `release-artifacts/wheel-sha256.txt`
    > 2. GitHub Release attachment: `omnibase_core-0.4.0.sha256`
    > 3. Release notes body: SHA256 checksum section
    >
    > Retrieve expected hash using GitHub CLI (cross-platform):
    > ```
    > gh release download v0.4.0 --pattern "*.sha256" --output expected-hash.txt
    > ```
    >
    > Verify match (MUST be exact):
    > - If hashes match: "Hash verification: PASS"
    > - If hashes differ: "Hash verification: FAIL - Supply chain compromise possible!"

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
