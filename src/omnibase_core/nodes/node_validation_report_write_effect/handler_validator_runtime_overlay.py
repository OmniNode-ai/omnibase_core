# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerValidatorRuntimeOverlay — read an overlay, bind the bus it names (OMN-21529).

The validator runtime's bus is data. An overlay file names the bus class and how to
build it; the runtime binds that class into the container and the report writer
resolves it from there. The in-memory overlay and the Redpanda overlay differ only in
that binding, so choosing one is choosing a file, never changing code. The node
contract's ``validator_runtime`` block names the default overlay, the default report
path and the default repository.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_overlay import (
    ModelValidatorRuntimeOverlay,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_settings import (
    ModelValidatorRuntimeSettings,
)
from omnibase_core.overlays.contract_env_ref import expand_contract_env_refs
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

__all__ = ["HandlerValidatorRuntimeOverlay"]

_NODE_DIR = Path(__file__).resolve().parent
_SETTINGS = _NODE_DIR / "overlays/validator_runtime.settings.yaml"


class HandlerValidatorRuntimeOverlay:
    """Load the runtime settings and overlays; bind the overlay's bus."""

    def settings(self, path: Path = _SETTINGS) -> ModelValidatorRuntimeSettings:
        """The settings file; an invalid one fails to load rather than passing."""
        return load_and_validate_yaml_model(path, ModelValidatorRuntimeSettings)

    def default_overlay_path(self) -> Path:
        """Where the settings say the default overlay lives."""
        return _NODE_DIR / self.settings().default_overlay

    def load(self, path: Path) -> ModelValidatorRuntimeOverlay:
        """Parse an overlay file; an invalid overlay fails to load rather than passing."""
        return load_and_validate_yaml_model(path, ModelValidatorRuntimeOverlay)

    def bind_bus(
        self, overlay: ModelValidatorRuntimeOverlay
    ) -> ModelValidatorRuntimeBus:
        """The bus the overlay names, as the lifecycle and publish calls the runtime uses."""
        bus = self.construct_bus(overlay)
        return ModelValidatorRuntimeBus(
            start=bus.start, publish=bus.publish, close=bus.close
        )

    def construct_bus(self, overlay: ModelValidatorRuntimeOverlay) -> Any:
        """Build the bus the overlay names; the overlay is the only thing that varies."""
        module_name, _, class_name = overlay.bus.implementation.partition(":")
        try:
            implementation = getattr(importlib.import_module(module_name), class_name)
            build = (
                implementation
                if overlay.bus.constructor is None
                else getattr(implementation, overlay.bus.constructor)
            )
        except (ImportError, AttributeError) as exc:
            raise ModelOnexError(
                message=f"overlay bus {overlay.bus} cannot be bound: {exc}",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            ) from exc
        if overlay.bus.argument is None:
            bus = build()
        else:
            argument = expand_contract_env_refs(overlay.bus.argument)
            if not argument:
                raise ModelOnexError(
                    message=f"overlay bus argument {overlay.bus.argument} expands to nothing",
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )
            bus = build(argument)
        return bus
