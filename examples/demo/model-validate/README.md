# Model Validation Demo: Support Ticket Classification

This demo scenario demonstrates ONEX model validation capabilities using a customer support ticket classification use case. It runs entirely offline with no external API dependencies.

## Scenario Overview

A hypothetical LLM-based support ticket classifier:
- **Input**: Customer support tickets (subject, body, metadata)
- **Output**: Classification (category, sentiment, confidence, suggested reply)

The demo compares two model configurations:
- **Baseline**: `gpt-4-turbo-2024-04-09` (higher accuracy, higher latency)
- **Candidate**: `gpt-4o-mini-2024-07-18` (faster, but some edge case failures)

## Directory Structure

```
model-validate/
├── corpus/
│   ├── golden/           # 10 clean, high-signal samples
│   └── edge-cases/       # 5 stress-test samples
├── mock-responses/
│   ├── baseline/         # 15 responses (all pass)
│   └── candidate/        # 15 responses (3 fail)
├── invariants.yaml       # Validation rules
├── contract.yaml         # Handler contract
└── README.md             # This file
```

## Corpus Samples

### Golden Samples (10)
Clean, unambiguous tickets covering all categories:

| File | Category | Description |
|------|----------|-------------|
| `ticket_001_billing_refund.yaml` | billing_refund | Refund request after cancellation |
| `ticket_002_billing_payment.yaml` | billing_payment | Payment failures during upgrade |
| `ticket_003_account_access.yaml` | account_access | Locked out, MFA issue |
| `ticket_004_account_profile.yaml` | account_profile | Email change request |
| `ticket_005_technical_bug.yaml` | technical_bug | App crashes on login |
| `ticket_006_technical_howto.yaml` | technical_howto | Data export question |
| `ticket_007_billing_refund_enterprise.yaml` | billing_refund | Enterprise invoice discrepancy |
| `ticket_008_account_access_chat.yaml` | account_access | Password reset not received |
| `ticket_009_technical_bug_detailed.yaml` | technical_bug | Sync failures with detailed logs |
| `ticket_010_billing_payment_pro.yaml` | billing_refund | Double charge issue |

### Edge Case Samples (5)
Challenging inputs to test model robustness:

| File | Challenge | Expected Outcome |
|------|-----------|------------------|
| `ticket_011_malformed_date.yaml` | Timezone offset format | Should parse correctly |
| `ticket_012_missing_fields.yaml` | Minimal required fields | Should handle gracefully |
| `ticket_013_unicode_body.yaml` | Unicode/emoji content | May lower confidence |
| `ticket_014_borderline_content.yaml` | Ambiguous category | May lower confidence |
| `ticket_015_negative_sentiment.yaml` | Strong negative tone | Should detect sentiment |

## Invariant Rules

From `invariants.yaml`:

| Rule | Threshold | Description |
|------|-----------|-------------|
| Confidence (general) | >= 0.70 | Minimum for any response |
| Confidence (golden) | >= 0.85 | Higher bar for clean samples |
| Latency (baseline) | <= 2500ms | gpt-4-turbo expected max |
| Latency (candidate) | <= 900ms | gpt-4o-mini expected max |
| ticket_id match | exact | Response must match input |

## Expected Results

### Baseline (gpt-4-turbo)
- **Pass**: 15/15 (100%)
- All samples meet confidence thresholds
- Higher latency (900-1700ms)

### Candidate (gpt-4o-mini)
- **Pass**: 12/15 (80%)
- **Fail**: 3/15 (20%)
- Lower latency (180-520ms)

**Failures:**
1. `response_013_unicode_body.json` - Confidence 0.58 < 0.70 threshold
2. `response_014_borderline_content.json` - Confidence 0.62 < 0.70 threshold
3. `response_015_negative_sentiment.json` - Wrong category (billing_refund vs technical_bug)

## Models

### Input: ModelSupportTicket

```python
from omnibase_core.models.demo.model_validate import ModelSupportTicket

ticket = ModelSupportTicket(
    ticket_id="TKT-2024-001",
    created_at=datetime.now(),
    customer_tier=EnumCustomerTier.PRO,
    channel=EnumSupportChannel.EMAIL,
    subject="Request for refund",
    body="I was charged incorrectly..."
)
```

### Output: ModelSupportClassificationResult

```python
from omnibase_core.models.demo.model_validate import ModelSupportClassificationResult

result = ModelSupportClassificationResult(
    ticket_id="TKT-2024-001",
    category=EnumSupportCategory.BILLING_REFUND,
    confidence=0.95,
    sentiment=EnumSentiment.NEUTRAL,
    summary="Refund request for incorrect charge",
    suggested_reply="I'll process your refund...",
    latency_ms=1250,
    model_id="gpt-4-turbo-2024-04-09"
)
```

## Running the Demo

### Load and Validate Corpus

```python
import yaml
from pathlib import Path
from omnibase_core.models.demo.model_validate import ModelSupportTicket

corpus_dir = Path("examples/demo/model-validate/corpus/golden")
for yaml_file in corpus_dir.glob("*.yaml"):
    with open(yaml_file) as f:
        data = yaml.safe_load(f)
    ticket = ModelSupportTicket.model_validate(data)
    print(f"Loaded: {ticket.ticket_id}")
```

### Validate Mock Responses

```python
import json
from pathlib import Path
from omnibase_core.models.demo.model_validate import ModelSupportClassificationResult

responses_dir = Path("examples/demo/model-validate/mock-responses/candidate")
for json_file in responses_dir.glob("*.json"):
    with open(json_file) as f:
        data = json.load(f)
    result = ModelSupportClassificationResult.model_validate(data)

    # Check confidence threshold
    if result.confidence < 0.70:
        print(f"FAIL: {json_file.name} - confidence {result.confidence} < 0.70")
    else:
        print(f"PASS: {json_file.name}")
```

## Use Cases

1. **Model Comparison**: Compare baseline vs candidate model performance
2. **Regression Testing**: Ensure model updates don't degrade quality
3. **Invariant Validation**: Verify outputs meet schema and threshold requirements
4. **CI/CD Integration**: Automated validation in deployment pipelines
