# ONEX Opus Nightly Review System

Deterministic, diff-driven code review using Opus 4.1 for preventing drift in codebases.

## Overview

ONEX provides automated code review through two modes:
- **Baseline**: Initial analysis of entire repository (non-archived code)
- **Nightly**: Incremental review of changes since last successful run

## Quick Start

```bash
# Run baseline analysis (first time)
./onex/run_onex.sh baseline

# Run nightly review
./onex/run_onex.sh nightly

# Check status
./onex/run_onex.sh status
```

## Directory Structure

```
onex/
├── configs/
│   └── policy.yaml         # Rule configuration and repo policies
├── scripts/
│   ├── baseline_producer.sh # Generates baseline analysis data
│   ├── nightly_producer.sh  # Generates nightly review data
│   └── onex_reviewer.py    # Main review engine
├── outputs/                # Review results
└── run_onex.sh            # Main orchestrator

.onex_baseline/            # Baseline data cache
.onex_nightly/             # Nightly state and runs
```

## Rules

### Naming Rules
- `ONEX.NAMING.PROTOCOL_001`: Protocol classes must start with "Protocol"
- `ONEX.NAMING.MODEL_001`: Model classes must start with "Model"
- `ONEX.NAMING.ENUM_001`: Enum classes must start with "Enum"
- `ONEX.NAMING.NODE_001`: Node classes must start with "Node"

### Boundary Rules
- `ONEX.BOUNDARY.FORBIDDEN_IMPORT_001`: Enforces import boundaries between repos

### SPI Purity Rules
- `ONEX.SPI.RUNTIMECHECKABLE_001`: Protocol classes need @runtime_checkable
- `ONEX.SPI.FORBIDDEN_LIB_001`: No OS/network libraries in SPI code

### Typing Rules
- `ONEX.TYPE.UNANNOTATED_DEF_001`: Functions must have type annotations
- `ONEX.TYPE.ANY_001`: Avoid using Any type
- `ONEX.TYPE.OPTIONAL_ASSERT_001`: Don't assert Optional types immediately

### Waiver Rules
- `ONEX.WAIVER.MALFORMED_001`: Waivers need reason= and expires=
- `ONEX.WAIVER.EXPIRED_001`: Expired waivers are errors

## Configuration

Edit `onex/configs/policy.yaml` to customize:
- Repository-specific import boundaries
- Rule enablement/severity
- File size and diff limits

## Waiver Format

```python
# onex:ignore ONEX.NAMING.PROTOCOL_001 reason=Temporary during migration expires=2025-10-15
class ConfigProvider(Protocol):
    pass
```

## Output Format

### NDJSON Findings
```json
{"ruleset_version":"0.1","rule_id":"ONEX.NAMING.PROTOCOL_001","severity":"error","repo":"omnibase-core","path":"src/protocol_config.py","line":12,"message":"Protocol class does not start with 'Protocol'","evidence":{"class_name":"ConfigProvider"},"suggested_fix":"Rename to ProtocolConfigProvider","fingerprint":"b3b1c3b0"}
```

### Markdown Summary
- Executive summary with risk score (0-100)
- Top violations
- Waiver issues
- Next actions
- Coverage notes

## GitHub Actions

Automated nightly runs at 22:00 America/New_York:
- Creates issues for errors
- Posts summaries to workflow
- Maintains state between runs

## Manual Commands

```bash
# Run with custom policy
./onex/run_onex.sh baseline --policy custom_policy.yaml

# Clean all cache
./onex/run_onex.sh clean

# Direct script usage
./onex/scripts/baseline_producer.sh
python3 ./onex/scripts/onex_reviewer.py baseline .onex_baseline/*/latest
```

## Risk Scoring

- Each error: +15 points
- Each warning: +5 points
- Max score: 100
- Score 0-30: Low risk
- Score 31-60: Medium risk
- Score 61-100: High risk

## Performance

- Baseline: Shards large diffs into 200KB chunks
- Nightly: Single diff up to 500KB (truncates if larger)
- Excludes: archives, build directories, node_modules, etc.

## Troubleshooting

1. **No files found**: Check EXCLUDE_REGEX and INCLUDE_EXT in scripts
2. **Policy not applied**: Verify repo name matches policy.yaml
3. **Marker not updated**: Only updates after successful review
4. **Memory issues**: Reduce BYTES_PER_SHARD in baseline_producer.sh