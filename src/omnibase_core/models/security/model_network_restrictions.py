"""
Network Restrictions Model

Typed model for network access restrictions,
replacing Dict[str, Any] with structured fields.
"""

from pydantic import BaseModel, Field


class ModelNetworkRestrictions(BaseModel):
    """
    Structured network access restrictions configuration.

    Defines IP ranges, ports, protocols, and geographic restrictions
    for network access control.
    """

    # IP-based restrictions
    allowed_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Allowed IP ranges in CIDR notation (e.g., 192.168.1.0/24)",
    )

    blocked_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Blocked IP ranges in CIDR notation",
    )

    whitelist_mode: bool = Field(
        default=False,
        description="If true, only allowed IPs can connect (deny all others)",
    )

    # Port restrictions
    allowed_ports: list[int] = Field(
        default_factory=lambda: [443, 8443],
        description="Allowed network ports",
    )

    blocked_ports: list[int] = Field(
        default_factory=lambda: [21, 22, 23, 25, 110, 139, 445],
        description="Blocked network ports",
    )

    # Protocol restrictions
    allowed_protocols: list[str] = Field(
        default_factory=lambda: ["https", "wss"],
        description="Allowed network protocols",
    )

    blocked_protocols: list[str] = Field(
        default_factory=lambda: ["http", "ftp", "telnet"],
        description="Blocked network protocols",
    )

    # Geographic restrictions
    geo_blocking_enabled: bool = Field(
        default=False,
        description="Enable geographic-based blocking",
    )

    allowed_countries: list[str] = Field(
        default_factory=list,
        description="Allowed countries (ISO 3166-1 alpha-2 codes)",
    )

    blocked_countries: list[str] = Field(
        default_factory=list,
        description="Blocked countries (ISO 3166-1 alpha-2 codes)",
    )

    allowed_regions: list[str] = Field(
        default_factory=list,
        description="Allowed regions/states",
    )

    blocked_regions: list[str] = Field(
        default_factory=list,
        description="Blocked regions/states",
    )

    # DNS restrictions
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="Allowed domain names for connections",
    )

    blocked_domains: list[str] = Field(
        default_factory=list,
        description="Blocked domain names",
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")

    requests_per_minute: int | None = Field(
        default=60,
        description="Maximum requests per minute per IP",
        ge=1,
    )

    requests_per_hour: int | None = Field(
        default=1000,
        description="Maximum requests per hour per IP",
        ge=1,
    )

    burst_size: int = Field(
        default=10,
        description="Burst size for rate limiting",
        ge=1,
    )

    # Connection limits
    max_connections_per_ip: int | None = Field(
        default=10,
        description="Maximum concurrent connections per IP",
        ge=1,
    )

    max_total_connections: int | None = Field(
        default=1000,
        description="Maximum total concurrent connections",
        ge=1,
    )

    connection_timeout_seconds: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=1,
    )

    # VPN/Proxy detection
    block_vpn_connections: bool = Field(
        default=False,
        description="Block connections from known VPNs",
    )

    block_proxy_connections: bool = Field(
        default=False,
        description="Block connections from known proxies",
    )

    block_tor_connections: bool = Field(
        default=False,
        description="Block connections from Tor network",
    )

    # Additional security
    require_reverse_dns: bool = Field(
        default=False,
        description="Require valid reverse DNS for connections",
    )

    block_cloud_providers: bool = Field(
        default=False,
        description="Block connections from cloud provider IP ranges",
    )

    block_hosting_providers: bool = Field(
        default=False,
        description="Block connections from hosting provider IP ranges",
    )

    # Exceptions
    exception_ips: list[str] = Field(
        default_factory=list,
        description="IPs exempt from all restrictions",
    )

    exception_tokens: list[str] = Field(
        default_factory=list,
        description="Access tokens that bypass restrictions",
    )

    def is_ip_allowed(self, ip: str) -> bool:
        """Check if an IP address is allowed (simplified logic)."""
        # Note: Simplified IP check - production version would use ipaddress module for proper validation
        if ip in self.exception_ips:
            return True
        if self.whitelist_mode:
            return any(ip in range_str for range_str in self.allowed_ip_ranges)
        return not any(ip in range_str for range_str in self.blocked_ip_ranges)

    def is_country_allowed(self, country_code: str) -> bool:
        """Check if a country is allowed."""
        if not self.geo_blocking_enabled:
            return True
        if self.allowed_countries:
            return country_code in self.allowed_countries
        return country_code not in self.blocked_countries

    @classmethod
    def create_open(cls) -> "ModelNetworkRestrictions":
        """Create open network policy (minimal restrictions)."""
        return cls(
            rate_limit_enabled=False,
            geo_blocking_enabled=False,
            block_vpn_connections=False,
            block_proxy_connections=False,
            block_tor_connections=False,
        )

    @classmethod
    def create_standard(cls) -> "ModelNetworkRestrictions":
        """Create standard network restrictions."""
        return cls()  # Use defaults

    @classmethod
    def create_restricted(cls) -> "ModelNetworkRestrictions":
        """Create restricted network policy."""
        return cls(
            whitelist_mode=True,
            allowed_ip_ranges=["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
            geo_blocking_enabled=True,
            allowed_countries=["US", "CA", "GB", "AU"],
            block_vpn_connections=True,
            block_proxy_connections=True,
            requests_per_minute=30,
            max_connections_per_ip=5,
        )

    @classmethod
    def create_maximum(cls) -> "ModelNetworkRestrictions":
        """Create maximum security network restrictions."""
        return cls(
            whitelist_mode=True,
            allowed_ip_ranges=[],  # Must be explicitly configured
            allowed_ports=[443],
            allowed_protocols=["https"],
            geo_blocking_enabled=True,
            allowed_countries=["US"],
            rate_limit_enabled=True,
            requests_per_minute=10,
            requests_per_hour=100,
            burst_size=5,
            max_connections_per_ip=2,
            connection_timeout_seconds=10,
            block_vpn_connections=True,
            block_proxy_connections=True,
            block_tor_connections=True,
            require_reverse_dns=True,
            block_cloud_providers=True,
            block_hosting_providers=True,
        )
