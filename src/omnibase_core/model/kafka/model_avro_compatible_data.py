"""ModelAvroCompatibleData: Avro-compatible envelope data structure"""

from typing import Dict, Optional

from pydantic import BaseModel


class ModelAvroCompatibleData(BaseModel):
    """Avro-compatible envelope data structure"""

    envelope_version: str
    op_id: str
    correlation_id: str
    traceparent: Optional[str] = None
    tracestate: Optional[str] = None
    timestamp: int
    source_service: str
    source_node_id: str
    event_type: str
    payload_type: str
    payload_schema_version: str
    payload: bytes
    content_encoding: str
    priority: str
    delivery_guarantee: str
    partition_key: Optional[str] = None
    metadata: Dict[str, str]
