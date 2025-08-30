#!/usr/bin/env python3
"""
ONEX Sandbox Environment Model.

Defines the structure and constraints for secure agent sandbox environments
with comprehensive security policies and resource limitations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class EnumSandboxLanguage(str, Enum):
    """Supported sandbox execution languages."""

    PYTHON = "python"
    NODEJS = "nodejs"
    SHELL = "shell"
    CUSTOM = "custom"


class EnumSandboxSecurityLevel(str, Enum):
    """Sandbox security isolation levels."""

    MINIMAL = "minimal"  # Basic container isolation
    STANDARD = "standard"  # Standard hardening (default)
    STRICT = "strict"  # Maximum security hardening
    PARANOID = "paranoid"  # Ultra-secure with minimal capabilities


class EnumSandboxNetworkPolicy(str, Enum):
    """Network access policies for sandboxes."""

    NONE = "none"  # No network access
    LOCALHOST = "localhost"  # Local network only
    WHITELIST = "whitelist"  # Whitelist-based external access
    RESTRICTED = "restricted"  # Limited external access


class ModelSandboxResourceLimits(BaseModel):
    """Resource limits for sandbox environments."""

    cpu_cores: float = Field(
        default=0.5, ge=0.1, le=2.0, description="Maximum CPU cores (0.1-2.0)"
    )

    memory_mb: int = Field(
        default=512, ge=128, le=2048, description="Maximum memory in MB (128-2048)"
    )

    disk_mb: int = Field(
        default=1024, ge=256, le=5120, description="Maximum disk space in MB (256-5120)"
    )

    network_bandwidth_mbps: float = Field(
        default=10.0,
        ge=1.0,
        le=100.0,
        description="Network bandwidth limit in Mbps (1.0-100.0)",
    )

    execution_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Maximum execution time in seconds (30-1800)",
    )

    max_file_descriptors: int = Field(
        default=1024,
        ge=256,
        le=4096,
        description="Maximum open file descriptors (256-4096)",
    )

    max_processes: int = Field(
        default=32, ge=1, le=128, description="Maximum number of processes (1-128)"
    )


class ModelSandboxSecurityPolicy(BaseModel):
    """Security policies for sandbox isolation."""

    security_level: EnumSandboxSecurityLevel = Field(
        default=EnumSandboxSecurityLevel.STANDARD,
        description="Security isolation level",
    )

    network_policy: EnumSandboxNetworkPolicy = Field(
        default=EnumSandboxNetworkPolicy.NONE, description="Network access policy"
    )

    readonly_filesystem: bool = Field(
        default=True, description="Mount root filesystem as read-only"
    )

    drop_all_capabilities: bool = Field(
        default=True, description="Drop all Linux capabilities"
    )

    no_new_privileges: bool = Field(
        default=True, description="Prevent privilege escalation"
    )

    use_seccomp_profile: bool = Field(
        default=True, description="Use seccomp security profile"
    )

    use_apparmor_profile: bool = Field(
        default=False, description="Use AppArmor security profile"
    )

    allowed_syscalls: Optional[List[str]] = Field(
        default=None, description="Whitelist of allowed system calls"
    )

    blocked_syscalls: Optional[List[str]] = Field(
        default_factory=lambda: [
            "mount",
            "umount",
            "pivot_root",
            "chroot",
            "clone",
            "unshare",
            "setns",
            "ptrace",
            "process_vm_readv",
            "process_vm_writev",
        ],
        description="Blacklist of blocked system calls",
    )

    environment_whitelist: Optional[List[str]] = Field(
        default_factory=lambda: [
            "PATH",
            "HOME",
            "USER",
            "LANG",
            "LC_ALL",
            "PYTHONPATH",
            "NODE_PATH",
            "SHELL",
        ],
        description="Allowed environment variables",
    )


class ModelSandboxEnvironment(BaseModel):
    """Complete sandbox environment configuration."""

    sandbox_id: UUID = Field(description="Unique identifier for the sandbox instance")

    agent_id: UUID = Field(description="ID of the agent requesting the sandbox")

    language: EnumSandboxLanguage = Field(
        description="Programming language runtime for the sandbox"
    )

    base_image: str = Field(description="Docker base image for the sandbox environment")

    resource_limits: ModelSandboxResourceLimits = Field(
        default_factory=ModelSandboxResourceLimits,
        description="Resource constraints for the sandbox",
    )

    security_policy: ModelSandboxSecurityPolicy = Field(
        default_factory=ModelSandboxSecurityPolicy,
        description="Security policies and restrictions",
    )

    environment_variables: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables for the sandbox"
    )

    package_requirements: List[str] = Field(
        default_factory=list, description="Package dependencies to install"
    )

    working_directory: str = Field(
        default="/workspace", description="Working directory inside the sandbox"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Sandbox creation timestamp"
    )

    expires_at: Optional[datetime] = Field(
        default=None, description="Sandbox expiration timestamp"
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata for the sandbox"
    )

    @validator("base_image")
    def validate_base_image(cls, v):
        """Validate that base image follows security standards."""
        allowed_bases = {
            EnumSandboxLanguage.PYTHON: ["python:3.11-slim", "python:3.12-slim"],
            EnumSandboxLanguage.NODEJS: ["node:18-slim", "node:20-slim"],
            EnumSandboxLanguage.SHELL: ["ubuntu:22.04", "alpine:3.18"],
        }

        # For now, just validate format
        if not v or ":" not in v:
            raise ValueError("Base image must include tag (e.g., 'python:3.11-slim')")

        return v

    @validator("environment_variables")
    def validate_environment_variables(cls, v, values):
        """Validate environment variables against security policy."""
        if "security_policy" in values:
            policy = values["security_policy"]
            if policy.environment_whitelist:
                for key in v.keys():
                    if key not in policy.environment_whitelist:
                        raise ValueError(
                            f"Environment variable '{key}' not in whitelist"
                        )

        return v

    @validator("expires_at")
    def validate_expiration(cls, v, values):
        """Ensure expiration is in the future."""
        if v and "created_at" in values:
            created = values["created_at"]
            if v <= created:
                raise ValueError("Expiration must be after creation time")

        return v

    def is_expired(self) -> bool:
        """Check if the sandbox has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def get_security_hardening_flags(self) -> List[str]:
        """Generate Docker security flags based on security policy."""
        flags = []

        policy = self.security_policy

        # Always run as non-root
        flags.extend(["--user", "1000:1000"])

        if policy.readonly_filesystem:
            flags.append("--read-only")
            # Add writable tmp and workspace volumes
            flags.extend(
                [
                    "--tmpfs",
                    "/tmp:rw,noexec,nosuid,size=100m",
                    "--tmpfs",
                    f"{self.working_directory}:rw,noexec,nosuid,size=512m",
                ]
            )

        if policy.drop_all_capabilities:
            flags.extend(["--cap-drop", "ALL"])

        if policy.no_new_privileges:
            flags.extend(["--security-opt", "no-new-privileges"])

        if policy.use_seccomp_profile:
            flags.extend(["--security-opt", "seccomp=default"])

        if policy.use_apparmor_profile:
            flags.extend(["--security-opt", "apparmor=docker-default"])

        # Network policy
        if policy.network_policy == EnumSandboxNetworkPolicy.NONE:
            flags.extend(["--network", "none"])
        elif policy.network_policy == EnumSandboxNetworkPolicy.LOCALHOST:
            flags.extend(
                ["--network", "host", "--add-host", "host.docker.internal:host-gateway"]
            )

        # Resource limits
        limits = self.resource_limits
        flags.extend(
            [
                "--memory",
                f"{limits.memory_mb}m",
                "--cpus",
                str(limits.cpu_cores),
                "--ulimit",
                f"nofile={limits.max_file_descriptors}:{limits.max_file_descriptors}",
                "--ulimit",
                f"nproc={limits.max_processes}:{limits.max_processes}",
            ]
        )

        return flags

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
