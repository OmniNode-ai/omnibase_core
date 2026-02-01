"""
Sandbox Requirements Model.

Defines resource constraints and permission requirements for handler sandboxing.
This model specifies what resources a handler needs to operate within a sandboxed
environment.

Design Principles:
    - Declarative: Specifies requirements, not enforcement (runtime enforces)
    - Minimal by default: All permissions default to restrictive settings
    - Validatable: All constraints are validated at model creation time

Validation Bounds (v1):
    - memory_limit_mb: 64 MB - 256 GB (262144 MB)
    - cpu_limit_cores: 0.1 - 256 cores
    - allowed_domains: Valid hostnames, wildcard only at leftmost label

Thread Safety:
    ModelSandboxRequirements is immutable (frozen=True) after creation.
    Thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.handlers.model_sandbox_requirements import (
    ...     ModelSandboxRequirements,
    ... )
    >>> # Minimal sandbox (no network, no filesystem)
    >>> minimal = ModelSandboxRequirements()
    >>> minimal.requires_network
    False

    >>> # Handler that needs network access to specific domains
    >>> network_handler = ModelSandboxRequirements(
    ...     requires_network=True,
    ...     allowed_domains=["api.example.com", "*.storage.example.com"],
    ...     memory_limit_mb=512,
    ... )

See Also:
    - ModelHandlerPackaging: Uses sandbox requirements for handler distribution
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Domain validation constants
_MIN_MEMORY_MB = 64
_MAX_MEMORY_MB = 262144  # 256 GB
_MIN_CPU_CORES = 0.1
_MAX_CPU_CORES = 256.0

# Hostname pattern: alphanumeric, hyphens allowed (not at start/end of label)
# Supports optional wildcard at leftmost label only
_DOMAIN_LABEL_PATTERN = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")
_WILDCARD_PREFIX = "*."


def _validate_domain(domain: str) -> bool:
    """
    Validate a domain string for sandbox allowed_domains.

    Rules:
        - Must be a valid hostname (labels separated by dots)
        - Each label: alphanumeric, may contain hyphens (not at start/end)
        - Wildcard (*.) allowed ONLY at leftmost position
        - No IP literals (see rationale below)
        - No scheme (http://) or path (/foo)

    IP Literal Policy:
        IP literals (e.g., 192.168.1.1, [::1]) are NOT allowed in allowed_domains.
        This is intentional and differs from artifact_reference (which allows IPs):

        - **allowed_domains** is a security allowlist for network access control.
          Domains have clear ownership and can be verified via DNS/TLS certificates.
          IP addresses lack this trust chain and could be spoofed or reassigned.

        - **artifact_reference** is a location specifier for fetching artifacts.
          IPs are allowed there because artifact integrity is verified via hash,
          not network trust. Private registries often use IP addresses.

        For handlers that need to access IP-based services, either:
        1. Use a domain name that resolves to the IP
        2. Set allowed_domains to empty list (allows all) with requires_network=True

    Args:
        domain: Domain string to validate

    Returns:
        True if valid, False otherwise
    """
    if not domain:
        return False

    # No schemes or paths
    if "://" in domain or "/" in domain:
        return False

    # Handle wildcard prefix
    if domain.startswith(_WILDCARD_PREFIX):
        # Remove wildcard prefix for label validation
        remaining = domain[2:]  # Remove "*."
        # Cannot have nested wildcards (*.*.example.com)
        if "*" in remaining:
            return False
        labels = remaining.split(".")
    else:
        # No wildcards allowed elsewhere
        if "*" in domain:
            return False
        labels = domain.split(".")

    # Must have at least one label after wildcard (if present) or two labels total
    if not labels or all(not label for label in labels):
        return False

    # Validate each label
    for label in labels:
        if not label:
            # Empty label (consecutive dots)
            return False
        if not _DOMAIN_LABEL_PATTERN.match(label):
            return False

    return True


class ModelSandboxRequirements(BaseModel):
    """
    Resource constraints and permission requirements for handler sandboxing.

    This model defines what a handler needs to operate within a sandboxed
    environment. All fields default to restrictive settings (no network,
    no filesystem access, no special resources).

    The sandbox requirements are declarative - they specify what the handler
    needs, but enforcement is performed by the runtime sandbox implementation.

    Attributes:
        requires_network: Whether the handler needs network access. When True,
            the handler may make outbound network connections. Default False.
        requires_filesystem: Whether the handler needs filesystem access beyond
            its designated working directory. Default False.
        allowed_domains: List of domains the handler may access when network
            is enabled. Supports wildcard at leftmost label only (e.g.,
            "*.example.com"). Empty list means no domain restrictions when
            requires_network is True.
        memory_limit_mb: Maximum memory allocation in megabytes. Range: 64-262144.
            None means no explicit limit (runtime default applies).
        cpu_limit_cores: Maximum CPU cores allocation. Range: 0.1-256.
            None means no explicit limit (runtime default applies).

    Example:
        >>> # Isolated compute handler (default - most restrictive)
        >>> isolated = ModelSandboxRequirements()
        >>> isolated.requires_network
        False

        >>> # Handler that calls external APIs
        >>> api_client = ModelSandboxRequirements(
        ...     requires_network=True,
        ...     allowed_domains=["api.github.com", "*.googleapis.com"],
        ...     memory_limit_mb=1024,
        ...     cpu_limit_cores=2.0,
        ... )

        >>> # High-memory compute handler
        >>> compute_heavy = ModelSandboxRequirements(
        ...     requires_filesystem=True,  # Needs temp file access
        ...     memory_limit_mb=16384,     # 16 GB
        ...     cpu_limit_cores=8.0,
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    requires_network: bool = Field(
        default=False,
        description=(
            "Whether the handler requires network access. When False (default), "
            "the handler operates in network-isolated mode."
        ),
    )

    requires_filesystem: bool = Field(
        default=False,
        description=(
            "Whether the handler requires filesystem access beyond its working "
            "directory. When False (default), filesystem access is restricted."
        ),
    )

    allowed_domains: list[str] = Field(
        default_factory=list,
        description=(
            "List of domains the handler may access when requires_network=True. "
            "Supports wildcard at leftmost label only (e.g., '*.example.com'). "
            "Empty list with requires_network=True means no domain restrictions."
        ),
    )

    memory_limit_mb: int | None = Field(
        default=None,
        description=(
            f"Maximum memory allocation in megabytes. "
            f"Range: {_MIN_MEMORY_MB}-{_MAX_MEMORY_MB} MB. "
            f"None means runtime default applies."
        ),
        ge=_MIN_MEMORY_MB,
        le=_MAX_MEMORY_MB,
    )

    cpu_limit_cores: float | None = Field(
        default=None,
        description=(
            f"Maximum CPU cores allocation. "
            f"Range: {_MIN_CPU_CORES}-{_MAX_CPU_CORES} cores. "
            f"None means runtime default applies."
        ),
        ge=_MIN_CPU_CORES,
        le=_MAX_CPU_CORES,
    )

    @field_validator("allowed_domains", mode="after")
    @classmethod
    def validate_allowed_domains(cls, domains: list[str]) -> list[str]:
        """Validate that all domains are valid hostnames or wildcards."""
        invalid_domains = []
        for domain in domains:
            if not _validate_domain(domain):
                invalid_domains.append(domain)

        if invalid_domains:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid domain(s) in allowed_domains: {invalid_domains}. "
                    f"Domains must be valid hostnames. Wildcard (*.) is allowed "
                    f"only at the leftmost label (e.g., '*.example.com'). "
                    f"IP literals (e.g., 192.168.1.1, [::1]), schemes (http://), "
                    f"and paths (/foo) are not allowed. For IP-based access, use "
                    f"an empty allowed_domains list with requires_network=True."
                ),
            )
        return domains

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        parts = []
        if self.requires_network:
            parts.append("network=True")
            if self.allowed_domains:
                parts.append(f"domains={len(self.allowed_domains)}")
        if self.requires_filesystem:
            parts.append("filesystem=True")
        if self.memory_limit_mb:
            parts.append(f"mem={self.memory_limit_mb}MB")
        if self.cpu_limit_cores:
            parts.append(f"cpu={self.cpu_limit_cores}")
        return f"ModelSandboxRequirements({', '.join(parts) or 'isolated'})"


__all__ = ["ModelSandboxRequirements"]
