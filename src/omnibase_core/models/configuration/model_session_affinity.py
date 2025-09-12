"""
ModelSessionAffinity - Session affinity configuration for load balancing

Session affinity model for configuring sticky sessions and client-to-node
routing persistence in load balancing systems.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelSessionAffinityMetadata(BaseModel):
    """Metadata for session affinity configuration."""

    # Session tracking
    session_id_format: str = Field(
        "uuid",
        description="Format for session IDs",
        pattern="^(uuid|ulid|nanoid|custom)$",
    )
    include_timestamp: bool = Field(
        True,
        description="Include timestamp in session metadata",
    )

    # Client identification
    include_user_agent: bool = Field(
        True,
        description="Include user agent in affinity calculation",
    )
    include_accept_language: bool = Field(
        False,
        description="Include accept-language header in affinity",
    )
    include_geo_location: bool = Field(
        False,
        description="Include geo-location in affinity calculation",
    )

    # Session persistence
    persist_across_restarts: bool = Field(
        False,
        description="Persist affinity data across server restarts",
    )
    storage_backend: str | None = Field(
        None,
        description="Storage backend for persistent affinity",
        pattern="^(redis|memcached|dynamodb|custom)$",
    )

    # Load balancing hints
    preferred_node_tags: list[str] = Field(
        default_factory=list,
        description="Preferred node tags for affinity",
    )
    excluded_node_tags: list[str] = Field(
        default_factory=list,
        description="Node tags to exclude from affinity",
    )

    # Failover behavior
    failover_priority: list[str] = Field(
        default_factory=list,
        description="Failover node priority order",
    )
    preserve_session_data: bool = Field(
        True,
        description="Preserve session data during failover",
    )

    # Monitoring
    track_session_metrics: bool = Field(True, description="Track session-level metrics")
    metrics_sampling_rate: float = Field(
        1.0,
        description="Sampling rate for session metrics",
        ge=0.0,
        le=1.0,
    )

    # Custom extensions
    custom_extractors: dict[str, str] = Field(
        default_factory=dict,
        description="Custom field extractors (name: regex)",
    )


class ModelSessionAffinity(BaseModel):
    """
    Session affinity configuration for load balancing

    This model defines how client sessions should be maintained and routed
    to specific nodes to ensure session persistence.
    """

    enabled: bool = Field(
        default=False,
        description="Whether session affinity is enabled",
    )

    affinity_type: str = Field(
        default="cookie",
        description="Type of session affinity",
        pattern="^(cookie|ip_hash|header|query_param|custom)$",
    )

    cookie_name: str | None = Field(
        None,
        description="Cookie name for cookie-based affinity",
    )

    cookie_ttl_seconds: int | None = Field(
        None,
        description="Cookie TTL in seconds",
        ge=60,
        le=86400,  # 24 hours max
    )

    cookie_domain: str | None = Field(None, description="Cookie domain for affinity")

    cookie_path: str | None = Field(None, description="Cookie path for affinity")

    cookie_secure: bool = Field(
        default=True,
        description="Whether affinity cookie should be secure",
    )

    cookie_http_only: bool = Field(
        default=True,
        description="Whether affinity cookie should be HTTP-only",
    )

    header_name: str | None = Field(
        None,
        description="Header name for header-based affinity",
    )

    query_param_name: str | None = Field(
        None,
        description="Query parameter name for query-based affinity",
    )

    hash_algorithm: str = Field(
        default="sha256",
        description="Hash algorithm for IP/header hashing",
        pattern="^(md5|sha1|sha256|sha512)$",
    )

    session_timeout_seconds: int | None = Field(
        None,
        description="Session timeout in seconds",
        ge=300,  # 5 minutes minimum
        le=86400,  # 24 hours maximum
    )

    failover_enabled: bool = Field(
        default=True,
        description="Whether to failover sessions when target node is unhealthy",
    )

    sticky_on_failure: bool = Field(
        default=False,
        description="Whether to maintain stickiness even when target node fails",
    )

    max_retries_before_failover: int = Field(
        default=3,
        description="Maximum retries on target node before failover",
        ge=1,
        le=10,
    )

    custom_affinity_function: str | None = Field(
        None,
        description="Custom function name for affinity calculation",
    )

    affinity_metadata: ModelSessionAffinityMetadata = Field(
        default_factory=ModelSessionAffinityMetadata,
        description="Additional affinity metadata",
    )

    def get_affinity_key(
        self,
        client_ip: str = "",
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> str | None:
        """Extract affinity key from request components"""
        if not self.enabled:
            return None

        headers = headers or {}
        query_params = query_params or {}
        cookies = cookies or {}

        if self.affinity_type == "ip_hash":
            return client_ip
        if self.affinity_type == "cookie" and self.cookie_name:
            return cookies.get(self.cookie_name)
        if self.affinity_type == "header" and self.header_name:
            return headers.get(self.header_name)
        if self.affinity_type == "query_param" and self.query_param_name:
            return query_params.get(self.query_param_name)

        return None

    def calculate_node_hash(
        self,
        affinity_key: str,
        available_nodes: list[str],
    ) -> str | None:
        """Calculate target node based on affinity key"""
        if not affinity_key or not available_nodes:
            return None

        import hashlib

        # Create hash of affinity key
        if self.hash_algorithm == "md5":
            hash_obj = hashlib.md5(affinity_key.encode())
        elif self.hash_algorithm == "sha1":
            hash_obj = hashlib.sha1(affinity_key.encode())
        elif self.hash_algorithm == "sha256":
            hash_obj = hashlib.sha256(affinity_key.encode())
        elif self.hash_algorithm == "sha512":
            hash_obj = hashlib.sha512(affinity_key.encode())
        else:
            return None

        # Convert to integer and select node
        hash_int = int(hash_obj.hexdigest(), 16)
        node_index = hash_int % len(available_nodes)
        return available_nodes[node_index]

    def should_create_affinity(self, existing_affinity: str | None) -> bool:
        """Check if new affinity should be created"""
        return self.enabled and existing_affinity is None

    def should_maintain_affinity(self, target_node_healthy: bool) -> bool:
        """Check if affinity should be maintained despite node health"""
        if not self.enabled:
            return False

        if target_node_healthy:
            return True

        return self.sticky_on_failure

    def get_cookie_attributes(self) -> dict[str, Any]:
        """Get cookie attributes for affinity cookie"""
        if not self.enabled or self.affinity_type != "cookie":
            return {}

        attrs: dict[str, Any] = {
            "secure": self.cookie_secure,
            "httponly": self.cookie_http_only,
        }

        if self.cookie_ttl_seconds:
            attrs["max_age"] = self.cookie_ttl_seconds
        if self.cookie_domain:
            attrs["domain"] = self.cookie_domain
        if self.cookie_path:
            attrs["path"] = self.cookie_path

        return attrs

    @classmethod
    def create_cookie_affinity(
        cls,
        cookie_name: str = "ONEX_NODE_AFFINITY",
        ttl_seconds: int = 3600,
    ) -> "ModelSessionAffinity":
        """Create cookie-based session affinity"""
        return cls(
            enabled=True,
            affinity_type="cookie",
            cookie_name=cookie_name,
            cookie_ttl_seconds=ttl_seconds,
            cookie_secure=True,
            cookie_http_only=True,
            failover_enabled=True,
        )

    @classmethod
    def create_ip_hash_affinity(
        cls,
        hash_algorithm: str = "sha256",
    ) -> "ModelSessionAffinity":
        """Create IP hash-based session affinity"""
        return cls(
            enabled=True,
            affinity_type="ip_hash",
            hash_algorithm=hash_algorithm,
            failover_enabled=True,
        )

    @classmethod
    def create_header_affinity(cls, header_name: str) -> "ModelSessionAffinity":
        """Create header-based session affinity"""
        return cls(
            enabled=True,
            affinity_type="header",
            header_name=header_name,
            failover_enabled=True,
        )

    @classmethod
    def create_disabled(cls) -> "ModelSessionAffinity":
        """Create disabled session affinity configuration"""
        return cls(enabled=False)
