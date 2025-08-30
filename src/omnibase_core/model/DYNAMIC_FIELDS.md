# Legitimate Dynamic Fields Documentation

**Last Updated:** 2025-06-29  
**Purpose:** Document remaining Dict[str, Any] usage that is genuinely necessary

## Overview

This document tracks all remaining `Dict[str, Any]` fields in the ONEX model architecture that are intentionally kept as dynamic fields. Each entry includes justification, example usage, and potential future migration paths.

## Legitimate Dynamic Fields

### 1. Tool Collections (`tools: Dict[str, Any]`)

**Location:** `src/omnibase/model/core/model_enhanced_tool_collection.py`

**Field:** `tools: Dict[str, Any]`

**Justification:** Stores dynamically loaded tool implementations where the value type varies based on the tool being stored. Tools can be functions, classes, or instances.

**Example Usage:**
```python
tools = {
    "hash_tool": HashUtilityTool,  # Class
    "logger": logger_instance,      # Instance
    "validator": validate_func      # Function
}
```

**Migration Path:** Could potentially use `Dict[str, Union[Type, Callable, Any]]` but this doesn't add much value.

### 2. Metadata Fields (`metadata: Dict[str, Any]`)

**Locations:**
- Various models throughout the codebase
- `model_generic_metadata.py`
- Event models, node models, etc.

**Justification:** Metadata is inherently extensible and varies by context. Different nodes, events, and components need to attach arbitrary metadata.

**Example Usage:**
```python
metadata = {
    "created_by": "user123",
    "tags": ["important", "reviewed"],
    "custom_field": {"nested": "data"},
    "timestamp": datetime.utcnow()
}
```

**Migration Path:** None recommended - metadata should remain flexible.

### 3. Discovery Metadata (`discovery_metadata: Dict[str, Any]`)

**Location:** Node discovery result models

**Justification:** Discovery sources (Consul, Kubernetes, file system, etc.) return different metadata structures. Forcing a unified model would lose source-specific information.

**Example Usage:**
```python
# From Consul
discovery_metadata = {
    "consul_tags": ["web", "api"],
    "service_id": "web-1",
    "datacenter": "us-east-1"
}

# From Kubernetes
discovery_metadata = {
    "namespace": "default",
    "labels": {"app": "web"},
    "annotations": {"version": "1.2.3"}
}
```

**Migration Path:** Could create source-specific metadata models, but would need to handle unknown sources.

### 4. Custom Security Settings (`custom_security_settings: Dict[str, Any]`)

**Location:** `src/omnibase/model/security/model_security_level.py`

**Justification:** Security requirements vary by deployment and compliance needs. Organizations need to add custom security settings without modifying core models.

**Example Usage:**
```python
custom_security_settings = {
    "require_hardware_token": True,
    "biometric_required": False,
    "custom_audit_fields": ["ip", "device_id"],
    "organization_specific": {"dept": "finance"}
}
```

**Migration Path:** None - extensibility is the primary requirement.

### 5. Performance Metrics (`performance_metrics: Dict[str, Any]`)

**Location:** Result models, CLI models

**Justification:** Performance metrics vary by operation type. Different commands collect different metrics.

**Example Usage:**
```python
performance_metrics = {
    "query_time_ms": 45,
    "rows_processed": 1000,
    "cache_hits": 23,
    "custom_timer": 0.123
}
```

**Migration Path:** Could create a base metrics model with common fields and custom extensions.

### 6. Debug/Trace Data (`debug_info: Dict[str, Any]`, `trace_data: Dict[str, Any]`)

**Location:** CLI result models, execution models

**Justification:** Debug and trace data is highly contextual and varies by debugging needs. Structure depends on what's being debugged.

**Example Usage:**
```python
debug_info = {
    "stack_trace": [...],
    "variable_state": {"x": 1, "y": 2},
    "internal_state": {...},
    "timing_breakdown": {...}
}
```

**Migration Path:** None - flexibility needed for debugging.

### 7. Raw Data Fields (`raw_data: Dict[str, Any]`)

**Location:**
- `ModelCliOutputData`
- `ModelCustomFilters` (for legacy filters)

**Justification:** Backward compatibility and migration support. Allows handling of unknown data structures during transition periods.

**Example Usage:**
```python
# Unknown CLI output structure
raw_data = {
    "legacy_field": "value",
    "undocumented_response": {...}
}
```

**Migration Path:** Should decrease over time as more structures are typed.

### 8. Test Results (`test_results: Dict[str, bool]`)

**Location:** `ModelCliOutputData`

**Justification:** Test names are dynamic and vary by test suite. Simple bool results are sufficient.

**Example Usage:**
```python
test_results = {
    "test_connection": True,
    "test_auth": True,
    "test_custom_check": False
}
```

**Migration Path:** Current structure is appropriate for the use case.

### 9. Configuration Values (`config_values: Dict[str, str]`)

**Location:** `ModelCliOutputData`

**Justification:** Configuration keys vary by node and deployment. String values are sufficient for display.

**Example Usage:**
```python
config_values = {
    "api_endpoint": "https://api.example.com",
    "timeout": "30",
    "mode": "production"
}
```

**Migration Path:** Could potentially be more strictly typed per node type.

## Summary Statistics

- **Total Dict[str, Any] instances remaining:** ~10-12
- **Legitimate (documented here):** 9
- **Target for future elimination:** 1-3
- **Permanently dynamic:** 6-8

## Guidelines for New Code

1. **Avoid Dict[str, Any] by default** - Always try to create a typed model first
2. **Document if truly dynamic** - If you must use Dict[str, Any], add it to this document
3. **Consider Union types** - Sometimes `Union[ModelA, ModelB, ModelC]` is better
4. **Use base classes** - Common fields in base class, extensions in subclasses
5. **Think about the future** - Will this field always be dynamic, or just unknown now?

## Review Schedule

This document should be reviewed quarterly to:
1. Check if any dynamic fields can now be typed
2. Ensure new Dict[str, Any] usage is documented
3. Update migration paths based on new patterns
4. Remove entries that have been migrated
