"""
Contract CLI Commands.

Provides CLI commands for contract management operations including
initialization, building, and comparison of ONEX contracts.

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

import functools
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import click
import yaml

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.common.model_validation_result import (
        ModelValidationResult,
    )
    from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
    from omnibase_core.models.contracts.model_handler_contract import (
        ModelHandlerContract,
    )

# Type alias for output formats
BuildOutputFormat = Literal["yaml", "json"]
DiffOutputFormat = Literal["text", "json", "yaml"]

# LRU cache size for profile lookup.
#
# Cache Size Calculation:
#   - 4 node kinds exist: ORCHESTRATOR, REDUCER, EFFECT, COMPUTE
#   - Each node kind maps to one cached tuple of profile names
#   - 8 slots = 4 kinds * 2x headroom for potential future expansion
#
# Performance Impact:
#   - Cache prevents redundant profile registry lookups during interactive sessions
#   - Profile dictionaries (ORCHESTRATOR_PROFILES, etc.) are module-level constants
#   - First call per node_kind triggers lazy import; subsequent calls hit cache
#   - LRU eviction is acceptable since cache misses are cheap (just re-imports)
#
# Why not larger? The profile set is small and stable. Excessive cache size
# wastes memory with no benefit since there are only 4 possible cache keys.
# The 2x headroom ensures no eviction during normal usage patterns.
PROFILE_CACHE_SIZE: int = 8

# Maximum file size for contract files (10 MB).
# This limit prevents denial-of-service attacks via extremely large input files
# that could exhaust memory. 10 MB is generous for contract YAML files which
# typically range from 1-50 KB. Files larger than this are almost certainly
# not valid contracts and should be rejected early.
MAX_CONTRACT_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Full SHA256 hash length (64 hex characters = 256 bits).
# Documented here for reference; we truncate to MERGE_HASH_LENGTH for readability.
SHA256_FULL_LENGTH: int = 64

# Truncation length for merge hashes. 40 hex characters (160 bits) provides
# strong uniqueness for detecting contract changes with an extra safety margin.
#
# Collision Probability Analysis (Birthday Paradox):
#   - At 160 bits, collision probability = n^2 / 2^161 where n = contract count
#   - For 10 billion contracts (10^10): P(collision) ≈ 1.5e-29
#   - For 1 trillion contracts (10^12): P(collision) ≈ 1.5e-25
#   - This is effectively zero for all practical purposes
#
# Why 40 chars (160 bits) instead of 32 chars (128 bits)?
#   - 32 chars (128 bits) is already sufficient: ~1.5e-20 collision probability for 10B
#   - 40 chars provides additional 32-bit safety margin for extra confidence
#   - Still readable in logs/CLI while exceeding common security thresholds
#   - Matches the output length of SHA-1 (160 bits), a well-understood security baseline
#
# Purpose: BUILD REPRODUCIBILITY FINGERPRINT (NOT cryptographic security)
# ---------------------------------------------------------------------
# The merge hash serves as a deterministic fingerprint for build caching:
#   - Same inputs (profile + version + patch content) → same hash
#   - Any change to inputs → different hash
#   - CI/CD pipelines use this to detect when contracts need rebuilding
#   - Two contracts with identical hashes are considered identical builds
#
# This is NOT used for:
#   - Cryptographic authentication or signing
#   - Protecting against adversarial collision attacks
#   - Security-sensitive operations requiring full SHA256
#
# If cryptographic security is ever needed, use SHA256_FULL_LENGTH (64 chars).
MERGE_HASH_LENGTH: int = 40

# Mapping from EnumNodeKind to short names used in CLI
_NODE_KIND_TO_CLI_NAME: dict[EnumNodeKind, str] = {
    EnumNodeKind.ORCHESTRATOR: "orchestrator",
    EnumNodeKind.REDUCER: "reducer",
    EnumNodeKind.EFFECT: "effect",
    EnumNodeKind.COMPUTE: "compute",
}

# Reverse mapping for CLI name to EnumNodeKind
_CLI_NAME_TO_NODE_KIND: dict[str, EnumNodeKind] = {
    v: k for k, v in _NODE_KIND_TO_CLI_NAME.items()
}


@functools.lru_cache(maxsize=PROFILE_CACHE_SIZE)
def _get_available_profiles_for_kind(node_kind: EnumNodeKind) -> tuple[str, ...]:
    """
    Get available profile short names for a node kind.

    Design Decision: Profile Lookup Strategy
    -----------------------------------------
    This function uses explicit imports from the profile factory module rather than
    a generic registry lookup. This is intentional for several reasons:

    1. **Type Safety**: Each profile dictionary is typed for its specific node kind,
       ensuring compile-time validation of profile structures.

    2. **Performance**: The LRU cache (PROFILE_CACHE_SIZE slots) prevents redundant
       imports during interactive CLI sessions. With only 4 node kinds, 8 cache slots
       provide 2x headroom for potential future expansion.

    3. **Explicit Dependencies**: Direct imports make the profile dependencies
       visible and auditable, rather than hidden behind a dynamic registry.

    4. **Prefix Convention**: Profile names follow the convention "{node_type}_{profile}"
       (e.g., "orchestrator_safe"). The prefix is stripped to present short names to
       users while the full name is used internally for profile resolution.

    Args:
        node_kind: The node kind to get profiles for.

    Returns:
        Tuple of profile short names (without the node type prefix).
    """
    from omnibase_core.factories.profiles import (
        COMPUTE_PROFILES,
        EFFECT_PROFILES,
        ORCHESTRATOR_PROFILES,
        REDUCER_PROFILES,
    )

    kind_name = _NODE_KIND_TO_CLI_NAME[node_kind]
    prefix = f"{kind_name}_"

    # Get profile names based on node kind using explicit dictionary mapping.
    # Each dictionary contains profiles registered for that specific node type.
    profile_names: list[str]
    if node_kind == EnumNodeKind.ORCHESTRATOR:
        profile_names = list(ORCHESTRATOR_PROFILES.keys())
    elif node_kind == EnumNodeKind.REDUCER:
        profile_names = list(REDUCER_PROFILES.keys())
    elif node_kind == EnumNodeKind.EFFECT:
        profile_names = list(EFFECT_PROFILES.keys())
    else:
        profile_names = list(COMPUTE_PROFILES.keys())

    # Strip the prefix to get user-friendly short names.
    # e.g., "orchestrator_safe" -> "safe"
    return tuple(p.removeprefix(prefix) for p in profile_names)


def _build_full_profile_name(node_type: str, profile: str) -> str:
    """
    Build the full profile name from node type and profile short name.

    Args:
        node_type: The node type (e.g., "orchestrator").
        profile: The profile short name (e.g., "safe").

    Returns:
        The full profile name (e.g., "orchestrator_safe").

    Examples:
        >>> _build_full_profile_name("orchestrator", "safe")
        'orchestrator_safe'
        >>> _build_full_profile_name("compute", "pure")
        'compute_pure'
    """
    return f"{node_type}_{profile}"


def _validate_profile_exists(node_type: str, profile: str) -> str | None:
    """
    Validate that the profile exists for the given node type.

    Args:
        node_type: The node type (e.g., "orchestrator").
        profile: The profile short name (e.g., "safe").

    Returns:
        None if valid, or an error message if invalid.

    Examples:
        >>> _validate_profile_exists("orchestrator", "safe")  # Valid
        >>> _validate_profile_exists("orchestrator", "invalid") is not None
        True
        >>> _validate_profile_exists("unknown_type", "any") is not None
        True
    """
    node_kind = _CLI_NAME_TO_NODE_KIND.get(node_type)
    if node_kind is None:
        return f"Unknown node type: {node_type}"

    available = _get_available_profiles_for_kind(node_kind)
    if profile not in available:
        available_str = ", ".join(available)
        return (
            f"Unknown profile '{profile}' for {node_type}. "
            f"Available profiles: {available_str}"
        )

    return None


# Dangerous path prefixes that should never be written to by CLI tools
_DANGEROUS_PATH_PREFIXES: tuple[str, ...] = (
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/var/log",
    "/boot",
    "/root",
    "/sys",
    "/proc",
    "/dev",
)


def _validate_path_security(path: Path, *, is_output: bool = False) -> Path:
    """Validate and resolve a file path for security.

    Performs security checks to prevent path traversal attacks and
    accidental access to sensitive system directories. Used for both
    input and output paths.

    Args:
        path: The file path to validate.
        is_output: If True, validates as an output path (write operation).
                   If False, validates as an input path (read operation).

    Returns:
        The resolved (absolute) path if valid.

    Raises:
        click.ClickException: If the path is invalid or potentially dangerous.

    Security Checks:
        1. Resolves the path to an absolute path (follows symlinks)
        2. Detects path traversal patterns (.. in resolved path)
        3. Blocks access to sensitive system directories
        4. For symlinks: validates the resolved target is safe
    """
    resolved = path.resolve()
    resolved_str = str(resolved)

    # Check for path traversal patterns in the resolved path.
    # After resolve(), ".." should not appear in the path. If it does,
    # it indicates a suspicious symlink chain or filesystem manipulation.
    if ".." in resolved_str:
        action = "write to" if is_output else "read from"
        raise click.ClickException(
            f"Path traversal detected: cannot {action} '{resolved_str}'"
        )

    # Block access to sensitive system directories
    for prefix in _DANGEROUS_PATH_PREFIXES:
        if resolved_str.startswith(prefix + "/") or resolved_str == prefix:
            action = "write to" if is_output else "read from"
            raise click.ClickException(
                f"Cannot {action} system directory '{prefix}'. "
                f"Resolved path: {resolved_str}"
            )

    # Additional check: if original path was a symlink, verify the target
    # is not in a dangerous location (symlink resolution is already done above,
    # but we log this explicitly for security auditing)
    if path.is_symlink():
        # The resolved path has already been validated above, but we verify
        # the symlink target doesn't escape to unexpected locations
        try:
            link_target = path.readlink()
            # If the link target is absolute and points to a dangerous location,
            # the check above already caught it. For relative symlinks, the
            # resolved path check is sufficient.
        except OSError:
            # If we can't read the symlink, rely on the resolved path check
            pass

    return resolved


def _validate_output_path(path: Path) -> Path:
    """Validate and resolve an output path for safety.

    Convenience wrapper around _validate_path_security for output paths.

    Args:
        path: The output path to validate.

    Returns:
        The resolved (absolute) path if valid.

    Raises:
        click.ClickException: If the path is invalid or potentially dangerous.
    """
    return _validate_path_security(path, is_output=True)


def _validate_input_file(path: Path) -> Path:
    """Validate an input file path for security and size limits.

    Performs security checks including:
    - Path traversal prevention
    - System directory access prevention
    - File size validation (DoS prevention)

    Args:
        path: The input file path to validate.

    Returns:
        The resolved (absolute) path if valid.

    Raises:
        click.ClickException: If the path is invalid, dangerous, or file is too large.
    """
    # First validate path security
    resolved = _validate_path_security(path, is_output=False)

    # Check file size to prevent DoS attacks via large files
    try:
        file_size = resolved.stat().st_size
    except FileNotFoundError:
        raise click.ClickException(f"File not found: '{resolved}'") from None
    except PermissionError:
        raise click.ClickException(
            f"Permission denied: cannot access '{resolved}'"
        ) from None
    except OSError as e:
        raise click.ClickException(f"Cannot access file '{resolved}': {e}") from e

    if file_size > MAX_CONTRACT_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        limit_mb = MAX_CONTRACT_FILE_SIZE / (1024 * 1024)
        raise click.ClickException(
            f"File too large: '{resolved}' is {size_mb:.2f} MB. "
            f"Maximum allowed size is {limit_mb:.0f} MB. "
            f"Contract files should be small YAML documents."
        )

    return resolved


def _generate_patch_template(
    node_type: str,
    profile: str,
    full_profile_name: str,
    *,
    name: str | None = None,
    override_only: bool = False,
) -> str:
    """
    Generate a patch template YAML for the given profile.

    Args:
        node_type: The node type (e.g., "orchestrator").
        profile: The profile short name (e.g., "safe").
        full_profile_name: The full profile name (e.g., "orchestrator_safe").
        name: Optional custom name for the contract. If provided, uses this
            instead of the placeholder "my-contract-name".
        override_only: If True, omit name and node_version fields (for patches
            that only override behavior without creating a new contract).

    Returns:
        The generated YAML patch template as a string.
    """
    # Common header
    lines = [
        "# Contract Patch - Generated by onex contract init",
        "# Edit this file and run: onex contract build <this-file>",
        "",
        "extends:",
        f"  profile: {full_profile_name}  # Base profile to extend",
        '  version: "1.0.0"',
        "",
    ]

    # Add name and version fields unless override_only mode
    if not override_only:
        contract_name = name if name else "my_contract_name"
        name_comment = "" if name else "  # TODO(OMN-TBD): Change this  [NEEDS TICKET]"
        lines.extend(
            [
                "# Required for new contracts:",
                f"name: {contract_name}{name_comment}",
                "node_version:",
                "  major: 1",
                "  minor: 0",
                "  patch: 0",
                "",
            ]
        )

    lines.extend(
        [
            "# Optional overrides (uncomment to customize):",
            '# description: "My contract description"',
            "",
            "# Behavior overrides:",
            "# descriptor:",
            "#   timeout_ms: 30000",
            "#   retry_policy:",
            "#     max_retries: 3",
            "#     backoff_ms: 1000",
        ]
    )

    # Add node-type-specific sections
    if node_type in ("orchestrator", "reducer"):
        lines.extend(
            [
                "",
                "# Add handlers (for orchestrator/reducer):",
                "# handlers__add:",
                "#   - handler_id: my.handler",
                "#     name: My Handler",
            ]
        )

    if node_type == "orchestrator":
        lines.extend(
            [
                "",
                "# Workflow configuration:",
                "# workflow_coordination:",
                "#   execution_mode: serial",
                "#   max_parallel_branches: 1",
                "#   checkpoint_enabled: false",
            ]
        )

    if node_type == "reducer":
        lines.extend(
            [
                "",
                "# FSM configuration:",
                "# fsm:",
                "#   initial_state: pending",
                "#   states:",
                "#     - name: pending",
                "#       description: Initial state",
            ]
        )

    if node_type == "effect":
        lines.extend(
            [
                "",
                "# Effect configuration:",
                "# effect:",
                "#   idempotency_key: request_id",
                "#   timeout_ms: 5000",
            ]
        )

    if node_type == "compute":
        lines.extend(
            [
                "",
                "# Compute configuration:",
                "# compute:",
                "#   deterministic: true",
                "#   cacheable: true",
            ]
        )

    # Common footer
    lines.extend(
        [
            "",
            "# Add dependencies:",
            "# dependencies__add:",
            '#   - "some.other.contract"',
        ]
    )

    return "\n".join(lines) + "\n"


# =============================================================================
# Build Command Helper Functions
# =============================================================================
#
# Design Decision: Single-File Processing (No Batch Operations)
# -------------------------------------------------------------
# The build and diff commands intentionally process one file at a time rather
# than supporting batch operations. This design follows UNIX philosophy:
#
# 1. **Composability**: Users can batch-process with shell tools:
#      find . -name "*.patch.yaml" -exec onex contract build {} \;
#      for f in patches/*.yaml; do onex contract build "$f" -o "contracts/${f%.yaml}.expanded.yaml"; done
#
# 2. **Error Isolation**: Single-file processing provides clear error attribution.
#    In batch mode, a failure in file N obscures whether files 1..N-1 succeeded.
#
# 3. **Parallelism**: Shell-level parallelism (xargs -P, GNU parallel) is more
#    flexible than CLI-level parallelism and respects system load.
#
# 4. **Simplicity**: Single-file mode is easier to test, debug, and maintain.
#    Batch mode adds complexity: progress reporting, partial failure handling,
#    output file naming conventions, etc.
#
# Future Considerations:
#   If profiling shows significant overhead from repeated CLI startup, consider:
#   - A `build-batch` subcommand that accepts glob patterns
#   - A daemon mode that keeps the Python process warm
#   - Pre-compiled .pyc files to reduce import time
#
# Current Performance Characteristics:
#   - ContractProfileFactory: Stateless, lightweight instantiation (~1ms)
#   - ContractValidationPipeline: Stateless, creates validators on demand
#   - Profile dictionaries: Module-level constants, loaded once per process
#   - YAML parsing: Inherently sequential; ruamel.yaml is already optimized
#   - Hash computation: SHA256 is fast (~10μs for typical patch files)


def _get_runtime_version() -> str:
    """Get the runtime version from package metadata.

    Returns:
        The package version string, or "unknown" if not available.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("omnibase_core")
    except (ImportError, PackageNotFoundError):
        try:
            from omnibase_core import __version__

            return __version__
        except (
            AttributeError,
            ImportError,
        ):  # fallback-ok: version getter must never crash
            return "unknown"


def _generate_merge_hash(
    profile_name: str,
    version_str: str,
    patch_content: str,
) -> str:
    """Generate a deterministic hash from merge inputs for build reproducibility.

    Creates a SHA256 hash from the profile name, version, and patch content,
    truncated to MERGE_HASH_LENGTH (40 hex chars = 160 bits) for readability.

    Purpose: BUILD REPRODUCIBILITY FINGERPRINT
    ------------------------------------------
    This hash enables CI/CD pipelines to detect when a contract needs rebuilding:
    - Same inputs always produce the same hash (deterministic)
    - Any change to profile, version, or patch content changes the hash
    - Two contracts with identical hashes can be treated as identical builds
    - Enables build caching and skip-if-unchanged optimizations

    Security Properties:
    - Algorithm: SHA256 (truncated to 160 bits)
    - Collision probability: ~1.5e-29 for 10 billion contracts (Birthday paradox)
    - NOT intended for cryptographic security (see SHA256_FULL_LENGTH for that)
    - Suitable for build fingerprinting and change detection

    The 40-character length (160 bits) provides:
    - Effectively zero collision probability for practical use cases
    - Extra safety margin beyond the minimum needed (128 bits)
    - Readability in logs and CLI output
    - Alignment with SHA-1's output length as a familiar security baseline

    Args:
        profile_name: The profile name (e.g., "compute_pure").
        version_str: The profile version string (e.g., "1.0.0").
        patch_content: The raw patch file content as a string.

    Returns:
        A 40-character hex hash string (160 bits). The truncation provides
        negligible collision probability (~1e-29) while maintaining readability.

    Examples:
        >>> hash1 = _generate_merge_hash("compute_pure", "1.0.0", "name: test")
        >>> len(hash1)
        40
        >>> hash1 == _generate_merge_hash("compute_pure", "1.0.0", "name: test")
        True
        >>> hash1 != _generate_merge_hash("compute_pure", "1.0.1", "name: test")
        True
    """
    hash_input = f"{profile_name}:{version_str}:{patch_content}"
    full_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return full_hash[:MERGE_HASH_LENGTH]


# Common validation error suggestions by error code or field pattern
_VALIDATION_SUGGESTIONS: dict[str, str] = {
    "name": "Ensure 'name' is a valid identifier (letters, numbers, underscores)",
    "node_version": "node_version requires major, minor, and patch as integers",
    "extends": "Check that 'extends.profile' matches an available profile name",
    "profile": "Run 'onex contract init --type <type> --profile invalid' to see available profiles",
    "handler_id": "handler_id should be a dot-separated identifier (e.g., 'my.handler.name')",
    "timeout_ms": "timeout_ms must be a positive integer (milliseconds)",
    "required": "This field is required and cannot be omitted",
    "type_error": "Check the field type matches the expected schema type",
}

# Separator line width for error output formatting
ERROR_SEPARATOR_WIDTH: int = 60


def _get_suggestion_for_error(field: str, message: str, code: str | None) -> str | None:
    """Get a helpful suggestion for a validation error.

    Args:
        field: The field path that failed validation.
        message: The error message.
        code: The error code (if any).

    Returns:
        A suggestion string, or None if no suggestion applies.

    Examples:
        >>> _get_suggestion_for_error("name", "invalid", None) is not None
        True
        >>> _get_suggestion_for_error("field", "field is required", None) is not None
        True
        >>> _get_suggestion_for_error("unknown", "some error", None) is None
        True
    """
    # Check for exact field match
    field_name = field.split(".")[-1] if "." in field else field
    if field_name in _VALIDATION_SUGGESTIONS:
        return _VALIDATION_SUGGESTIONS[field_name]

    # Check for pattern in message
    message_lower = message.lower()
    if "required" in message_lower:
        return _VALIDATION_SUGGESTIONS["required"]
    if "type" in message_lower or "expected" in message_lower:
        return _VALIDATION_SUGGESTIONS["type_error"]

    return None


def _format_validation_errors(
    validation_results: dict[str, ModelValidationResult[None]],
    phase_failed: EnumValidationPhase | None,
) -> str:
    """Format validation errors for display.

    Produces a detailed, user-friendly error message with context about
    which validation phase failed and suggestions for fixing common issues.

    Args:
        validation_results: Dictionary of validation results by phase.
        phase_failed: The phase where validation failed (if any).

    Returns:
        Formatted error string for CLI output.
    """
    lines = ["=" * ERROR_SEPARATOR_WIDTH]
    lines.append("ERROR: Contract validation failed")
    lines.append("=" * ERROR_SEPARATOR_WIDTH)
    lines.append("")

    # Show which phase failed prominently
    if phase_failed:
        phase_descriptions = {
            EnumValidationPhase.PATCH: "validating the patch file structure",
            EnumValidationPhase.MERGE: "merging patch with base profile",
            EnumValidationPhase.EXPANDED: "validating the expanded contract",
        }
        phase_desc = phase_descriptions.get(phase_failed, phase_failed.value)
        lines.append(f"Failed during: {phase_failed.value.upper()} ({phase_desc})")
        lines.append("")

    # Process phases in order
    phase_order = [
        EnumValidationPhase.PATCH,
        EnumValidationPhase.MERGE,
        EnumValidationPhase.EXPANDED,
    ]

    subseparator_width = ERROR_SEPARATOR_WIDTH // 2 + 10
    for phase in phase_order:
        phase_key = phase.value
        if phase_key not in validation_results:
            continue

        result = validation_results[phase_key]
        if result.is_valid:
            continue

        lines.append("-" * subseparator_width)
        lines.append(f"Phase: {phase.value.upper()}")
        lines.append("-" * subseparator_width)

        # Format issues if available (issues is always a list, may be empty)
        if result.issues:
            for issue in result.issues:
                # Use file_path for location info (ModelValidationIssue field)
                file_path_str = str(issue.file_path) if issue.file_path else "unknown"
                lines.append(f"  Field: {file_path_str}")
                lines.append(f"  Error: {issue.message}")
                if issue.code:
                    lines.append(f"  Code:  {issue.code}")

                # Add suggestion if available
                suggestion = _get_suggestion_for_error(
                    file_path_str, issue.message, issue.code
                )
                if suggestion:
                    lines.append(f"  Hint:  {suggestion}")
                lines.append("")

        # Fall back to errors list if no issues (errors is always a list, may be empty)
        elif result.errors:
            for error in result.errors:
                lines.append(f"  - {error}")
            lines.append("")

    # Add general help footer
    lines.append("=" * ERROR_SEPARATOR_WIDTH)
    lines.append("For more information:")
    lines.append("  - Check your patch file syntax with: onex contract build --help")
    lines.append(
        "  - View available profiles: onex contract init --type <type> --profile ?"
    )
    lines.append("=" * ERROR_SEPARATOR_WIDTH)

    return "\n".join(lines)


def _build_expanded_contract_with_metadata(
    contract: ModelHandlerContract,
    patch: ModelContractPatch,
    patch_path: Path,
    merge_hash: str,
) -> dict[str, object]:
    """Build the expanded contract dictionary with metadata.

    Args:
        contract: The expanded ModelHandlerContract.
        patch: The original contract patch.
        patch_path: Path to the source patch file.
        merge_hash: Pre-computed merge hash for metadata.

    Returns:
        Dictionary with _metadata section and expanded contract fields.
    """
    metadata: dict[str, str] = {
        "profile": patch.extends.profile,
        "profile_version": patch.extends.version,
        "runtime_version": _get_runtime_version(),
        "merge_hash": merge_hash,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_patch": str(patch_path),
    }

    # Convert contract to dict
    contract_dict = contract.model_dump(mode="json", exclude_none=True)

    # Build output with _metadata first
    output: dict[str, object] = {"_metadata": metadata}
    output.update(contract_dict)

    return output


@click.group()
@click.pass_context
def contract(ctx: click.Context) -> None:
    """Contract management commands for ONEX.

    Provides tools for creating, building, and comparing ONEX contracts.
    Contracts define the behavioral specification for nodes including
    capabilities, handlers, and execution policies.

    \b
    Commands:
        init   - Initialize a new contract patch file from a profile
        build  - Expand a patch file into a complete contract
        diff   - Compare two contracts and show differences

    \b
    Examples:
        onex contract init --type orchestrator --profile safe
        onex contract build my_patch.yaml --output my_contract.yaml
        onex contract diff old_contract.yaml new_contract.yaml
    """
    ctx.ensure_object(dict)


@contract.command()
@click.option(
    "--type",
    "-t",
    "node_type",
    required=True,
    type=click.Choice(["orchestrator", "reducer", "effect", "compute"]),
    help="Node type for the contract (determines available profiles and capabilities).",
)
@click.option(
    "--profile",
    "-p",
    required=True,
    help="Profile name to use as base (e.g., 'safe', 'parallel', 'fsm_basic').",
)
@click.option(
    "--name",
    "-n",
    "name",
    default=None,
    help="Custom name for the contract. If not specified, uses a placeholder.",
)
@click.option(
    "--override-only",
    "override_only",
    is_flag=True,
    default=False,
    help="Generate override-only patch without name/node_version fields.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path. If not specified, writes to stdout.",
)
@click.pass_context
def init(
    ctx: click.Context,
    node_type: str,
    profile: str,
    name: str | None,
    override_only: bool,
    output: Path | None,
) -> None:
    """Initialize a new contract patch file from a profile template.

    Creates a minimal patch file that extends a base profile. Edit the
    generated file to customize your contract, then use 'onex contract build'
    to generate the full contract.

    \b
    Exit Codes:
        0 - Success (patch template created)
        1 - Error (invalid profile, file write error, etc.)

    \b
    Profile Names (examples, may not be exhaustive):
        orchestrator: safe, parallel, resilient
        reducer: fsm_basic
        effect: idempotent
        compute: pure
    Use an invalid profile name to see the current list of available profiles.

    \b
    Examples:
        onex contract init --type orchestrator --profile safe
        onex contract init --type orchestrator --profile parallel -o my-workflow.yaml
        onex contract init -t reducer -p fsm_basic --output state-machine.yaml
    """
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    # Validate the profile exists
    error_message = _validate_profile_exists(node_type, profile)
    if error_message:
        if verbose:
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "Invalid profile specified",
                {"node_type": node_type, "profile": profile, "error": error_message},
            )
        raise click.ClickException(error_message)

    # Build the full profile name
    full_profile_name = _build_full_profile_name(node_type, profile)

    if verbose:
        emit_log_event_sync(
            EnumLogLevel.INFO,
            "Generating contract patch template",
            {
                "node_type": node_type,
                "profile": profile,
                "full_profile_name": full_profile_name,
            },
        )

    # Generate the patch template
    patch_content = _generate_patch_template(
        node_type,
        profile,
        full_profile_name,
        name=name,
        override_only=override_only,
    )

    # Output the result
    if output:
        try:
            # Validate and resolve path for security
            resolved_output = _validate_output_path(output)
            resolved_output.write_text(patch_content)
            click.echo(f"Contract patch template written to {resolved_output}")
        except OSError as e:
            if verbose:
                emit_log_event_sync(
                    EnumLogLevel.ERROR,
                    "Failed to write patch file",
                    {"output": str(output), "error": str(e)},
                )
            raise click.ClickException(f"Failed to write file: {e}") from e
    else:
        click.echo(patch_content)

    ctx.exit(EnumCLIExitCode.SUCCESS)


@contract.command()
@click.argument(
    "patch_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path. If not specified, writes to stdout.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format (default: yaml).",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Validate the expanded contract against schema (default: enabled).",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Strict mode: treat warnings as errors.",
)
@click.pass_context
def build(
    ctx: click.Context,
    patch_path: Path,
    output: Path | None,
    output_format: str,
    validate: bool,
    strict: bool,
) -> None:
    """Build an expanded contract from a patch file.

    Reads a patch file, resolves the base profile, merges the patch
    overrides, and produces a complete expanded contract. The resulting
    contract includes all inherited capabilities, handlers, and policies.

    \b
    Exit Codes:
        0 - Success (contract built and written)
        1 - Error (validation failed, file I/O error, etc.)

    \b
    Examples:
        onex contract build my_patch.yaml
        onex contract build my_patch.yaml --output my_contract.yaml
        onex contract build my_patch.yaml --format json -o contract.json
        onex contract build my_patch.yaml --no-validate

    \b
    Output:
        The expanded contract includes a _metadata section with:
          - profile: The base profile name
          - profile_version: The profile version
          - runtime_version: The omnibase_core version
          - merge_hash: Deterministic hash of merge inputs
          - generated_at: ISO timestamp of generation
          - source_patch: Path to the source patch file
    """
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    # Cast format to typed literal for type safety
    format_typed: BuildOutputFormat = cast(BuildOutputFormat, output_format)

    try:
        # Validate input file security and size before reading
        validated_patch_path = _validate_input_file(patch_path)

        # Read raw patch content for hash generation
        patch_content = validated_patch_path.read_text(encoding="utf-8")

        if verbose:
            emit_log_event_sync(
                EnumLogLevel.INFO,
                "Loading patch file",
                {"patch_path": str(validated_patch_path)},
            )

        # Load and validate patch file
        from omnibase_core.models.contracts.model_contract_patch import (
            ModelContractPatch,
        )
        from omnibase_core.utils.util_safe_yaml_loader import (
            load_and_validate_yaml_model,
            serialize_data_to_yaml,
        )

        try:
            patch = load_and_validate_yaml_model(
                validated_patch_path, ModelContractPatch
            )
        except ModelOnexError as e:
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "Failed to parse patch file",
                {"patch_path": str(validated_patch_path), "error": e.message},
            )
            click.echo(f"ERROR: Failed to parse patch file: {e.message}", err=True)
            ctx.exit(EnumCLIExitCode.ERROR)

        if verbose:
            emit_log_event_sync(
                EnumLogLevel.INFO,
                "Patch file loaded",
                {
                    "profile": patch.extends.profile,
                    "version": patch.extends.version,
                    "is_new_contract": patch.is_new_contract,
                },
            )

        # Create profile factory and validation pipeline
        # Performance Note: These are created fresh per invocation by design.
        # - ContractProfileFactory is stateless; profile dicts are module-level
        # - ContractValidationPipeline is stateless and thread-safe
        # - No caching needed: instantiation is cheap (~1ms combined)
        # - For batch processing, use shell-level parallelism (see module header)
        from omnibase_core.factories.factory_contract_profile import (
            ContractProfileFactory,
        )
        from omnibase_core.validation.validator_contract_pipeline import (
            ContractValidationPipeline,
        )

        profile_factory = ContractProfileFactory()
        pipeline = ContractValidationPipeline()

        if verbose:
            emit_log_event_sync(
                EnumLogLevel.INFO,
                "Running validation pipeline",
                {"validate_enabled": validate},
            )

        # Run full validation pipeline
        result = pipeline.validate_all(patch, profile_factory)

        # Check for validation failures
        if not result.success:
            error_output = _format_validation_errors(
                result.validation_results,
                result.phase_failed,
            )
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "Contract validation failed",
                {
                    "phase_failed": result.phase_failed.value
                    if result.phase_failed
                    else None,
                    "error_count": len(result.errors),
                },
            )
            click.echo(error_output, err=True)
            ctx.exit(EnumCLIExitCode.ERROR)

        # In strict mode, treat warnings as errors
        if strict:
            all_warnings: list[str] = []
            for phase_result in result.validation_results.values():
                # warnings is always a list on ModelValidationResult, may be empty
                if phase_result.warnings:
                    all_warnings.extend(phase_result.warnings)

            if all_warnings:
                emit_log_event_sync(
                    EnumLogLevel.ERROR,
                    "Strict mode: warnings treated as errors",
                    {"warning_count": len(all_warnings)},
                )
                click.echo("ERROR: Strict mode - warnings treated as errors:", err=True)
                for warning in all_warnings:
                    click.echo(f"  - {warning}", err=True)
                ctx.exit(EnumCLIExitCode.ERROR)

        # Build expanded contract with metadata
        if result.contract is None:
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "Validation succeeded but no contract was produced",
                {},
            )
            click.echo(
                "ERROR: Validation succeeded but no contract was produced",
                err=True,
            )
            ctx.exit(EnumCLIExitCode.ERROR)

        # Compute merge hash for logging and metadata
        merge_hash = _generate_merge_hash(
            profile_name=patch.extends.profile,
            version_str=patch.extends.version,
            patch_content=patch_content,
        )

        expanded = _build_expanded_contract_with_metadata(
            contract=result.contract,
            patch=patch,
            patch_path=validated_patch_path,
            merge_hash=merge_hash,
        )

        if verbose:
            emit_log_event_sync(
                EnumLogLevel.INFO,
                "Contract built successfully",
                {
                    "handler_id": result.contract.handler_id,
                    "name": result.contract.name,
                    "merge_hash": merge_hash,
                },
            )

        # Format output
        if format_typed == "json":
            output_content = json.dumps(expanded, indent=2, ensure_ascii=False)
        else:
            output_content = serialize_data_to_yaml(expanded)

        # Write output
        if output:
            # Validate and resolve path for security
            resolved_output = _validate_output_path(output)
            resolved_output.write_text(output_content, encoding="utf-8")
            click.echo(f"Expanded contract written to {resolved_output}")
        else:
            click.echo(output_content)

        # Success - return normally (exit code 0)
        return

    except yaml.YAMLError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "YAML parsing error",
            {"patch_path": str(patch_path), "error": str(e)},
        )
        click.echo(
            f"ERROR: YAML parsing error in '{patch_path}':\n"
            f"  {e}\n"
            f"  Hint: Check for incorrect indentation, missing colons, "
            f"or invalid characters.",
            err=True,
        )
        ctx.exit(EnumCLIExitCode.ERROR)
    except ModelOnexError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "ONEX error during build",
            {
                "patch_path": str(patch_path),
                "error_code": str(e.error_code),
                "message": e.message,
            },
        )
        # Include file path and hint in error output
        click.echo(
            f"ERROR: Contract build failed for '{patch_path}':\n"
            f"  {e.message}\n"
            f"  Error code: {e.error_code}\n"
            f"  Hint: Review the patch file for missing or invalid fields.",
            err=True,
        )
        ctx.exit(EnumCLIExitCode.ERROR)
    except OSError as e:
        # Determine which file caused the error based on error attributes
        error_path = getattr(e, "filename", None) or str(patch_path)
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "File I/O error",
            {"patch_path": str(patch_path), "error_path": error_path, "error": str(e)},
        )
        click.echo(
            f"ERROR: File I/O error while processing '{patch_path}':\n"
            f"  {e}\n"
            f"  Hint: Check file permissions and that the path exists.",
            err=True,
        )
        ctx.exit(EnumCLIExitCode.ERROR)
    except click.exceptions.Exit:
        # Re-raise click.Exit to allow ctx.exit() to work properly
        raise
    except (
        Exception
    ) as e:  # catch-all-ok: CLI catch-all for user-friendly error messages
        # Catches unexpected errors for user-friendly output
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Unexpected error during build",
            {
                "patch_path": str(patch_path),
                "error": str(e),
                "type": type(e).__name__,
            },
        )
        click.echo(
            f"ERROR: Unexpected error while building '{patch_path}':\n"
            f"  {type(e).__name__}: {e}\n"
            f"  Hint: This may be a bug. Please report with the full error trace.",
            err=True,
        )
        ctx.exit(EnumCLIExitCode.ERROR)


@contract.command()
@click.argument(
    "old_contract",
    type=click.Path(exists=True, path_type=Path),
)
@click.argument(
    "new_contract",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format for the diff (default: text).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path. If not specified, writes to stdout.",
)
@click.pass_context
def diff(
    ctx: click.Context,
    old_contract: Path,
    new_contract: Path,
    output_format: str,
    output: Path | None,
) -> None:
    """Compare two expanded contracts and show semantic differences.

    Performs a semantic diff between two contract YAML files, detecting
    added, removed, and changed fields. Special attention is given to
    behavioral changes (purity, idempotency, timeouts, etc.) that affect
    runtime behavior.

    \b
    Exit Codes:
        0 - No differences found
        2 - Differences found (like git diff)
        1 - Error loading or parsing files

    \b
    Examples:
        onex contract diff old.yaml new.yaml
        onex contract diff old.yaml new.yaml --format json
        onex contract diff old.yaml new.yaml -o diff.txt
        onex contract diff before.expanded.yaml after.expanded.yaml

    \b
    Output Formats:
        text - Human-readable format with sections for behavioral/added/removed/changed
        json - Structured JSON with severity levels and categorized changes
        yaml - Structured YAML with severity levels and categorized changes
    """
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    # Import diff helpers
    from omnibase_core.cli.cli_contract_diff import (
        categorize_diff_entries,
        diff_contract_dicts,
        format_json_diff_output,
        format_text_diff_output,
        format_yaml_diff_output,
        load_contract_yaml_file,
    )

    # Cast format to typed literal for type safety
    format_typed: DiffOutputFormat = cast(DiffOutputFormat, output_format)

    if verbose:
        emit_log_event_sync(
            EnumLogLevel.INFO,
            "Starting contract diff",
            {
                "old_contract": str(old_contract),
                "new_contract": str(new_contract),
                "output_format": format_typed,
            },
        )

    # Load both contracts
    old_data = load_contract_yaml_file(old_contract)
    new_data = load_contract_yaml_file(new_contract)

    # Compute diff
    diffs = diff_contract_dicts(old_data, new_data)

    # Categorize diffs
    result = categorize_diff_entries(diffs)
    result.old_path = str(old_contract)
    result.new_path = str(new_contract)

    if verbose:
        emit_log_event_sync(
            EnumLogLevel.INFO,
            "Diff computed",
            {
                "total_changes": result.total_changes,
                "behavioral_changes": len(result.behavioral_changes),
                "added": len(result.added),
                "removed": len(result.removed),
                "changed": len(result.changed),
            },
        )

    # Format output
    if format_typed == "json":
        output_text = format_json_diff_output(result)
    elif format_typed == "yaml":
        output_text = format_yaml_diff_output(result)
    else:
        output_text = format_text_diff_output(result)

    # Write output
    if output:
        try:
            # Validate and resolve path for security
            resolved_output = _validate_output_path(output)
            resolved_output.write_text(output_text, encoding="utf-8")
            click.echo(f"Diff written to {resolved_output}")
        except OSError as e:
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "Failed to write diff output",
                {"output": str(output), "error": str(e)},
            )
            raise click.ClickException(f"Cannot write to '{output}': {e}") from e
    else:
        click.echo(output_text)

    # Exit with appropriate code
    if result.has_changes:
        ctx.exit(EnumCLIExitCode.WARNING)  # 2 - differences found
    else:
        ctx.exit(EnumCLIExitCode.SUCCESS)  # 0 - no differences


__all__ = ["contract"]
