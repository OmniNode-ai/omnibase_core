"""
ModelOnexEnvelopeV1: Kafka Standardized Event Envelope

Production-grade Kafka event envelope implementing OnexEnvelopeV1 Avro schema
for standardized cross-component intelligence coordination with W3C trace context
and enterprise reliability features.
"""

import gzip
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.kafka.model_avro_compatible_data import \
    ModelAvroCompatibleData
from omnibase_core.model.kafka.model_content_encoding import \
    ModelContentEncoding
from omnibase_core.model.kafka.model_delivery_guarantee import \
    ModelDeliveryGuarantee
from omnibase_core.model.kafka.model_event_priority import ModelEventPriority
from omnibase_core.model.kafka.model_intelligence_result import \
    ModelIntelligenceResult
from omnibase_core.model.kafka.model_payload_data import ModelPayloadData
from omnibase_core.model.kafka.model_performance_hints import \
    ModelPerformanceHints
from omnibase_core.model.kafka.model_retention_policy import \
    ModelRetentionPolicy
from omnibase_core.model.kafka.model_routing_context import ModelRoutingContext
from omnibase_core.model.kafka.model_rule_context import ModelRuleContext
from omnibase_core.model.kafka.model_security_context import \
    ModelSecurityContext
from omnibase_core.utils.json_encoder import OmniJSONEncoder


class ModelOnexEnvelopeV1(BaseModel):
    """
    Standardized Kafka event envelope for ONEX intelligence coordination.

    Implements OnexEnvelopeV1 Avro schema with production reliability features:
    - W3C trace context propagation for end-to-end observability
    - Payload signing with service keys for security
    - Flexible payload encoding (JSON, compressed, Avro, Protobuf)
    - Production topic routing with partition strategies
    - Idempotent producer support with retry logic
    - Performance optimization hints for high-volume processing (>1000 events/sec)
    """

    model_config = ConfigDict(
        extra="forbid",  # Strict schema compliance
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)},
    )

    # Core envelope metadata
    envelope_version: str = Field(
        default="1.0.0", description="Schema version for backward compatibility"
    )
    op_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique operation identifier"
    )
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Correlation ID for tracking"
    )

    # W3C Trace Context for distributed tracing
    traceparent: Optional[str] = Field(
        None, description="W3C traceparent header (00-{trace_id}-{span_id}-{flags})"
    )
    tracestate: Optional[str] = Field(
        None, description="W3C tracestate header for vendor-specific data"
    )

    # Event metadata
    timestamp: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Timestamp in milliseconds",
    )
    source_service: str = Field(..., description="Originating service identifier")
    source_node_id: str = Field(
        ..., description="Node identifier where event was generated"
    )
    event_type: str = Field(..., description="Namespaced event type")

    # Payload handling
    payload_type: str = Field(
        ..., description="Type identifier for payload schema validation"
    )
    payload_schema_version: str = Field(
        default="1.0.0", description="Payload schema version"
    )
    payload: bytes = Field(..., description="JSON-encoded event payload")
    content_encoding: ModelContentEncoding = Field(
        default=ModelContentEncoding.JSON, description="Payload encoding"
    )

    # Production features
    priority: ModelEventPriority = Field(
        default=ModelEventPriority.NORMAL, description="Processing priority"
    )
    delivery_guarantee: ModelDeliveryGuarantee = Field(
        default=ModelDeliveryGuarantee.AT_LEAST_ONCE, description="Delivery semantics"
    )
    partition_key: Optional[str] = Field(
        None, description="Custom partition key override"
    )

    # Advanced configuration
    retention_policy: ModelRetentionPolicy = Field(
        default_factory=ModelRetentionPolicy, description="Retention config"
    )
    security: ModelSecurityContext = Field(
        default_factory=ModelSecurityContext, description="Security context"
    )
    routing: ModelRoutingContext = Field(
        default_factory=ModelRoutingContext, description="Routing context"
    )
    performance_hints: ModelPerformanceHints = Field(
        default_factory=ModelPerformanceHints, description="Performance hints"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Extensible metadata"
    )

    @field_validator("traceparent")
    @classmethod
    def validate_traceparent_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate W3C traceparent format: 00-{trace_id}-{span_id}-{flags}"""
        if v is None:
            return v

        parts = v.split("-")
        if len(parts) != 4:
            raise ValueError(
                "traceparent must have format: 00-{trace_id}-{span_id}-{flags}"
            )

        if parts[0] != "00":
            raise ValueError("traceparent version must be '00'")

        if len(parts[1]) != 32 or not all(c in "0123456789abcdef" for c in parts[1]):
            raise ValueError("trace_id must be 32 hex characters")

        if len(parts[2]) != 16 or not all(c in "0123456789abcdef" for c in parts[2]):
            raise ValueError("span_id must be 16 hex characters")

        if len(parts[3]) != 2 or not all(c in "0123456789abcdef" for c in parts[3]):
            raise ValueError("flags must be 2 hex characters")

        return v

    @classmethod
    def from_onex_event(
        cls,
        event: ModelOnexEvent,
        source_service: str,
        payload_type: Optional[str] = None,
        **kwargs,
    ) -> "ModelOnexEnvelopeV1":
        """
        Create envelope from existing ModelOnexEvent.

        Args:
            event: Source ONEX event
            source_service: Originating service identifier
            payload_type: Payload type override
            **kwargs: Additional envelope fields

        Returns:
            OnexEnvelopeV1 instance
        """
        # Serialize event as payload
        payload_data = event.model_dump()
        payload_bytes = json.dumps(payload_data, cls=OmniJSONEncoder).encode("utf-8")

        # Determine payload type
        if payload_type is None:
            payload_type = f"onex_event.{event.get_event_namespace() or 'unknown'}"

        return cls(
            source_service=source_service,
            source_node_id=event.node_id,
            event_type=str(event.event_type),
            payload_type=payload_type,
            payload=payload_bytes,
            correlation_id=(
                str(event.correlation_id) if event.correlation_id else str(uuid4())
            ),
            **kwargs,
        )

    @classmethod
    def create_fs_event(
        cls,
        repo_id: str,
        path: str,
        change_type: str,
        source_service: str = "fs_watcher",
        **kwargs,
    ) -> "ModelOnexEnvelopeV1":
        """Create file system change event with proper partitioning"""
        payload_data = {
            "repo_id": repo_id,
            "path": path,
            "change_type": change_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return cls(
            source_service=source_service,
            source_node_id=f"fs_{repo_id}",
            event_type=f"fs.change.{change_type}",
            payload_type="fs_change_event",
            payload=json.dumps(payload_data, cls=OmniJSONEncoder).encode("utf-8"),
            partition_key=f"{repo_id}:{path}",
            **kwargs,
        )

    @classmethod
    def create_intelligence_result(
        cls,
        result: ModelIntelligenceResult,
        source_service: str = "langextract",
        **kwargs,
    ) -> "ModelOnexEnvelopeV1":
        """Create intelligence analysis result event"""
        payload_data = result.model_dump()

        return cls(
            source_service=source_service,
            source_node_id=f"intelligence_{result.analysis_type}",
            event_type="intelligence.analysis.completed",
            payload_type="intelligence_result",
            payload=json.dumps(payload_data, cls=OmniJSONEncoder).encode("utf-8"),
            partition_key=result.uid,
            **kwargs,
        )

    @classmethod
    def create_rule_decision(
        cls,
        context: ModelRuleContext,
        decision: str,
        source_service: str = "context_rules",
        **kwargs,
    ) -> "ModelOnexEnvelopeV1":
        """Create context rules decision event"""
        payload_data = {
            "rule_id": context.rule_id,
            "decision": decision,
            "context": context.model_dump(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return cls(
            source_service=source_service,
            source_node_id=f"rules_{context.rule_id}",
            event_type=f"rule.decision.{decision}",
            payload_type="rule_decision",
            payload=json.dumps(payload_data, cls=OmniJSONEncoder).encode("utf-8"),
            partition_key=context.rule_id,
            retention_policy=ModelRetentionPolicy(
                compaction_key=context.rule_id
            ),  # Enable compaction for latest decisions
            **kwargs,
        )

    def compress_payload(self) -> "ModelOnexEnvelopeV1":
        """Compress payload using gzip for large events"""
        if self.content_encoding == ModelContentEncoding.JSON:
            compressed_payload = gzip.compress(self.payload)
            self.payload = compressed_payload
            self.content_encoding = ModelContentEncoding.JSON_GZIP
        return self

    def decompress_payload(self) -> "ModelOnexEnvelopeV1":
        """Decompress gzipped payload"""
        if self.content_encoding == ModelContentEncoding.JSON_GZIP:
            decompressed_payload = gzip.decompress(self.payload)
            self.payload = decompressed_payload
            self.content_encoding = ModelContentEncoding.JSON
        return self

    def sign_payload(self, signing_key: str, key_id: str) -> "ModelOnexEnvelopeV1":
        """Sign payload with HMAC-SHA256 for integrity verification"""
        signature = hmac.new(
            signing_key.encode("utf-8"), self.payload, hashlib.sha256
        ).hexdigest()

        self.security.signature = signature
        self.security.signing_key_id = key_id
        return self

    def verify_signature(self, signing_key: str) -> bool:
        """Verify payload signature"""
        if not self.security.signature:
            return False

        expected_signature = hmac.new(
            signing_key.encode("utf-8"), self.payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, self.security.signature)

    def get_payload_json(self) -> ModelPayloadData:
        """Get payload as strongly typed payload data (decompressing if needed)"""
        payload_bytes = self.payload

        if self.content_encoding == ModelContentEncoding.JSON_GZIP:
            payload_bytes = gzip.decompress(payload_bytes)
        elif self.content_encoding != ModelContentEncoding.JSON:
            raise ValueError(
                f"Cannot parse payload with encoding {self.content_encoding}"
            )

        payload_dict = json.loads(payload_bytes.decode("utf-8"))

        # Map payload type to appropriate model
        if self.payload_type == "intelligence_result":
            return ModelPayloadData(
                payload_type=self.payload_type,
                data=ModelIntelligenceResult(**payload_dict),
            )
        elif self.payload_type == "rule_decision":
            context_data = payload_dict.get("context", {})
            return ModelPayloadData(
                payload_type=self.payload_type, data=ModelRuleContext(**context_data)
            )
        else:
            # For other types, use generic string mapping
            return ModelPayloadData(
                payload_type=self.payload_type,
                data=(
                    payload_dict
                    if isinstance(payload_dict, dict)
                    else {"raw": str(payload_dict)}
                ),
            )

    def get_partition_key(self) -> str:
        """Get effective partition key for Kafka"""
        if self.partition_key:
            return self.partition_key

        # Default partition strategies by event type
        if self.event_type.startswith("fs."):
            payload_data = self.get_payload_json()
            if isinstance(payload_data.data, dict):
                repo_id = payload_data.data.get("repo_id", "unknown")
                path = payload_data.data.get("path", "")
                return f"{repo_id}:{path}"
        elif self.event_type.startswith("intelligence."):
            payload_data = self.get_payload_json()
            if isinstance(payload_data.data, ModelIntelligenceResult):
                return payload_data.data.uid
            elif isinstance(payload_data.data, dict):
                return payload_data.data.get("uid", self.op_id)
        elif self.event_type.startswith("rule."):
            payload_data = self.get_payload_json()
            if isinstance(payload_data.data, ModelRuleContext):
                return payload_data.data.rule_id
            elif isinstance(payload_data.data, dict):
                return payload_data.data.get("rule_id", self.op_id)

        return self.op_id

    def get_topic_name(self) -> str:
        """Get appropriate Kafka topic name based on event type"""
        if self.event_type.startswith("fs."):
            return "fs.events"
        elif self.event_type.startswith("intelligence."):
            return "intelligence.results"
        elif self.event_type.startswith("metadata."):
            return "metadata-updates"
        elif self.event_type.startswith("rule."):
            return "rules-decisions"
        else:
            return "onex.events.default.v1"

    def add_trace_context(
        self, trace_id: str, span_id: str, flags: str = "01"
    ) -> "ModelOnexEnvelopeV1":
        """Add W3C trace context for distributed tracing"""
        self.traceparent = f"00-{trace_id}-{span_id}-{flags}"
        return self

    def get_estimated_size_bytes(self) -> int:
        """Estimate serialized size for performance planning"""
        # Rough estimation based on payload size plus envelope overhead
        base_overhead = 1024  # Approximate envelope metadata size
        return len(self.payload) + base_overhead

    def is_high_volume_event(self) -> bool:
        """Check if this is a high-volume event type that needs optimization"""
        high_volume_types = ["fs.change", "intelligence.result", "tool.execution"]
        return any(self.event_type.startswith(prefix) for prefix in high_volume_types)

    def to_avro_dict(self) -> ModelAvroCompatibleData:
        """Convert to Avro-compatible dictionary for serialization"""
        return ModelAvroCompatibleData(
            envelope_version=self.envelope_version,
            op_id=self.op_id,
            correlation_id=self.correlation_id,
            traceparent=self.traceparent,
            tracestate=self.tracestate,
            timestamp=self.timestamp,
            source_service=self.source_service,
            source_node_id=self.source_node_id,
            event_type=self.event_type,
            payload_type=self.payload_type,
            payload_schema_version=self.payload_schema_version,
            payload=self.payload,
            content_encoding=self.content_encoding.value,
            priority=self.priority.value,
            delivery_guarantee=self.delivery_guarantee.value,
            partition_key=self.partition_key,
            metadata=self.metadata,
        )

    def __str__(self) -> str:
        """Human-readable representation"""
        size_kb = len(self.payload) / 1024
        return f"OnexEnvelopeV1[{self.op_id[:8]}] {self.event_type} from {self.source_service} ({size_kb:.1f}KB)"


# Backward compatibility aliases
OnexEnvelopeV1 = ModelOnexEnvelopeV1
