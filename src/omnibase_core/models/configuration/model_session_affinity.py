from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_session_affinity_metadata import (
    ModelSessionAffinityMetadata,
)

"""
ModelSessionAffinity - Session affinity configuration for load balancing

Session affinity model for configuring sticky sessions and client-to-node
routing persistence in load balancing systems.
"""


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
        default=None,
        description="Cookie name for cookie-based affinity",
    )

    cookie_ttl_seconds: int | None = Field(
        default=None,
        description="Cookie TTL in seconds",
        ge=60,
        le=86400,  # 24 hours max
    )

    cookie_domain: str | None = Field(
        default=None, description="Cookie domain for affinity"
    )

    cookie_path: str | None = Field(
        default=None, description="Cookie path for affinity"
    )

    cookie_secure: bool = Field(
        default=True,
        description="Whether affinity cookie should be secure",
    )

    cookie_http_only: bool = Field(
        default=True,
        description="Whether affinity cookie should be HTTP-only",
    )

    header_name: str | None = Field(
        default=None,
        description="Header name for header-based affinity",
    )

    query_param_name: str | None = Field(
        default=None,
        description="Query parameter name for query-based affinity",
    )

    hash_algorithm: str = Field(
        default="sha256",
        description="Hash algorithm for IP/header hashing (sha256 recommended, md5/sha1 deprecated)",
        pattern="^(md5|sha1|sha256|sha512)$",
    )

    session_timeout_seconds: int | None = Field(
        default=None,
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
        default=None,
        description="Custom function name for affinity calculation",
    )

    affinity_metadata: ModelSessionAffinityMetadata = Field(
        default_factory=lambda: ModelSessionAffinityMetadata(),
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
        import warnings

        # Create hash of affinity key
        if self.hash_algorithm == "md5":
            warnings.warn(
                "MD5 hash algorithm is deprecated and insecure. Use SHA256 or SHA512 instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            hash_obj = hashlib.md5(affinity_key.encode())
        elif self.hash_algorithm == "sha1":
            warnings.warn(
                "SHA1 hash algorithm is deprecated and insecure. Use SHA256 or SHA512 instead.",
                DeprecationWarning,
                stacklevel=2,
            )
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
