# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests demonstrating handler packaging artifact verification workflow.

These tests serve as executable documentation for the expected verification flow
when downloading and using packaged handlers. They demonstrate how
ProtocolPackageVerifier (to be implemented in omnibase_spi OMN-1232) should
operate on ModelHandlerPackaging metadata.

Key Security Concepts Demonstrated:

1. TOCTOU (Time-of-Check-Time-of-Use) Prevention:
   - WRONG: Check hash -> Download -> Use (vulnerable to replacement between check and use)
   - RIGHT: Download -> Check hash -> Use (secure - hash verified on actual downloaded content)

2. Hash Verification:
   - SHA256 integrity hashes are verified AFTER download completes
   - Hash mismatch indicates artifact tampering or corruption
   - Verification must happen on the actual bytes that will be executed

3. Signature Verification:
   - Optional ED25519 signatures provide authenticity guarantees
   - Signature is verified against downloaded content + public key
   - Enables supply chain security (proves artifact came from trusted source)

4. Sandbox Constraint Enforcement:
   - ModelSandboxRequirements declares handler's resource needs
   - Runtime enforces constraints BEFORE handler execution
   - Violations are detected at verification time, not runtime

Relationship to ModelHandlerPackaging:
    ModelHandlerPackaging is the metadata model that describes:
    - artifact_reference: Where to download the handler artifact
    - integrity_hash: Expected SHA256 hash for verification
    - signature_reference: Optional detached signature location
    - sandbox_compatibility: Resource constraints for safe execution

    This test suite demonstrates how a verifier implementation should use
    this metadata to securely download, verify, and prepare handlers for execution.

Implementation Notes:
    - ProtocolPackageVerifier will be defined in omnibase_spi (OMN-1232)
    - These tests use simulated downloads and verification for illustration
    - Real implementation will use httpx/aiohttp for downloads, cryptography lib for Ed25519
    - All tests are self-contained with mocked external dependencies

Thread Safety:
    Tests may run in parallel via pytest-xdist. Each test is isolated
    with no shared mutable state.
"""

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from omnibase_core.enums.enum_hash_algorithm import EnumHashAlgorithm
from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm
from omnibase_core.models.handlers.model_handler_packaging import ModelHandlerPackaging
from omnibase_core.models.handlers.model_sandbox_requirements import (
    ModelSandboxRequirements,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Test Constants
# =============================================================================

INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60

# Sample handler binary content for testing
SAMPLE_HANDLER_CONTENT = b"#!/usr/bin/env python3\nprint('Hello from handler')\n"
SAMPLE_HANDLER_HASH = hashlib.sha256(SAMPLE_HANDLER_CONTENT).hexdigest()

# Tampered content (simulates MITM attack or corruption)
TAMPERED_HANDLER_CONTENT = b"#!/usr/bin/env python3\nprint('MALICIOUS CODE')\n"
TAMPERED_HANDLER_HASH = hashlib.sha256(TAMPERED_HANDLER_CONTENT).hexdigest()


# =============================================================================
# Simulated Verifier Protocol (to be defined in omnibase_spi OMN-1232)
# =============================================================================


@dataclass
class VerificationResult:
    """Result of artifact verification.

    This is a simplified version of what ProtocolPackageVerifier will return.
    The actual implementation will include more detailed error information.
    """

    success: bool
    artifact_path: str | None = None
    error_message: str | None = None
    hash_verified: bool = False
    signature_verified: bool | None = None  # None if no signature configured


class SimulatedPackageVerifier:
    """Simulated package verifier for demonstration purposes.

    This class demonstrates the expected verification workflow that
    ProtocolPackageVerifier will implement. It shows:
    - How to properly verify artifacts AFTER download (TOCTOU prevention)
    - How to check hash integrity
    - How to verify signatures when present
    - How to enforce sandbox constraints

    WARNING: This is for testing/documentation only. Real implementation
    will be in omnibase_spi with proper async HTTP client and cryptography.
    """

    def __init__(
        self,
        artifact_downloader: Callable[[str], Awaitable[bytes]] | None = None,
        signature_downloader: Callable[[str], Awaitable[bytes]] | None = None,
    ) -> None:
        """Initialize verifier with optional mock downloaders.

        Args:
            artifact_downloader: Callable that simulates artifact download.
                Returns bytes or raises exception.
            signature_downloader: Callable that simulates signature download.
                Returns bytes or raises exception.
        """
        self._artifact_downloader = artifact_downloader
        self._signature_downloader = signature_downloader

    async def download_artifact(self, url: str) -> bytes:
        """Simulate artifact download.

        In real implementation, this would use httpx or aiohttp to
        download from the artifact_reference URL.

        Args:
            url: Artifact URL to download from.

        Returns:
            Downloaded bytes.
        """
        if self._artifact_downloader:
            return await self._artifact_downloader(url)
        # Default: return sample content
        return SAMPLE_HANDLER_CONTENT

    async def download_signature(self, url: str) -> bytes:
        """Simulate signature download.

        Args:
            url: Signature file URL.

        Returns:
            Downloaded signature bytes.
        """
        if self._signature_downloader:
            return await self._signature_downloader(url)
        return b"simulated_ed25519_signature_bytes"

    def compute_hash(self, content: bytes, algorithm: EnumHashAlgorithm) -> str:
        """Compute hash of content using specified algorithm.

        Args:
            content: Bytes to hash.
            algorithm: Hash algorithm to use.

        Returns:
            Hex-encoded hash string.
        """
        if algorithm == EnumHashAlgorithm.SHA256:
            return hashlib.sha256(content).hexdigest()
        # Future: Add SHA384, SHA512 support
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    def verify_signature(
        self,
        content: bytes,
        signature: bytes,
        algorithm: EnumSignatureAlgorithm,
    ) -> bool:
        """Verify signature of content.

        In real implementation, this would use the cryptography library
        to verify ED25519 signatures against a known public key.

        Args:
            content: Content that was signed.
            signature: Signature bytes to verify.
            algorithm: Signature algorithm used.

        Returns:
            True if signature is valid, False otherwise.
        """
        # Simulated: Real implementation uses cryptography.hazmat.primitives
        if algorithm == EnumSignatureAlgorithm.ED25519:
            # For testing, we accept any non-empty signature as valid
            # Real implementation verifies against public key
            return len(signature) > 0
        return False

    async def verify_and_download(
        self, packaging: ModelHandlerPackaging
    ) -> VerificationResult:
        """Verify and download a handler artifact.

        This implements the TOCTOU-safe verification workflow:
        1. Download artifact from artifact_reference
        2. Compute hash of downloaded content
        3. Compare computed hash with expected integrity_hash
        4. If signature configured, download and verify signature
        5. Return verification result with path to verified artifact

        Security Note:
            Hash verification happens AFTER download, not before.
            This prevents TOCTOU attacks where an attacker replaces
            the artifact between verification and download.

        Args:
            packaging: Handler packaging metadata with verification info.

        Returns:
            VerificationResult with success status and artifact path.
        """
        # Step 1: Download artifact
        try:
            content = await self.download_artifact(packaging.artifact_reference)
        except Exception as e:
            return VerificationResult(
                success=False,
                error_message=f"Download failed: {e}",
            )

        # Step 2: Compute hash of DOWNLOADED content (TOCTOU-safe)
        computed_hash = self.compute_hash(content, packaging.hash_algorithm)

        # Step 3: Verify integrity hash
        if computed_hash != packaging.integrity_hash:
            return VerificationResult(
                success=False,
                error_message=(
                    f"Hash mismatch: expected {packaging.integrity_hash[:16]}..., "
                    f"got {computed_hash[:16]}..."
                ),
                hash_verified=False,
            )

        # Step 4: Verify signature if configured
        signature_verified: bool | None = None
        if packaging.signature_reference and packaging.signature_algorithm:
            try:
                signature = await self.download_signature(packaging.signature_reference)
                signature_verified = self.verify_signature(
                    content, signature, packaging.signature_algorithm
                )
                if not signature_verified:
                    return VerificationResult(
                        success=False,
                        error_message="Signature verification failed",
                        hash_verified=True,
                        signature_verified=False,
                    )
            except Exception as e:
                return VerificationResult(
                    success=False,
                    error_message=f"Signature download failed: {e}",
                    hash_verified=True,
                    signature_verified=False,
                )

        # Step 5: Success - artifact is verified
        return VerificationResult(
            success=True,
            artifact_path="/tmp/verified/handler.py",  # Simulated path
            hash_verified=True,
            signature_verified=signature_verified,
        )


def check_sandbox_constraints(
    requirements: ModelSandboxRequirements,
    runtime_config: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check if sandbox constraints can be satisfied.

    This simulates the runtime's sandbox constraint enforcement.
    The runtime checks if the handler's requirements are compatible
    with the current sandbox configuration.

    Args:
        requirements: Handler's declared sandbox requirements.
        runtime_config: Runtime sandbox configuration with available resources.

    Returns:
        Tuple of (is_compatible, error_message).
        error_message is None if compatible.
    """
    max_memory = runtime_config.get("max_memory_mb", 256)
    max_cpu = runtime_config.get("max_cpu_cores", 1.0)
    network_allowed = runtime_config.get("network_allowed", False)
    filesystem_allowed = runtime_config.get("filesystem_allowed", False)

    # Check memory constraint
    if requirements.memory_limit_mb and requirements.memory_limit_mb > max_memory:
        return (
            False,
            f"Memory requirement {requirements.memory_limit_mb}MB exceeds "
            f"sandbox limit {max_memory}MB",
        )

    # Check CPU constraint
    if requirements.cpu_limit_cores and requirements.cpu_limit_cores > max_cpu:
        return (
            False,
            f"CPU requirement {requirements.cpu_limit_cores} cores exceeds "
            f"sandbox limit {max_cpu} cores",
        )

    # Check network constraint
    if requirements.requires_network and not network_allowed:
        return False, "Handler requires network access but sandbox disallows it"

    # Check filesystem constraint
    if requirements.requires_filesystem and not filesystem_allowed:
        return False, "Handler requires filesystem access but sandbox disallows it"

    return True, None


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_packaging() -> ModelHandlerPackaging:
    """Create sample handler packaging metadata.

    Returns:
        ModelHandlerPackaging with valid sample data.
    """
    return ModelHandlerPackaging(
        artifact_reference="https://releases.example.com/handler-v1.0.0.py",
        integrity_hash=SAMPLE_HANDLER_HASH,
        sandbox_compatibility=ModelSandboxRequirements(),
        min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
    )


@pytest.fixture
def signed_packaging() -> ModelHandlerPackaging:
    """Create handler packaging with signature verification.

    Returns:
        ModelHandlerPackaging with signature configuration.
    """
    return ModelHandlerPackaging(
        artifact_reference="oci://ghcr.io/omninode/handlers/validator:v1.0.0",
        integrity_hash=SAMPLE_HANDLER_HASH,
        signature_reference="https://releases.example.com/validator-v1.0.0.sig",
        signature_algorithm=EnumSignatureAlgorithm.ED25519,
        sandbox_compatibility=ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=["api.example.com"],
            memory_limit_mb=512,
        ),
        min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
    )


@pytest.fixture
def restrictive_sandbox_config() -> dict[str, Any]:
    """Create restrictive sandbox configuration.

    Returns:
        Sandbox config that blocks most operations.
    """
    return {
        "max_memory_mb": 256,
        "max_cpu_cores": 1.0,
        "network_allowed": False,
        "filesystem_allowed": False,
    }


@pytest.fixture
def permissive_sandbox_config() -> dict[str, Any]:
    """Create permissive sandbox configuration.

    Returns:
        Sandbox config that allows most operations.
    """
    return {
        "max_memory_mb": 16384,  # 16 GB
        "max_cpu_cores": 8.0,
        "network_allowed": True,
        "filesystem_allowed": True,
    }


# =============================================================================
# Integration Tests: Artifact Download Verification Workflow
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestHandlerPackagingVerificationWorkflow:
    """Integration tests demonstrating artifact verification workflow.

    These tests show the expected verification flow for handler packaging:
    1. Download artifact from artifact_reference
    2. Verify integrity_hash AFTER download (TOCTOU prevention)
    3. Verify signature if signature_reference is set
    4. Enforce sandbox_compatibility constraints

    The workflow ensures that:
    - Artifacts are verified on the actual downloaded bytes
    - Hash verification detects tampering or corruption
    - Signatures provide authenticity guarantees
    - Sandbox constraints are enforced before execution

    Implementation Reference:
        - ProtocolPackageVerifier: omnibase_spi (OMN-1232)
        - ModelHandlerPackaging: omnibase_core/models/handlers/
        - ModelSandboxRequirements: omnibase_core/models/handlers/
    """

    # =========================================================================
    # Hash Verification Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_verify_integrity_hash_after_download(
        self, sample_packaging: ModelHandlerPackaging
    ) -> None:
        """Verify that hash verification happens AFTER download, not before.

        This demonstrates TOCTOU (time-of-check-time-of-use) prevention:
        - WRONG: Check hash -> Download -> Use (vulnerable to replacement)
        - RIGHT: Download -> Check hash -> Use (secure)

        The key insight is that hash verification must happen on the ACTUAL
        bytes that will be executed, not on bytes fetched in a separate request.

        Security Rationale:
            If we verified the hash before download (in a separate request),
            an attacker with network access could:
            1. Serve correct content for the verification request
            2. Serve malicious content for the actual download
            This is the classic TOCTOU attack vector.

        By computing the hash on the downloaded bytes, we ensure verification
        happens on the exact content that will be executed.
        """

        # Create verifier with mock downloader returning known content
        async def mock_download(url: str) -> bytes:
            return SAMPLE_HANDLER_CONTENT

        verifier = SimulatedPackageVerifier(artifact_downloader=mock_download)

        # Verify workflow: download first, then verify hash
        result = await verifier.verify_and_download(sample_packaging)

        # Hash verification should succeed on matching content
        assert result.success is True
        assert result.hash_verified is True
        assert result.error_message is None

        # Verify the hash was computed correctly
        computed = hashlib.sha256(SAMPLE_HANDLER_CONTENT).hexdigest()
        assert computed == sample_packaging.integrity_hash

    @pytest.mark.asyncio
    async def test_reject_tampered_artifact(
        self, sample_packaging: ModelHandlerPackaging
    ) -> None:
        """Verify that tampered artifacts are rejected.

        This test simulates a scenario where the artifact has been modified
        after the packaging metadata was created (e.g., supply chain attack,
        compromised mirror, or bit rot).

        The hash mismatch detection is the primary defense against artifact
        tampering. When the computed hash differs from the expected hash,
        the verifier must reject the artifact.

        Attack Scenarios Detected:
            - MITM attack replacing artifact in transit
            - Compromised artifact repository
            - Accidental corruption during storage
            - Supply chain attack modifying artifact after signing
        """

        # Create verifier that returns tampered content
        async def mock_download_tampered(url: str) -> bytes:
            return TAMPERED_HANDLER_CONTENT  # Different from expected

        verifier = SimulatedPackageVerifier(artifact_downloader=mock_download_tampered)

        result = await verifier.verify_and_download(sample_packaging)

        # Verification should fail due to hash mismatch
        assert result.success is False
        assert result.hash_verified is False
        assert result.error_message is not None
        assert "Hash mismatch" in result.error_message

        # Verify hashes are indeed different
        assert SAMPLE_HANDLER_HASH != TAMPERED_HANDLER_HASH

    @pytest.mark.asyncio
    async def test_hash_algorithm_enforcement(self) -> None:
        """Verify that only supported hash algorithms are accepted.

        ModelHandlerPackaging enforces SHA256 as the only supported algorithm
        in v1. This test demonstrates that the model validation prevents
        use of unsupported algorithms.

        Why SHA256?
            - Well-established, widely supported
            - 256-bit output provides sufficient collision resistance
            - Standardized in FIPS 180-4
            - Balance of security and performance

        Future versions may add SHA384/SHA512 for higher security requirements.
        """
        # SHA256 is accepted (default)
        packaging = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            hash_algorithm=EnumHashAlgorithm.SHA256,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.hash_algorithm == EnumHashAlgorithm.SHA256

        # Model validation ensures hash format is correct
        assert len(packaging.integrity_hash) == 64
        assert EnumHashAlgorithm.SHA256.validate_hash(packaging.integrity_hash)

    # =========================================================================
    # Signature Verification Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_verify_signature_when_present(
        self, signed_packaging: ModelHandlerPackaging
    ) -> None:
        """Verify that signatures are checked when configured.

        When signature_reference and signature_algorithm are set,
        the verifier must:
        1. Download the signature file
        2. Verify the signature against the artifact content
        3. Fail verification if signature is invalid

        Signature verification provides authenticity guarantees:
        - Proves artifact came from trusted source (key holder)
        - Detects tampering even if attacker can modify hash
        - Enables trust chains via certificate hierarchies

        ED25519 is used because:
        - Modern, fast, and secure (EdDSA)
        - Compact 64-byte signatures
        - No known practical attacks
        - Deterministic signing (no random values needed)
        """

        # Create verifier with valid signature
        async def mock_download(url: str) -> bytes:
            return SAMPLE_HANDLER_CONTENT

        async def mock_signature_download(url: str) -> bytes:
            return b"valid_ed25519_signature_64_bytes_padding_to_meet_length"

        verifier = SimulatedPackageVerifier(
            artifact_downloader=mock_download,
            signature_downloader=mock_signature_download,
        )

        result = await verifier.verify_and_download(signed_packaging)

        # Both hash and signature should be verified
        assert result.success is True
        assert result.hash_verified is True
        assert result.signature_verified is True

    @pytest.mark.asyncio
    async def test_skip_signature_when_not_configured(
        self, sample_packaging: ModelHandlerPackaging
    ) -> None:
        """Verify that signature check is skipped when not configured.

        Not all handlers require cryptographic signatures. When
        signature_reference is not set, the verifier should:
        - Skip signature verification entirely
        - Still verify hash integrity
        - Succeed if hash matches

        Use Cases for Unsigned Handlers:
        - Development/testing handlers
        - Internal handlers from trusted sources
        - Handlers where hash alone provides sufficient verification
        """
        # sample_packaging has no signature configured
        assert sample_packaging.signature_reference is None
        assert sample_packaging.signature_algorithm is None

        async def mock_download(url: str) -> bytes:
            return SAMPLE_HANDLER_CONTENT

        verifier = SimulatedPackageVerifier(artifact_downloader=mock_download)
        result = await verifier.verify_and_download(sample_packaging)

        # Hash verified, signature not checked (None)
        assert result.success is True
        assert result.hash_verified is True
        assert result.signature_verified is None  # Not checked

    @pytest.mark.asyncio
    async def test_reject_invalid_signature(
        self, signed_packaging: ModelHandlerPackaging
    ) -> None:
        """Verify that invalid signatures cause verification failure.

        When signature verification fails (invalid signature, wrong key,
        corrupted signature file), the verifier must reject the artifact
        even if the hash matches.

        This prevents attacks where an attacker:
        - Modifies both artifact and hash
        - Cannot forge a valid signature without private key
        """

        async def mock_download(url: str) -> bytes:
            return SAMPLE_HANDLER_CONTENT

        async def mock_signature_download(url: str) -> bytes:
            return b""  # Empty/invalid signature

        verifier = SimulatedPackageVerifier(
            artifact_downloader=mock_download,
            signature_downloader=mock_signature_download,
        )

        # Override verify_signature to simulate failure
        original_verify = verifier.verify_signature

        def mock_verify_failure(
            content: bytes,
            signature: bytes,
            algorithm: EnumSignatureAlgorithm,
        ) -> bool:
            return False  # Simulate verification failure

        verifier.verify_signature = mock_verify_failure  # type: ignore[method-assign]

        result = await verifier.verify_and_download(signed_packaging)

        # Hash passes, signature fails
        assert result.success is False
        assert result.hash_verified is True
        assert result.signature_verified is False
        assert "Signature verification failed" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_signature_download_failure(
        self, signed_packaging: ModelHandlerPackaging
    ) -> None:
        """Verify graceful handling of signature download failure.

        If the signature file cannot be downloaded (network error,
        404, etc.), verification must fail. We cannot proceed without
        verifying the required signature.
        """

        async def mock_download(url: str) -> bytes:
            return SAMPLE_HANDLER_CONTENT

        async def mock_signature_download_fail(url: str) -> bytes:
            raise ConnectionError("Signature server unavailable")

        verifier = SimulatedPackageVerifier(
            artifact_downloader=mock_download,
            signature_downloader=mock_signature_download_fail,
        )

        result = await verifier.verify_and_download(signed_packaging)

        assert result.success is False
        assert result.hash_verified is True  # Hash was verified before signature
        assert "Signature download failed" in (result.error_message or "")

    # =========================================================================
    # Sandbox Constraint Enforcement Tests
    # =========================================================================

    def test_enforce_sandbox_network_constraint(
        self,
        restrictive_sandbox_config: dict[str, Any],
    ) -> None:
        """Verify that network requirements are enforced.

        When a handler declares requires_network=True but the sandbox
        configuration disallows network access, the handler cannot
        be executed in that sandbox.

        This is checked BEFORE execution to provide early feedback
        rather than runtime failures.
        """
        requirements = ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=["api.example.com"],
        )

        compatible, error = check_sandbox_constraints(
            requirements, restrictive_sandbox_config
        )

        assert compatible is False
        assert error is not None
        assert "network access" in error.lower()

    def test_enforce_sandbox_filesystem_constraint(
        self,
        restrictive_sandbox_config: dict[str, Any],
    ) -> None:
        """Verify that filesystem requirements are enforced.

        Handlers that need filesystem access beyond their working
        directory must declare requires_filesystem=True. If the
        sandbox doesn't allow it, execution is prevented.
        """
        requirements = ModelSandboxRequirements(
            requires_filesystem=True,
        )

        compatible, error = check_sandbox_constraints(
            requirements, restrictive_sandbox_config
        )

        assert compatible is False
        assert error is not None
        assert "filesystem access" in error.lower()

    def test_enforce_sandbox_memory_limit(
        self,
        restrictive_sandbox_config: dict[str, Any],
    ) -> None:
        """Verify that memory limits are enforced.

        If a handler requires more memory than the sandbox allows,
        it cannot be executed. This prevents OOM situations and
        ensures fair resource allocation.
        """
        requirements = ModelSandboxRequirements(
            memory_limit_mb=1024,  # Requires 1GB
        )

        compatible, error = check_sandbox_constraints(
            requirements,
            restrictive_sandbox_config,  # Allows 256MB
        )

        assert compatible is False
        assert error is not None
        assert "Memory requirement" in error
        assert "256" in error

    def test_enforce_sandbox_cpu_limit(
        self,
        restrictive_sandbox_config: dict[str, Any],
    ) -> None:
        """Verify that CPU limits are enforced.

        Handlers declaring CPU requirements beyond sandbox limits
        cannot be executed. This ensures compute-intensive handlers
        don't starve other workloads.
        """
        requirements = ModelSandboxRequirements(
            cpu_limit_cores=4.0,  # Requires 4 cores
        )

        compatible, error = check_sandbox_constraints(
            requirements,
            restrictive_sandbox_config,  # Allows 1 core
        )

        assert compatible is False
        assert error is not None
        assert "CPU requirement" in error

    def test_sandbox_constraints_satisfied(
        self,
        permissive_sandbox_config: dict[str, Any],
    ) -> None:
        """Verify that compatible handlers pass constraint checking.

        When handler requirements fit within sandbox limits, the
        constraint check should pass, allowing execution to proceed.
        """
        requirements = ModelSandboxRequirements(
            requires_network=True,
            requires_filesystem=True,
            allowed_domains=["*.example.com"],
            memory_limit_mb=4096,
            cpu_limit_cores=2.0,
        )

        compatible, error = check_sandbox_constraints(
            requirements, permissive_sandbox_config
        )

        assert compatible is True
        assert error is None

    def test_minimal_sandbox_requirements_always_pass(
        self,
        restrictive_sandbox_config: dict[str, Any],
    ) -> None:
        """Verify that minimal requirements pass any sandbox.

        The default ModelSandboxRequirements (no network, no filesystem,
        no explicit resource limits) should pass even the most
        restrictive sandbox configuration.
        """
        requirements = ModelSandboxRequirements()  # All defaults

        compatible, error = check_sandbox_constraints(
            requirements, restrictive_sandbox_config
        )

        assert compatible is True
        assert error is None

    # =========================================================================
    # TOCTOU Prevention Pattern Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_toctou_prevention_pattern(self) -> None:
        """Demonstrate the TOCTOU-safe verification pattern.

        This test explicitly shows why hash verification must happen
        AFTER download completes, not in a separate request.

        TOCTOU Attack Vector (if done wrong):
            1. Verifier requests hash of artifact (GET /hash)
            2. Server returns correct hash
            3. Verifier requests artifact (GET /artifact)
            4. Attacker intercepts and serves malicious artifact
            5. Verifier uses malicious artifact (hash was verified earlier!)

        Secure Pattern (demonstrated here):
            1. Verifier downloads artifact (GET /artifact)
            2. Verifier computes hash of downloaded bytes
            3. Verifier compares computed hash with expected hash
            4. Hash mismatch = reject (attack detected)

        The key difference is that we verify the hash of the EXACT bytes
        that will be used, not bytes from a separate request.
        """
        # Simulate an attacker who serves different content to different requests
        request_count = 0

        async def attacker_controlled_server(url: str) -> bytes:
            nonlocal request_count
            request_count += 1

            if request_count == 1:
                # First request (verification): serve correct content
                return SAMPLE_HANDLER_CONTENT
            else:
                # Subsequent requests (actual download): serve malicious content
                return TAMPERED_HANDLER_CONTENT

        # Create packaging with correct hash
        packaging = ModelHandlerPackaging(
            artifact_reference="https://malicious-server.example/handler.py",
            integrity_hash=SAMPLE_HANDLER_HASH,  # Hash of correct content
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )

        # WRONG approach (vulnerable to TOCTOU):
        # Don't do this! This is just to demonstrate the vulnerability.
        # content_for_hash = await attacker_controlled_server(packaging.artifact_reference)
        # hash_check = hashlib.sha256(content_for_hash).hexdigest()
        # assert hash_check == packaging.integrity_hash  # Would pass!
        # content_for_use = await attacker_controlled_server(packaging.artifact_reference)
        # # Now content_for_use is TAMPERED but we already "verified" the hash!

        # CORRECT approach (TOCTOU-safe):
        # Our verifier downloads once and verifies that download
        verifier = SimulatedPackageVerifier(
            artifact_downloader=attacker_controlled_server
        )

        # Reset counter for actual test
        request_count = 0

        # First verification attempt gets correct content
        result1 = await verifier.verify_and_download(packaging)
        assert result1.success is True  # First request succeeds

        # Second verification attempt gets tampered content
        result2 = await verifier.verify_and_download(packaging)
        assert result2.success is False  # Attack detected!
        assert "Hash mismatch" in (result2.error_message or "")

    @pytest.mark.asyncio
    async def test_download_failure_handling(self) -> None:
        """Verify graceful handling of download failures.

        Network errors, timeouts, and server errors should be
        handled gracefully with clear error messages.
        """

        async def failing_download(url: str) -> bytes:
            raise TimeoutError("Connection timed out")

        packaging = ModelHandlerPackaging(
            artifact_reference="https://slow-server.example/handler.py",
            integrity_hash="a" * 64,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )

        verifier = SimulatedPackageVerifier(artifact_downloader=failing_download)
        result = await verifier.verify_and_download(packaging)

        assert result.success is False
        assert result.hash_verified is False
        assert "Download failed" in (result.error_message or "")

    # =========================================================================
    # Model Validation Tests
    # =========================================================================

    def test_artifact_reference_scheme_validation(self) -> None:
        """Verify that artifact references require explicit URI schemes.

        ModelHandlerPackaging requires artifact_reference to use one of:
        - https:// - HTTPS URLs
        - file:/// - Local file URLs (absolute path)
        - oci:// - OCI container registry references
        - registry:// - Internal registry references

        Raw local paths are not allowed for portability.
        """
        # Valid schemes
        for scheme in ["https://", "file:///", "oci://", "registry://"]:
            packaging = ModelHandlerPackaging(
                artifact_reference=f"{scheme}example.com/handler.py",
                integrity_hash="a" * 64,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
            assert packaging.artifact_reference.startswith(scheme)

        # Invalid: raw local path
        with pytest.raises(Exception):  # ModelOnexError
            ModelHandlerPackaging(
                artifact_reference="/path/to/local/handler.py",  # No scheme!
                integrity_hash="a" * 64,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )

    def test_signature_algorithm_consistency(self) -> None:
        """Verify that signature_reference and signature_algorithm are consistent.

        If signature_reference is set, signature_algorithm must also be set.
        If signature_algorithm is set, signature_reference must also be set.
        """
        # Valid: both set
        packaging = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            signature_reference="https://example.com/handler.sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.signature_reference is not None
        assert packaging.signature_algorithm is not None

        # Valid: neither set
        packaging_unsigned = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging_unsigned.signature_reference is None
        assert packaging_unsigned.signature_algorithm is None

        # Invalid: reference without algorithm
        with pytest.raises(Exception):
            ModelHandlerPackaging(
                artifact_reference="https://example.com/handler.py",
                integrity_hash="a" * 64,
                signature_reference="https://example.com/handler.sig",
                # Missing signature_algorithm!
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )

        # Invalid: algorithm without reference
        with pytest.raises(Exception):
            ModelHandlerPackaging(
                artifact_reference="https://example.com/handler.py",
                integrity_hash="a" * 64,
                signature_algorithm=EnumSignatureAlgorithm.ED25519,
                # Missing signature_reference!
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )

    def test_domain_validation_in_sandbox(self) -> None:
        """Verify that allowed_domains are validated.

        ModelSandboxRequirements validates domain format:
        - Valid hostnames (alphanumeric + hyphen)
        - Wildcards only at leftmost label (*.example.com)
        - No IP literals, schemes, or paths
        """
        # Valid domains
        valid_requirements = ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=[
                "api.example.com",
                "*.storage.example.com",
                "sub-domain.example.org",
            ],
        )
        assert len(valid_requirements.allowed_domains) == 3

        # Invalid: wildcard not at leftmost position
        with pytest.raises(Exception):
            ModelSandboxRequirements(
                requires_network=True,
                allowed_domains=["api.*.example.com"],  # Invalid!
            )

        # Invalid: contains scheme
        with pytest.raises(Exception):
            ModelSandboxRequirements(
                requires_network=True,
                allowed_domains=["https://example.com"],  # Has scheme!
            )


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestHandlerPackagingEdgeCases:
    """Edge case tests for handler packaging verification.

    These tests cover unusual but valid scenarios and error conditions
    that the verification system should handle correctly.
    """

    def test_runtime_version_constraints(self) -> None:
        """Verify runtime version constraints are validated.

        min_runtime_version must be <= max_runtime_version when both are set.
        """
        # Valid: min < max
        packaging = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            max_runtime_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert packaging.min_runtime_version < packaging.max_runtime_version

        # Valid: min == max (single version support)
        packaging_exact = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            max_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert (
            packaging_exact.min_runtime_version == packaging_exact.max_runtime_version
        )

        # Invalid: min > max
        with pytest.raises(Exception):
            ModelHandlerPackaging(
                artifact_reference="https://example.com/handler.py",
                integrity_hash="a" * 64,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=2, minor=0, patch=0),
                max_runtime_version=ModelSemVer(major=1, minor=0, patch=0),
            )

    def test_hash_format_validation(self) -> None:
        """Verify hash format is strictly validated.

        integrity_hash must be:
        - Exactly 64 characters (SHA256 output length)
        - Lowercase hexadecimal only
        """
        # Valid hash
        valid_hash = "a" * 64
        packaging = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash=valid_hash,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert len(packaging.integrity_hash) == 64

        # Invalid: wrong length
        with pytest.raises(Exception):
            ModelHandlerPackaging(
                artifact_reference="https://example.com/handler.py",
                integrity_hash="a" * 63,  # Too short
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )

        # Invalid: uppercase
        with pytest.raises(Exception):
            ModelHandlerPackaging(
                artifact_reference="https://example.com/handler.py",
                integrity_hash="A" * 64,  # Uppercase not allowed
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )

        # Invalid: non-hex characters
        with pytest.raises(Exception):
            ModelHandlerPackaging(
                artifact_reference="https://example.com/handler.py",
                integrity_hash="g" * 64,  # 'g' is not hex
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )

    def test_empty_allowed_domains_with_network(self) -> None:
        """Verify empty allowed_domains with network access.

        Empty allowed_domains with requires_network=True means
        no domain restrictions (all domains allowed).
        """
        requirements = ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=[],  # Empty = no restrictions
        )
        assert requirements.requires_network is True
        assert requirements.allowed_domains == []

    def test_resource_limits_boundaries(self) -> None:
        """Verify resource limit boundaries are enforced.

        memory_limit_mb: 64 - 262144 (64 MB to 256 GB)
        cpu_limit_cores: 0.1 - 256
        """
        # Minimum values
        min_requirements = ModelSandboxRequirements(
            memory_limit_mb=64,
            cpu_limit_cores=0.1,
        )
        assert min_requirements.memory_limit_mb == 64
        assert min_requirements.cpu_limit_cores == 0.1

        # Maximum values
        max_requirements = ModelSandboxRequirements(
            memory_limit_mb=262144,  # 256 GB
            cpu_limit_cores=256.0,
        )
        assert max_requirements.memory_limit_mb == 262144
        assert max_requirements.cpu_limit_cores == 256.0

        # Below minimum memory
        with pytest.raises(Exception):
            ModelSandboxRequirements(memory_limit_mb=32)  # Below 64

        # Above maximum CPU
        with pytest.raises(Exception):
            ModelSandboxRequirements(cpu_limit_cores=300.0)  # Above 256

    def test_model_immutability(self) -> None:
        """Verify that packaging models are immutable.

        Both ModelHandlerPackaging and ModelSandboxRequirements are
        frozen (immutable) after creation. This ensures thread safety
        and prevents accidental modification.
        """
        packaging = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # ValidationError from Pydantic frozen=True
            packaging.integrity_hash = "b" * 64

        requirements = ModelSandboxRequirements(memory_limit_mb=512)
        with pytest.raises(Exception):
            requirements.memory_limit_mb = 1024

    def test_model_repr_for_debugging(self) -> None:
        """Verify model repr is useful for debugging.

        Both models provide concise __repr__ for debugging
        without exposing sensitive information.
        """
        packaging = ModelHandlerPackaging(
            artifact_reference="https://example.com/handler.py",
            integrity_hash="a" * 64,
            signature_reference="https://example.com/handler.sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=ModelSandboxRequirements(
                requires_network=True,
                memory_limit_mb=512,
            ),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )

        repr_str = repr(packaging)
        assert "ModelHandlerPackaging" in repr_str
        assert "signed=True" in repr_str
        assert "scheme=https" in repr_str

        requirements_repr = repr(packaging.sandbox_compatibility)
        assert "ModelSandboxRequirements" in requirements_repr
        assert "network=True" in requirements_repr
        assert "mem=512MB" in requirements_repr
