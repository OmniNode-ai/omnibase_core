# ONEX Beta Demo Guide

> **Version**: 0.7.0 | **Status**: Beta | **Ticket**: OMN-1398

This guide walks you through the ONEX demo system, which demonstrates model validation with corpus replay and invariant evaluation.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [What This Demo Shows](#what-this-demo-shows)
3. [Demo Walkthrough](#demo-walkthrough)
4. [Understanding the Output](#understanding-the-output)
5. [Running with Real LLMs](#running-with-real-llms)
6. [CLI Reference](#cli-reference)
7. [Adding New Scenarios](#adding-new-scenarios)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

Run the demo in 30 seconds:

```bash
# From the repository root
cd /path/to/omnibase_core

# List available demos
poetry run onex demo list

# Run the model-validate demo (mock mode - no API key required)
poetry run onex demo run --scenario model-validate
```

Expected output:

```
=================================================================
                    ONEX DEMO: model-validate
=================================================================

Loading corpus from examples/demo/model-validate/corpus/...
  - golden: 10 samples
  - edge-cases: 5 samples
  Total: 15 samples

Running validation (mock mode)...
  [1/15] TKT-2024-001 (golden) ... PASS
  [2/15] TKT-2024-002 (golden) ... PASS
  ...
  [15/15] TKT-2024-015 (edge-case) ... FAIL

-----------------------------------------------------------------
RESULTS
-----------------------------------------------------------------
baseline_confidence        15/15 (100%)
candidate_confidence       12/15 (80%)  <- 3 failures

Verdict: REVIEW REQUIRED
Recommendation: Candidate model requires review before production use.

-----------------------------------------------------------------
OUTPUT
-----------------------------------------------------------------
Bundle:  ./out/demo/2024-01-15T103045/
Report:  ./out/demo/2024-01-15T103045/report.md

To view: cat ./out/demo/2024-01-15T103045/report.md
```

---

## What This Demo Shows

### The Problem

You want to replace your production LLM (expensive, slow) with a cheaper/faster candidate model. But how do you know the candidate performs as well?

### The Solution

ONEX model validation provides:

1. **Corpus Replay**: Run both models against the same test corpus
2. **Invariant Evaluation**: Check outputs against defined rules (confidence thresholds, schema validation, etc.)
3. **Comparison Reports**: Side-by-side analysis with pass/fail breakdown

### What You Get

| Artifact | Description |
|----------|-------------|
| `report.md` | Human-readable summary with verdict |
| `report.json` | Machine-readable results for CI/CD |
| `inputs/` | Numbered corpus samples used |
| `outputs/` | Per-sample evaluation results |
| `run_manifest.yaml` | Run configuration metadata |

---

## Demo Walkthrough

The `model-validate` scenario demonstrates support ticket classification.

### Scenario Structure

```text
examples/demo/model-validate/
├── corpus/
│   ├── golden/              # 10 clean, unambiguous tickets
│   │   ├── ticket_001_billing_refund.yaml
│   │   ├── ticket_002_billing_payment.yaml
│   │   └── ... (10 total)
│   └── edge-cases/          # 5 challenging tickets
│       ├── ticket_011_malformed_date.yaml
│       ├── ticket_012_missing_fields.yaml
│       └── ... (5 total)
├── mock-responses/
│   ├── baseline/            # 15 responses (all pass)
│   └── candidate/           # 15 responses (3 fail)
├── invariants.yaml          # Validation rules
├── contract.yaml            # Handler contract
└── README.md
```

### Example Corpus Sample

**File**: `corpus/golden/ticket_001_billing_refund.yaml`

```yaml
---
# Golden sample: Clear refund request, polite tone
ticket_id: "TKT-2024-001"
created_at: "2024-01-15T10:30:00Z"
customer_tier: "pro"
channel: "email"
language: "en"
subject: "Request for refund on recent charge"
body: |
  Hi Support Team,

  I was charged for a subscription renewal on January 10th, but I had
  cancelled my subscription back in December. Could you please process a refund
  for this charge?

  My account email is user@example.com and the transaction ID is TXN-12345.

  Thank you for your help!

  Best regards,
  Customer
attachments: null
product_area: "billing"
priority_hint: "medium"
previous_contact_count: 0
```

### Example Mock Response

**File**: `mock-responses/baseline/response_001_billing_refund.json`

```json
{
  "ticket_id": "TKT-2024-001",
  "category": "billing_refund",
  "confidence": 0.95,
  "sentiment": "neutral",
  "summary": "Customer requesting refund for subscription renewal charge after cancellation",
  "suggested_reply": "Thank you for contacting us about the charge. I've verified that your subscription was cancelled in December, and I'm processing a full refund to your original payment method. Please allow 5-7 business days for the refund to appear on your statement. We apologize for any inconvenience this may have caused.",
  "latency_ms": 1250,
  "model_id": "gpt-4-turbo-2024-04-09",
  "reason_codes": ["subscription_cancelled", "recent_charge", "refund_eligible"],
  "invariant_tags": ["billing_domain", "refund_flow"]
}
```

### Invariant Rules

**File**: `invariants.yaml`

| Rule | Threshold | Description |
|------|-----------|-------------|
| `confidence_min` | >= 0.70 | Minimum confidence for any response |
| `golden_confidence_min` | >= 0.85 | Higher bar for clean, unambiguous samples |
| `baseline_max_ms` | <= 2500ms | gpt-4-turbo expected max latency |
| `candidate_max_ms` | <= 900ms | gpt-4o-mini expected max latency |
| `ticket_id_must_match` | exact | Response ticket_id must match input |

### Execution Flow

```text
┌─────────────────┐
│  Load Corpus    │  15 YAML samples from corpus/
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Load Mocks     │  30 JSON responses (15 baseline + 15 candidate)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Evaluate       │  Check each response against invariants
│  Invariants     │  - confidence thresholds
└────────┬────────┘  - schema validation
         │           - latency constraints
         v
┌─────────────────┐
│  Aggregate      │  Calculate pass/fail counts
│  Results        │  Determine verdict (PASS/REVIEW/FAIL)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Generate       │  Write report.md, report.json
│  Reports        │  Save inputs/, outputs/
└─────────────────┘
```

### Expected Results

**Baseline (gpt-4-turbo)**:
- **Pass**: 15/15 (100%)
- All samples meet confidence thresholds
- Higher latency (900-1700ms)

**Candidate (gpt-4o-mini)**:
- **Pass**: 12/15 (80%)
- **Fail**: 3/15 (20%)
- Lower latency (180-520ms)

**Failures** (candidate model):

| Sample | Issue | Details |
|--------|-------|---------|
| `ticket_013_unicode_body.yaml` | Low confidence | 0.58 < 0.70 threshold |
| `ticket_014_borderline_content.yaml` | Low confidence | 0.62 < 0.70 threshold |
| `ticket_015_negative_sentiment.yaml` | Wrong category | billing_refund vs technical_bug |

---

## Understanding the Output

### Output Bundle Structure

After running the demo, you'll find this structure:

```text
./out/demo/<timestamp>/
├── run_manifest.yaml    # Run configuration metadata
├── inputs/              # Numbered YAML corpus samples
│   ├── sample_001.yaml
│   ├── sample_002.yaml
│   └── ...
├── outputs/             # Numbered JSON evaluation results
│   ├── sample_001.json
│   ├── sample_002.json
│   └── ...
├── report.md            # Human-readable markdown report
└── report.json          # Machine-readable canonical report
```

### Run Manifest

**File**: `run_manifest.yaml`

```yaml
scenario: model-validate
timestamp: "2024-01-15T10:30:45Z"
seed: null
live_mode: false
repeat: 1
corpus_count: 15
result_count: 15
```

### Markdown Report Sections

**File**: `report.md`

```markdown
# ONEX Demo Report: model-validate

**Generated**: 2024-01-15T10:30:45Z

## Summary

- **Total Samples**: 15
- **Passed**: 12
- **Failed**: 3
- **Pass Rate**: 80.0%
- **Verdict**: REVIEW
- **Recommendation**: Candidate model requires review before production use.

## Invariant Results

| Invariant | Passed | Failed | Total | Rate |
|-----------|--------|--------|-------|------|
| baseline_confidence | 15 | 0 | 15 | 100% |
| candidate_confidence | 12 | 3 | 15 | 80% |

## Failures

- **TKT-2024-013** (candidate_confidence): Confidence 0.58 below threshold 0.70
- **TKT-2024-014** (candidate_confidence): Confidence 0.62 below threshold 0.70
- **TKT-2024-015** (candidate_confidence): Category mismatch

## Sample Results

- PASS Sample 1: TKT-2024-001
- PASS Sample 2: TKT-2024-002
...
- FAIL Sample 13: TKT-2024-013
- FAIL Sample 14: TKT-2024-014
- FAIL Sample 15: TKT-2024-015
```

### Verdict Thresholds

| Verdict | Pass Rate | Color | Meaning |
|---------|-----------|-------|---------|
| **PASS** | 100% | Green | All invariants met, safe to proceed |
| **REVIEW** | >= 80% | Yellow | Some failures, needs human review |
| **FAIL** | < 80% | Red | Too many failures, do not proceed |

---

## Running with Real LLMs

### Live Mode Setup

To run with real LLM API calls instead of mock responses:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run in live mode
poetry run onex demo run --scenario model-validate --live
```

### Live Mode Differences

| Aspect | Mock Mode | Live Mode |
|--------|-----------|-----------|
| API Key | Not required | Required |
| Responses | From `mock-responses/` | From actual LLM |
| Determinism | 100% reproducible | May vary |
| Cost | Free | Per-token charges |
| Speed | Fast (~1s total) | Slower (API latency) |
| Confidence Check | Evaluated | Skipped (no mock comparison) |

### When to Use Each Mode

**Mock Mode** (default):
- CI/CD pipelines
- Local development
- Demonstrations
- Reproducible testing

**Live Mode**:
- Real model evaluation
- Production readiness checks
- A/B testing new models
- Collecting baseline data

---

## CLI Reference

### List Scenarios

```bash
# List available demo scenarios
poetry run onex demo list

# List with verbose details
poetry run onex demo list --verbose
```

### Run Demo

```bash
poetry run onex demo run --scenario <name> [OPTIONS]
```

### CLI Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--scenario` | `-s` | Demo scenario name (required) | Required |
| `--live` | | Use real LLM calls instead of mock | `false` |
| `--output` | `-o` | Custom output directory | `./out/demo/<timestamp>/` |
| `--seed` | | Random seed for deterministic execution | None |
| `--repeat` | | Repeat corpus N times (simulate larger corpus) | `1` |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All invariants passed (PASS verdict) |
| `1` | Some invariants failed or error occurred |

### Examples

```bash
# Basic run
poetry run onex demo run --scenario model-validate

# Live mode with real LLMs
poetry run onex demo run --scenario model-validate --live

# Custom output directory
poetry run onex demo run --scenario model-validate --output ./my-results

# Reproducible run with seed
poetry run onex demo run --scenario model-validate --seed 42

# Stress test with 3x corpus
poetry run onex demo run --scenario model-validate --repeat 3

# Combine options
poetry run onex demo run \
  --scenario model-validate \
  --live \
  --output ./prod-eval \
  --seed 12345
```

---

## Adding New Scenarios

### Step 1: Create Directory Structure

```bash
mkdir -p examples/demo/my-scenario/{corpus,mock-responses}
```

### Step 2: Add Contract and Invariants

**File**: `examples/demo/my-scenario/contract.yaml`

```yaml
---
name: my-scenario
version: "1.0.0"
description: "My custom demo scenario"
metadata:
  description: "Brief description for onex demo list"
  author: "Your Name"
```

**File**: `examples/demo/my-scenario/invariants.yaml`

```yaml
---
# Define your validation rules here
thresholds:
  confidence_min: 0.70

output_constraints:
  # Your constraints
```

### Step 3: Add Corpus Samples

Create YAML files in `corpus/`:

```yaml
# examples/demo/my-scenario/corpus/sample_001.yaml
---
id: "SAMPLE-001"
input_field: "Your input data"
# ... more fields
```

### Step 4: Add Mock Responses

Create JSON files in `mock-responses/`:

```json
{
  "id": "SAMPLE-001",
  "output_field": "Model response",
  "confidence": 0.92
}
```

### Step 5: Test Discovery

```bash
# Verify scenario is discovered
poetry run onex demo list

# Should show:
# my-scenario    My custom demo scenario
```

### Step 6: Run Your Scenario

```bash
poetry run onex demo run --scenario my-scenario
```

### Scenario Requirements

| Requirement | Notes |
|-------------|-------|
| Location | `examples/demo/<scenario-name>/` |
| Contract | `contract.yaml` OR `invariants.yaml` (at least one) |
| Corpus | YAML files in `corpus/` directory |
| Mock Responses | JSON files in `mock-responses/` (for mock mode) |
| README | Optional but recommended |

---

## Troubleshooting

### Common Issues

#### "Scenario not found"

```
Error: Scenario 'xyz' not found. Run 'onex demo list' to see available scenarios.
```

**Solution**: Check scenario name spelling and run `onex demo list` to see available scenarios.

#### "No corpus samples found"

```
Error: No corpus samples found in examples/demo/xyz/corpus/
```

**Solution**: Ensure your scenario has a `corpus/` directory with `.yaml` files.

#### "API key required" (live mode)

```
Error: OPENAI_API_KEY environment variable not set.
```

**Solution**: Only needed with `--live` flag. Either:
- Set the environment variable: `export OPENAI_API_KEY="sk-..."`
- Or use mock mode (remove `--live` flag)

#### "Could not locate examples/demo/"

```
Error: Could not locate examples/demo/ directory.
```

**Solution**: Run from the repository root directory, or ensure the package is installed correctly.

#### "Mock response not found"

```
Warning: No mock response for sample_001
```

**Solution**: Ensure `mock-responses/` directory has corresponding JSON files for each corpus sample. File naming should follow pattern: `response_001_*.json` for `ticket_001_*.yaml`.

### Debug Tips

1. **Check corpus loading**: Use `--verbose` (if available) or check `run_manifest.yaml` for corpus count.

2. **Inspect individual results**: Check `outputs/sample_NNN.json` for per-sample evaluation details.

3. **Review invariant configuration**: Verify `invariants.yaml` thresholds match your expectations.

4. **Compare baseline vs candidate**: Look at both `mock-responses/baseline/` and `mock-responses/candidate/` for the same sample.

### Getting Help

- **Documentation**: This guide and `examples/demo/model-validate/README.md`
- **CLI Help**: `poetry run onex demo --help`
- **Ticket**: Report issues referencing OMN-1398

---

## See Also

- [Node Building Guide](../guides/node-building/README.md)
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Model Validation Scenario README](../../examples/demo/model-validate/README.md)
