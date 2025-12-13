# ONEX Scripts

This directory contains utility scripts for ONEX development, validation, and maintenance.

---

## Table of Contents

1. [Contract Fingerprinting](#contract-fingerprinting)
   - [Computing Fingerprints](#computing-fingerprints)
   - [Regenerating Fingerprints](#regenerating-fingerprints)
   - [Linting Contracts](#linting-contracts)
2. [Validation Scripts](#validation-scripts)
3. [Code Quality Scripts](#code-quality-scripts)
4. [Quick Reference](#quick-reference)

---

## Contract Fingerprinting

ONEX uses deterministic SHA256 fingerprints to track contract integrity and detect drift.

### Fingerprint Format

```plaintext
<semver>:<sha256-first-12-hex-chars>
Example: 0.4.0:8fa1e2b4c9d1
```

**Components:**
- **semver**: Contract's semantic version (e.g., `1.0.0`, `0.4.0`)
- **hash**: First 12 characters of SHA256 hash of normalized contract content

### Hash Length Justification

The default hash length of **12 hex characters (48 bits)** provides:

- **~281 trillion possible values** (2^48)
- **Collision probability**: With 10,000 contracts, birthday paradox gives ~0.00002% collision chance
- **Readable fingerprints**: Short enough for human readability and copy/paste
- **Sufficient for registry use**: Contract registries typically have hundreds to thousands of contracts

For higher security requirements, use `--hash-length 16` (64 bits) or higher.

### Computing Fingerprints

**Script**: `scripts/compute_contract_fingerprint.py`

Compute fingerprints without modifying files:

```bash
# Compute fingerprint for a single contract
poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml

# Verbose output with full hash
poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --verbose

# Validate existing fingerprint matches computed
poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --validate

# Output as JSON for CI/CD
poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --json

# Process multiple files
poetry run python scripts/compute_contract_fingerprint.py contracts/*.yaml
```

**Exit Codes:**
- `0`: Success (fingerprint computed or validation passed)
- `1`: Validation failed (fingerprint mismatch)
- `2`: Error (file not found, invalid format, etc.)

### Regenerating Fingerprints

**Script**: `scripts/regenerate_fingerprints.py`

Update fingerprints in-place when contract content changes:

```bash
# Regenerate single contract
poetry run python scripts/regenerate_fingerprints.py contracts/my_contract.yaml

# Regenerate all contracts in directory
poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive

# Dry-run: preview changes without modifying files
poetry run python scripts/regenerate_fingerprints.py contracts/ --dry-run -v

# CI/CD: check if fingerprints are current (exits 1 if changes needed)
poetry run python scripts/regenerate_fingerprints.py contracts/ --dry-run --json
```

**Exit Codes:**
- `0`: All fingerprints up-to-date
- `1`: Fingerprints were changed (drift detected)
- `2`: Error occurred

**When to Regenerate:**
- After modifying contract YAML content
- After upgrading contract version
- Before committing contract changes
- In CI/CD to verify fingerprints are current

### Linting Contracts

**Script**: `scripts/lint_contract.py`

Comprehensive contract validation with fingerprint checking:

```bash
# Lint single contract
poetry run python scripts/lint_contract.py contracts/my_contract.yaml

# Lint directory recursively
poetry run python scripts/lint_contract.py contracts/ --recursive

# Lint with baseline for drift detection
poetry run python scripts/lint_contract.py contracts/ --baseline fingerprints.json

# Update baseline with current fingerprints
poetry run python scripts/lint_contract.py contracts/ --baseline fingerprints.json --update-baseline

# Only compute fingerprints (skip other checks)
poetry run python scripts/lint_contract.py contracts/ --compute-fingerprint

# Output as JSON
poetry run python scripts/lint_contract.py contracts/ --json
```

**Validation Checks:**
- YAML syntax validation
- Required field verification (`name`, `version`, `node_type`, `input_model`, `output_model`)
- ONEX naming conventions
- Fingerprint integrity (declared vs computed)
- Baseline drift detection

**Exit Codes:**
- `0`: Validation passed
- `1`: Validation failed (issues detected)
- `2`: Script error

---

## Validation Scripts

Located in `scripts/validation/`. See `scripts/validation/README.md` for details.

### Security Validators

```bash
# Detect hardcoded secrets
poetry run python scripts/validation/validate-secrets.py src/

# Detect hardcoded environment variables
poetry run python scripts/validation/validate-hardcoded-env-vars.py src/
```

### Code Quality Validators

```bash
# Check for stubbed functionality
poetry run python scripts/validation/check_stub_implementations.py

# Validate protocol exports
poetry run python scripts/check_protocol_exports.py

# Check for circular imports
poetry run python scripts/validation/test_circular_imports.py

# Validate ONEX error compliance
poetry run python scripts/validation/validate-onex-error-compliance.py src/
```

### Contract Validators

```bash
# Validate contract YAML structure
poetry run python scripts/validation/validate-contracts.py contracts/

# Validate markdown documentation links
poetry run python scripts/validation/validate_markdown_links.py docs/
```

---

## Code Quality Scripts

### Cleanup

```bash
# Clean temporary files (preserves caches)
poetry run python scripts/cleanup.py --tmp-only

# Full cleanup (removes ALL caches - slow rebuild!)
poetry run python scripts/cleanup.py

# Preview cleanup actions
poetry run python scripts/cleanup.py --dry-run

# Remove tracked tmp files from git
poetry run python scripts/cleanup.py --remove-from-git --tmp-only
```

### Protocol Checking

```bash
# Check protocol exports
poetry run python scripts/check_protocol_exports.py

# Check node purity (no side effects in COMPUTE nodes)
poetry run python scripts/check_node_purity.py

# Check transport imports
poetry run python scripts/check_transport_imports.py
```

---

## Quick Reference

### Contract Fingerprinting Workflow

```bash
# 1. Modify contract YAML

# 2. Regenerate fingerprint
poetry run python scripts/regenerate_fingerprints.py contracts/my_contract.yaml

# 3. Verify with lint
poetry run python scripts/lint_contract.py contracts/my_contract.yaml

# 4. Commit changes
git add contracts/my_contract.yaml
git commit -m "Update contract and fingerprint"
```

### CI/CD Integration

```bash
# Check fingerprints are current (fails if drift detected)
poetry run python scripts/regenerate_fingerprints.py contracts/ -r --dry-run
if [ $? -eq 1 ]; then
    echo "ERROR: Fingerprints out of date. Run regenerate_fingerprints.py"
    exit 1
fi
```

```bash
# Full contract validation
poetry run python scripts/lint_contract.py contracts/ -r --json
```

### Pre-commit Hook Integration

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: regenerate-fingerprints
      name: Regenerate Contract Fingerprints
      entry: poetry run python scripts/regenerate_fingerprints.py
      language: system
      files: ^contracts/.*\.yaml$
      pass_filenames: true
```

---

## Related Documentation

- **Contract Stability Spec**: `docs/architecture/CONTRACT_STABILITY_SPEC.md`
- **Hash Registry**: `src/omnibase_core/contracts/hash_registry.py`
- **Security Validators**: `scripts/validation/README.md`
- **ONEX Architecture**: `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md`

---

**Last Updated**: 2025-12-12
**Project**: omnibase_core v0.4.0
