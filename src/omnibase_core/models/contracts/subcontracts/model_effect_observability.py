"""
Effect Observability Model.

Observability configuration for effect operations.
Controls logging, metrics emission, and trace propagation.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectObservability"]


class ModelEffectObservability(BaseModel):
    """
    Observability configuration for effect operations.

    Controls logging, metrics emission, and distributed trace propagation
    for effect operations. These settings apply to all operations in the
    subcontract unless overridden at the operation level.

    Security Note:
        Response logging (log_response=True) may capture sensitive data such as
        API responses, database query results, or file contents. Enable only
        when necessary and ensure proper log sanitization is in place.

    Attributes:
        log_request: Whether to log outgoing request details (URL, method, headers).
            Defaults to True for debugging and audit purposes.
        log_response: Whether to log response content. Defaults to False to avoid
            capturing sensitive data. Enable with caution.
        emit_metrics: Whether to emit operation metrics (latency, success/failure,
            retry counts). Defaults to True for operational visibility.
        trace_propagation: Whether to propagate distributed trace context (e.g.,
            OpenTelemetry traceparent header). Defaults to True for end-to-end
            request tracing.

    Example:
        >>> observability = ModelEffectObservability(
        ...     log_request=True,
        ...     log_response=False,  # Avoid logging sensitive data
        ...     emit_metrics=True,
        ...     trace_propagation=True,
        ... )

    See Also:
        - ModelEffectSubcontract.observability: Subcontract-level observability settings
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    log_request: bool = Field(default=True)
    log_response: bool = Field(default=False, description="May contain sensitive data")
    emit_metrics: bool = Field(default=True)
    trace_propagation: bool = Field(default=True)
