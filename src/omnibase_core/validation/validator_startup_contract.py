# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Startup contract.yaml validation for ONEX nodes.

Validates that a node's contract.yaml exists and is well-formed during
startup. Validation is non-blocking: missing or malformed contracts produce
warnings but do not halt startup.

Acceptance Criteria (OMN-1533):
- Log warning if contract.yaml is missing
- Log confirmation when contract.yaml is found
- Do not block startup (warning only)
- Validate basic YAML parsing when contract is found

Usage Example:
    Direct invocation::

        from pathlib import Path
        from omnibase_core.validation.validator_startup_contract import (
            validate_startup_contract,
            StartupContractValidationResult,
        )

        result = validate_startup_contract(Path("/nodes/my_node/contract.yaml"))
        if result.found:
            # contract loaded and validated
            pass
        else:
            # contract missing — startup continues with warning logged

    Integration in node startup::

        from omnibase_core.validation.validator_startup_contract import (
            validate_startup_contract,
        )

        result = validate_startup_contract(contract_path)
        # startup always continues; result carries status for introspection

Thread Safety:
    validate_startup_contract() is stateless and safe to call concurrently.

See Also:
    - OMN-1533: Add contract.yaml validation on server startup
    - OMN-2362: Generic Validator Node Architecture (parent epic)
    - constants_contract.py: CONTRACT_FILENAME constant
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import yaml

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)

# Maximum contract file size accepted during startup validation (1 MB)
_MAX_CONTRACT_SIZE_BYTES: int = 1024 * 1024

_COMPONENT_NAME: str = "validator_startup_contract"


class StartupContractValidationResult(NamedTuple):
    """Immutable result of a startup contract.yaml validation.

    Attributes:
        found: True if contract.yaml was found at the given path.
        valid_yaml: True if the file was found and parsed as valid YAML.
            Always False when found is False.
        contract_data: Parsed YAML content as a dict, or None if not found
            or if YAML parsing failed.
        warning_message: Human-readable warning if something went wrong,
            or None when everything is fine.
    """

    found: bool
    valid_yaml: bool
    contract_data: dict[str, object] | None
    warning_message: str | None


def validate_startup_contract(
    contract_path: Path,
    *,
    node_name: str = "",
) -> StartupContractValidationResult:
    """Validate contract.yaml existence and YAML well-formedness at startup.

    Performs two checks in order:
    1. File existence — logs WARNING if missing, INFO if found.
    2. YAML parsing — logs WARNING if malformed, INFO if valid.

    Neither check blocks startup. The caller always receives a result
    object and may inspect it for introspection or metric purposes.

    Args:
        contract_path: Absolute or relative path to the contract.yaml file.
        node_name: Optional node class name for richer log context.

    Returns:
        StartupContractValidationResult with found, valid_yaml, contract_data,
        and warning_message fields.

    Example:
        >>> from pathlib import Path
        >>> result = validate_startup_contract(Path("nonexistent/contract.yaml"))
        >>> assert result.found is False
        >>> assert result.valid_yaml is False
        >>> assert result.warning_message is not None
    """
    log_context: dict[str, object] = {
        "component": _COMPONENT_NAME,
        "contract_path": str(contract_path),
    }
    if node_name:
        log_context["node_name"] = node_name

    # --- Check 1: existence ---
    if not contract_path.exists():
        warning = (
            f"contract.yaml not found — running without ONEX contract: {contract_path}"
        )
        emit_log_event(
            LogLevel.WARNING,
            warning,
            log_context,
        )
        return StartupContractValidationResult(
            found=False,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    if not contract_path.is_file():
        warning = f"contract.yaml path is not a regular file: {contract_path}"
        emit_log_event(
            LogLevel.WARNING,
            warning,
            log_context,
        )
        return StartupContractValidationResult(
            found=False,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    # File size guard — protect against DoS via huge contract files
    try:
        file_size = contract_path.stat().st_size
    except OSError as exc:
        warning = f"contract.yaml stat() failed: {exc}"
        emit_log_event(LogLevel.WARNING, warning, log_context)
        return StartupContractValidationResult(
            found=True,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    if file_size > _MAX_CONTRACT_SIZE_BYTES:
        warning = (
            f"contract.yaml exceeds maximum size "
            f"({file_size} > {_MAX_CONTRACT_SIZE_BYTES} bytes): {contract_path}"
        )
        emit_log_event(LogLevel.WARNING, warning, log_context)
        return StartupContractValidationResult(
            found=True,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    emit_log_event(
        LogLevel.INFO,
        f"Contract found: {contract_path}",
        {**log_context, "file_size_bytes": file_size},
    )

    # --- Check 2: YAML parsing ---
    try:
        raw_text = contract_path.read_text(encoding="utf-8")
    except OSError as exc:
        warning = f"contract.yaml could not be read: {exc}"
        emit_log_event(LogLevel.WARNING, warning, log_context)
        return StartupContractValidationResult(
            found=True,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    try:
        parsed = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        warning = f"contract.yaml is not valid YAML: {exc}"
        emit_log_event(LogLevel.WARNING, warning, log_context)
        return StartupContractValidationResult(
            found=True,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    if not isinstance(parsed, dict):
        warning = (
            f"contract.yaml top-level must be a YAML mapping, "
            f"got {type(parsed).__name__}: {contract_path}"
        )
        emit_log_event(LogLevel.WARNING, warning, log_context)
        return StartupContractValidationResult(
            found=True,
            valid_yaml=False,
            contract_data=None,
            warning_message=warning,
        )

    emit_log_event(
        LogLevel.INFO,
        f"Contract loaded: {contract_path}",
        {**log_context, "contract_keys": list(parsed.keys())},
    )

    return StartupContractValidationResult(
        found=True,
        valid_yaml=True,
        contract_data=parsed,
        warning_message=None,
    )
