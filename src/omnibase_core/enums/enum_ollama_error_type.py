"""
Ollama-specific error type enum.

Provides strongly-typed error types for Ollama LLM inference
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumOllamaErrorType(str, Enum):
    """Ollama-specific error types."""

    TIMEOUT = "timeout"
    CONNECTION = "connection"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
