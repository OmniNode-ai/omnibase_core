# Agent Templates - AI-Friendly Node Building Templates

**Status**: 🚧 Coming Soon - Planned Documentation
**Version**: 1.0.0 (planned)
**Last Updated**: 2025-01-20
**Estimated Reading Time**: 15 minutes
**Target Audience**: AI Agents and automated code generation systems

## Overview

This document provides structured, parseable templates specifically designed for AI agents to generate ONEX nodes. Each template includes complete code, clear annotations, and validation checkpoints for automated verification.

## Design Philosophy

Agent templates are optimized for:
- **Parseability**: Structured format easily parsed by AI systems
- **Completeness**: Copy-paste ready with all necessary imports
- **Validation**: Built-in checkpoints for automated testing
- **Clarity**: Explicit patterns with minimal ambiguity
- **Type Safety**: Strong typing throughout

## Planned Content

### 1. Template Format Specification

#### Standard Template Structure
```yaml
# Each template will follow this structure:
template:
  metadata:
    node_type: "COMPUTE|EFFECT|REDUCER|ORCHESTRATOR"
    name: "Descriptive name"
    purpose: "What this template accomplishes"
    complexity: "simple|intermediate|advanced"

  prerequisites:
    - List of required dependencies
    - List of required knowledge
    - List of required setup steps

  code:
    imports: "Complete import section"
    models: "Contract and model definitions"
    node_class: "Complete node implementation"
    tests: "Complete test suite"

  validation:
    checkpoints:
      - name: "Checkpoint name"
        command: "poetry run pytest ..."
        expected_result: "Success criteria"
```text

### 2. COMPUTE Node Templates

#### Template: Simple Data Transformer
**Purpose**: Pure transformation of input data to output data
**Use Case**: Data validation, formatting, calculation
**Complexity**: Simple

```python
# TODO: Complete template with:
# - Full imports section
# - Contract definitions
# - Node implementation
# - Test suite
# - Validation commands
```text

#### Template: Batch Data Processor
**Purpose**: Processing collections of items
**Use Case**: Bulk transformations, aggregations
**Complexity**: Intermediate

#### Template: Cached Calculator
**Purpose**: Expensive computations with memoization
**Use Case**: Complex calculations with repeated inputs
**Complexity**: Intermediate

### 3. EFFECT Node Templates

#### Template: Database Writer
**Purpose**: Persist data to database with transaction management
**Use Case**: CRUD operations, data persistence
**Complexity**: Intermediate

```python
# TODO: Complete template with:
# - Database dependency injection
# - Transaction management
# - Error handling and rollback
# - Idempotency considerations
# - Test suite with mocks
```text

#### Template: HTTP API Client
**Purpose**: Call external REST APIs with retry logic
**Use Case**: Third-party integrations, external services
**Complexity**: Intermediate

#### Template: File System Operations
**Purpose**: Read/write files with error handling
**Use Case**: File processing, backup, data export
**Complexity**: Simple

### 4. REDUCER Node Templates

#### Template: FSM State Manager
**Purpose**: Pure finite state machine with Intent emission
**Use Case**: Workflow state management, status tracking
**Complexity**: Advanced

```python
# TODO: Complete template with:
# - FSM pattern implementation
# - Intent emission
# - State transition validation
# - Event handling
# - Test suite for all transitions
```python

#### Template: Metrics Aggregator
**Purpose**: Collect and aggregate metrics data
**Use Case**: Real-time metrics, analytics
**Complexity**: Intermediate

#### Template: Event Sourcing Reducer
**Purpose**: Rebuild state from event stream
**Use Case**: Audit trails, event replay
**Complexity**: Advanced

### 5. ORCHESTRATOR Node Templates

#### Template: Sequential Workflow
**Purpose**: Execute nodes in sequence with error handling
**Use Case**: Multi-step processes with dependencies
**Complexity**: Intermediate

```python
# TODO: Complete template with:
# - Dependency injection of child nodes
# - Lease management for Actions
# - Error recovery strategies
# - Progress tracking
# - Test suite for workflow
```text

#### Template: Parallel Workflow
**Purpose**: Execute independent nodes concurrently
**Use Case**: Batch processing, parallel operations
**Complexity**: Advanced

#### Template: Conditional Router
**Purpose**: Dynamic routing based on conditions
**Use Case**: Decision trees, adaptive workflows
**Complexity**: Advanced

### 6. Agent Interaction Patterns

#### Pattern: Template Selection Decision Tree
```yaml
agent_decision_flow:
  question_1: "Does the node perform I/O operations?"
    yes: "Consider EFFECT or ORCHESTRATOR"
    no: "Consider COMPUTE or REDUCER"

  question_2: "Does it maintain state between calls?"
    yes: "Use REDUCER template"
    no: "Use COMPUTE template"

  question_3: "Does it coordinate other nodes?"
    yes: "Use ORCHESTRATOR template"
    no: "Use EFFECT template"
```python

#### Pattern: Validation Workflow
```yaml
agent_validation_steps:
  1. Generate code from template
  2. Run: poetry run mypy src/your_module/
  3. Run: poetry run pytest tests/your_tests/ -v
  4. Check: All tests pass
  5. Check: Type checking passes
  6. Check: Coverage > 90%
  7. Confirm: Ready for integration
```python

### 7. Copy-Paste Ready Templates

Each template will include:

```python
"""
TEMPLATE: [Template Name]
PURPOSE: [What it does]
USAGE: [When to use it]
VALIDATION: [How to verify it works]

STEP 1: Copy this template
STEP 2: Replace [PLACEHOLDERS] with your values
STEP 3: Run validation commands
STEP 4: Integrate into your project
"""

# [COMPLETE WORKING CODE HERE]

# VALIDATION COMMANDS:
# poetry run mypy src/your_module/node_your_name_type.py
# poetry run pytest tests/unit/test_node_your_name.py -xvs
# Expected: All tests pass, type checking passes
```python

### 8. Agent-Specific Utilities

#### Template Variable Extraction
```python
# TODO: Provide regex/parsing tools for extracting:
# - Node name from template
# - Node type from template
# - Required dependencies from template
# - Validation commands from template
```text

#### Automated Validation Scripts
```bash
# TODO: Provide validation scripts:
# validate_template.sh <node_file> <test_file>
# - Checks imports
# - Runs type checking
# - Runs tests
# - Verifies coverage
# - Reports success/failure
```python

## Temporary Resources

While agent-specific templates are being developed, AI agents can use:

### Existing Templates (Human-Oriented)
- [COMPUTE Node Template](../../guides/templates/COMPUTE_NODE_TEMPLATE.md)
- [EFFECT Node Template](../../guides/templates/EFFECT_NODE_TEMPLATE.md)
- [REDUCER Node Template](../../guides/templates/REDUCER_NODE_TEMPLATE.md)
- [ORCHESTRATOR Node Template](../../guides/templates/ORCHESTRATOR_NODE_TEMPLATE.md)

### Parsing Strategy for Existing Templates
```python
# Agents should:
# 1. Read template markdown
# 2. Extract code blocks (```python sections)
# 3. Identify imports, class definitions, methods
# 4. Adapt variable names and logic
# 5. Generate tests based on patterns
# 6. Validate with poetry run commands
```markdown

### Tutorial-Based Learning
- [COMPUTE Node Tutorial](03_COMPUTE_NODE_TUTORIAL.md) - Step-by-step example
- [Node Types](02_NODE_TYPES.md) - Decision criteria for type selection

## Coming Soon

Agent templates will include:

- ✅ **Structured YAML Metadata** - Machine-parseable template metadata
- ✅ **Complete Code Blocks** - No ellipsis, all code present
- ✅ **Inline Annotations** - Comments explaining each section
- ✅ **Validation Commands** - Exact commands to verify success
- ✅ **Decision Trees** - Logic for template selection
- ✅ **Error Handling Examples** - Complete error scenarios
- ✅ **Test Generation Rules** - How to generate tests from templates

## Agent Success Criteria

An AI agent successfully using these templates should:

1. **Select** appropriate template based on requirements
2. **Adapt** template variables to specific use case
3. **Generate** complete, working code
4. **Validate** using provided commands
5. **Verify** all tests pass (>90% coverage)
6. **Integrate** into existing codebase

## Agent Workflow Example

```yaml
agent_workflow:
  input: "User request: 'Create a node that calculates shipping costs'"

  step_1_analyze:
    question: "Does this involve I/O?"
    answer: "No - pure calculation"
    decision: "COMPUTE node"

  step_2_select_template:
    template: "COMPUTE: Simple Data Transformer"
    reason: "Pure transformation, no state needed"

  step_3_adapt:
    node_name: "NodeShippingCalculatorCompute"
    contract_name: "ModelContractShippingCalculation"
    input_fields: ["weight", "distance", "service_level"]
    output_fields: ["total_cost", "breakdown"]

  step_4_generate:
    action: "Replace template placeholders with values"
    output: "Complete node implementation"

  step_5_validate:
    commands:
      - "poetry run mypy src/shipping/node_shipping_calculator_compute.py"
      - "poetry run pytest tests/unit/test_node_shipping_calculator.py -xvs"
    expected: "All pass"

  step_6_report:
    status: "Success"
    artifacts:
      - "src/shipping/node_shipping_calculator_compute.py"
      - "tests/unit/test_node_shipping_calculator.py"
```markdown

## Related Documentation

- [README](README.md) - Node Building Guide overview
- [Node Types](02_NODE_TYPES.md) - Understanding node type selection
- [Patterns Catalog](07_PATTERNS_CATALOG.md) - Common patterns
- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Testing strategies

---

**TODO**: This document is planned for Phase 2 of documentation development, specifically designed for AI agent integration. Check [DOCUMENTATION_ARCHITECTURE.md](../../architecture/DOCUMENTATION_ARCHITECTURE.md) for the development roadmap.

**Last Updated**: 2025-01-20
