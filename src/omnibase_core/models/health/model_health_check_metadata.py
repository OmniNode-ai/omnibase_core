"""
Health Check Metadata Model

Type-safe health check metadata that replaces Dict[str, Any] usage.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Use TYPE_CHECKING guard to break circular import:
# services → ... → health.model_health_check_metadata → services.model_custom_fields
# → services.model_error_details [cycle back to services during __init__.py loading]
if TYPE_CHECKING:
    from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelHealthCheckMetadata(BaseModel):
    """
    Type-safe health check metadata.

    Provides structured metadata for health check configuration.
    """

    # Check identification
    check_name: str | None = Field(default=None, description="Health check name")
    check_version: ModelSemVer | None = Field(
        default=None, description="Health check version"
    )
    check_description: str | None = Field(
        default=None,
        description="Health check description",
    )

    # Check categorization
    check_type: str | None = Field(
        default=None,
        description="Type of check (http, tcp, custom)",
    )
    check_category: str | None = Field(
        default=None,
        description="Check category (basic, detailed, diagnostic)",
    )
    check_tags: list[str] = Field(
        default_factory=list,
        description="Tags for check organization",
    )

    # Business context
    business_impact: str | None = Field(
        default=None,
        description="Business impact if check fails",
    )
    sla_critical: bool = Field(
        default=False, description="Whether this check affects SLA"
    )

    # Technical details
    expected_response_time_ms: int | None = Field(
        default=None,
        description="Expected response time",
    )
    max_retries: int | None = Field(default=None, description="Maximum retry attempts")
    retry_delay_ms: int | None = Field(
        default=None, description="Delay between retries"
    )

    # Dependencies
    depends_on_checks: list[str] = Field(
        default_factory=list,
        description="Other checks this depends on",
    )
    dependent_services: list[str] = Field(
        default_factory=list,
        description="Services that depend on this check",
    )

    # Alert configuration
    alert_on_failure: bool = Field(
        default=True, description="Whether to alert on failure"
    )
    alert_channels: list[str] = Field(
        default_factory=list,
        description="Alert channels (email, slack, pager)",
    )
    alert_cooldown_minutes: int | None = Field(
        default=None,
        description="Cooldown between alerts",
    )

    # Custom fields for extensibility
    # Use string annotation for forward reference (TYPE_CHECKING import)
    custom_fields: "ModelCustomFields | None" = Field(
        default=None,
        description="Additional custom metadata",
    )


# Resolve forward reference for custom_fields field.
# This is done at module level to ensure the forward reference is resolved
# regardless of how the module is imported (directly or via __init__.py).
# The import is deferred until after the class is fully defined to avoid
# the circular import that would occur at the top of the file.
def _resolve_forward_references() -> None:
    """Resolve forward references for ModelHealthCheckMetadata."""
    try:
        # Import ModelCustomFields at runtime (after class definition)
        # This import is safe here because the class is fully defined
        from omnibase_core.models.services.model_custom_fields import (
            ModelCustomFields,
        )

        # Explicitly rebuild with the imported type in the namespace
        # This ensures the forward reference 'ModelCustomFields' is resolved
        ModelHealthCheckMetadata.model_rebuild(
            _types_namespace={"ModelCustomFields": ModelCustomFields}
        )
    except ImportError:
        # init-errors-ok: Import may fail during early module loading
        # The forward reference will be resolved when health/__init__.py completes
        pass
    except Exception:
        # init-errors-ok: model_rebuild may fail during circular import resolution
        # This is safe to ignore as the forward reference will be resolved
        # when the full module graph is loaded
        pass


# Attempt to resolve forward references at module load time.
# This may fail during circular import resolution, which is fine -
# the health/__init__.py will resolve it after all modules are loaded.
_resolve_forward_references()
