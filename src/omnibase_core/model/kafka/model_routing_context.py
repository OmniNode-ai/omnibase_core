"""ModelRoutingContext: Routing context for cross-component coordination"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelRoutingContext(BaseModel):
    """Routing context for cross-component coordination"""

    target_services: List[str] = Field(
        default_factory=list, description="List of target service identifiers"
    )
    routing_hints: Dict[str, str] = Field(
        default_factory=dict, description="Key-value routing hints"
    )
    reply_to_topic: Optional[str] = Field(None, description="Topic for response events")
