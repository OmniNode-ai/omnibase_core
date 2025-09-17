# SPI Protocol Validation Scripts

These are specialized copies of the omnibase_core validation framework designed for omnibase_spi use.

## Why Separate Scripts?

Since omnibase_spi cannot depend on omnibase_core (to avoid circular dependencies), it needs its own copies of the validation scripts with SPI-specific modifications.

## Scripts Included

### Core Validation Scripts
- `spi_protocol_auditor.py` - SPI-specific protocol auditing
- `spi_validation_utils.py` - Shared utilities for SPI validation
- `audit_spi_protocols.py` - CLI script for SPI protocol audit

### Integration Scripts
- `validate_spi_completeness.py` - Ensure SPI has all required protocols
- `check_spi_dependencies.py` - Validate SPI internal dependencies

### Pre-commit Integration
- `spi-pre-commit-config.yaml` - Pre-commit configuration for SPI

## Usage

### Quick SPI Audit
```bash
python scripts/spi-copy/audit_spi_protocols.py
```

### Comprehensive SPI Validation
```bash
python scripts/spi-copy/validate_spi_completeness.py
```

### Pre-commit Setup
```bash
cp scripts/spi-copy/spi-pre-commit-config.yaml .pre-commit-config.yaml
pre-commit install
```

## Maintenance

These scripts are copies from omnibase_core and need to be manually synchronized when the core validation logic changes.

**Last Synchronized**: 2024-11-XX
**Source**: omnibase_core/src/omnibase_core/validation/
