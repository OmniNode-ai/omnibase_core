#!/usr/bin/env python3
"""
Consul Adapter Models Package.

Strongly typed Pydantic models for consul adapter responses.
Tool-specific models following canonical ONEX pattern.
"""

from .model_consul_adapter_input import ModelConsulAdapterInput
from .model_consul_adapter_output import ModelConsulAdapterOutput
from .model_consul_response import (
    ModelConsulAdapterHealth,
    ModelConsulHealthCheck,
    ModelConsulHealthCheckNode,
    ModelConsulHealthResponse,
    ModelConsulHealthStatus,
    ModelConsulKVResponse,
    ModelConsulServiceInfo,
    ModelConsulServiceListResponse,
    ModelConsulServiceRegistration,
    ModelConsulServiceResponse,
)

__all__ = [
    "ModelConsulAdapterInput",
    "ModelConsulAdapterOutput",
    "ModelConsulAdapterHealth",
    "ModelConsulHealthCheck",
    "ModelConsulHealthCheckNode",
    "ModelConsulHealthResponse",
    "ModelConsulHealthStatus",
    "ModelConsulKVResponse",
    "ModelConsulServiceInfo",
    "ModelConsulServiceListResponse",
    "ModelConsulServiceRegistration",
    "ModelConsulServiceResponse",
]
