"""
Typed metadata models for replacing dict[str, Any] patterns.

This module re-exports strongly-typed models for common metadata patterns
found across discovery, effect, reducer, and other model modules.

All models are in individual files per ONEX single-class-per-file rule.
This module provides a unified import location for convenience.
"""

from omnibase_core.models.common.model_config_schema_property import (
    ModelConfigSchemaProperty,
)
from omnibase_core.models.common.model_custom_health_metrics import (
    ModelCustomHealthMetrics,
)
from omnibase_core.models.common.model_event_subscription_config import (
    ModelEventSubscriptionConfig,
)
from omnibase_core.models.common.model_graph_node_data import ModelGraphNodeData
from omnibase_core.models.common.model_intent_payload import ModelIntentPayload
from omnibase_core.models.common.model_introspection_custom_metrics import (
    ModelIntrospectionCustomMetrics,
)
from omnibase_core.models.common.model_mixin_config_schema import ModelMixinConfigSchema
from omnibase_core.models.common.model_node_capabilities_metadata import (
    ModelNodeCapabilitiesMetadata,
)
from omnibase_core.models.common.model_node_registration_metadata import (
    ModelNodeRegistrationMetadata,
)
from omnibase_core.models.common.model_operation_data import ModelOperationData
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.common.model_request_metadata import ModelRequestMetadata
from omnibase_core.models.common.model_shutdown_metrics import ModelShutdownMetrics
from omnibase_core.models.common.model_tool_metadata_fields import (
    ModelToolMetadataFields,
)
from omnibase_core.models.common.model_tool_result_data import ModelToolResultData
from omnibase_core.models.effect.model_effect_metadata import ModelEffectMetadata

__all__ = [
    "ModelToolMetadataFields",
    "ModelNodeCapabilitiesMetadata",
    "ModelNodeRegistrationMetadata",
    "ModelRequestMetadata",
    "ModelShutdownMetrics",
    "ModelConfigSchemaProperty",
    "ModelMixinConfigSchema",
    "ModelOperationData",
    "ModelEffectMetadata",
    "ModelIntentPayload",
    "ModelReducerMetadata",
    "ModelCustomHealthMetrics",
    "ModelIntrospectionCustomMetrics",
    "ModelGraphNodeData",
    "ModelToolResultData",
    "ModelEventSubscriptionConfig",
]
