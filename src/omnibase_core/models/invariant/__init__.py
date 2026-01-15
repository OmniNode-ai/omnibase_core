"""
Invariant models for user-defined validation rules.

This module provides models for defining and evaluating invariants - validation
rules that ensure AI model changes are safe before production deployment.

Models:
    ModelInvariant: Definition of a single invariant (validation rule).
    ModelInvariantResult: Result of evaluating an invariant.
    ModelInvariantDefinition: Detailed definition with type-specific config.
    ModelInvariantSet: Collection of invariants for a node or workflow.
    ModelInvariantViolationDetail: Detailed information about a single violation.
    ModelInvariantViolationReport: Aggregated report of all violations from an evaluation run.
    ModelEvaluationSummary: Summary of batch invariant evaluation results.

Config Models (type-specific configurations):
    ModelSchemaInvariantConfig: JSON Schema validation config.
    ModelFieldPresenceConfig: Required field existence check config.
    ModelFieldValueConfig: Field value matching config.
    ModelThresholdConfig: Numeric bounds checking config.
    ModelLatencyConfig: Response time constraint config.
    ModelCostConfig: Cost budget constraint config.
    ModelCustomInvariantConfig: User-defined callable config.

Functions:
    parse_invariant_set_from_yaml: Parse YAML string into ModelInvariantSet.
    load_invariant_set_from_file: Load ModelInvariantSet from YAML file.
    load_invariant_sets_from_directory: Load all invariant sets from directory.

Thread Safety:
    All invariant models in this module are immutable (frozen=True) after
    creation, making them thread-safe for concurrent read access. No
    synchronization is needed when sharing instances across threads.

Usage:
    >>> from omnibase_core.models.invariant import (
    ...     ModelInvariantDefinition,
    ...     ModelInvariantSet,
    ...     ModelSchemaInvariantConfig,
    ...     ModelLatencyConfig,
    ...     load_invariant_set_from_file,
    ... )
    >>> from omnibase_core.enums import EnumInvariantType
    >>>
    >>> # Define a latency constraint
    >>> latency_invariant = ModelInvariantDefinition(
    ...     invariant_type=EnumInvariantType.LATENCY,
    ...     config=ModelLatencyConfig(max_ms=500),
    ... )
    >>>
    >>> # Load invariant set from YAML file
    >>> invariant_set = load_invariant_set_from_file("path/to/invariants.yaml")
"""

# YAML parsing functions are in utils/ to avoid circular imports
from omnibase_core.utils.util_invariant_yaml_parser import (
    load_invariant_set_from_file,
    load_invariant_sets_from_directory,
    parse_invariant_set_from_yaml,
)

from .model_cost_config import ModelCostConfig
from .model_custom_invariant_config import ModelCustomInvariantConfig
from .model_evaluation_summary import ModelEvaluationSummary
from .model_field_presence_config import ModelFieldPresenceConfig
from .model_field_value_config import ModelFieldValueConfig
from .model_invariant import ModelInvariant
from .model_invariant_definition import InvariantConfigUnion, ModelInvariantDefinition
from .model_invariant_result import ModelInvariantResult
from .model_invariant_set import ModelInvariantSet
from .model_invariant_violation_detail import ModelInvariantViolationDetail
from .model_invariant_violation_report import ModelInvariantViolationReport
from .model_latency_config import ModelLatencyConfig
from .model_schema_invariant_config import ModelSchemaInvariantConfig
from .model_threshold_config import ModelThresholdConfig

__all__ = [
    # Core models
    "ModelInvariant",
    "ModelInvariantResult",
    "ModelInvariantDefinition",
    "ModelInvariantSet",
    "ModelInvariantViolationDetail",
    "ModelInvariantViolationReport",
    "ModelEvaluationSummary",
    # Config models
    "ModelSchemaInvariantConfig",
    "ModelFieldPresenceConfig",
    "ModelFieldValueConfig",
    "ModelThresholdConfig",
    "ModelLatencyConfig",
    "ModelCostConfig",
    "ModelCustomInvariantConfig",
    # Union type
    "InvariantConfigUnion",
    # YAML parsing functions
    "load_invariant_set_from_file",
    "load_invariant_sets_from_directory",
    "parse_invariant_set_from_yaml",
]
