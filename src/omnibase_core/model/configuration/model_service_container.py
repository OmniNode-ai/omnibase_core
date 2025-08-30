"""
Service container model.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelServiceContainer(BaseModel):
    """Service container configuration."""

    image: str = Field(..., description="Container image")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    ports: Optional[List[str]] = Field(None, description="Exposed ports")
    volumes: Optional[List[str]] = Field(None, description="Volume mounts")
    options: Optional[str] = Field(None, description="Container options")
    credentials: Optional[Dict[str, str]] = Field(
        None, description="Registry credentials"
    )
