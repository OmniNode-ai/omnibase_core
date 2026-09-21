# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-authoritative resolver for Pydantic model configuration."""

import importlib
import sys
from pathlib import Path
from types import ModuleType

from omnibase_core.models.validation.model_extra_forbid_finding import (
    STATUS_EXPLICIT_ALLOW,
    STATUS_EXPLICIT_FORBID,
    STATUS_EXPLICIT_IGNORE,
    STATUS_IMPLICIT_DEFAULT,
    STATUS_UNRESOLVED,
)
from omnibase_core.validation.pydantic_module_index import module_for_path

_STATUS_BY_EXTRA: dict[str, str] = {
    "forbid": STATUS_EXPLICIT_FORBID,
    "ignore": STATUS_EXPLICIT_IGNORE,
    "allow": STATUS_EXPLICIT_ALLOW,
}


class _RuntimeResolver:
    """Import modules and read Pydantic's merged ``model_config``."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleType] = {}
        self._failed: set[str] = set()
        self.import_failures: dict[str, str] = {}

    def load(self, path: Path) -> ModuleType | None:
        module_name, sys_root = module_for_path(path)
        if not module_name or module_name in self._failed:
            return None
        if module_name in self._modules:
            return self._modules[module_name]

        root = str(sys_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            module = importlib.import_module(module_name)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:  # noqa: BLE001  # fallback-ok: static AST resolver
            self._failed.add(module_name)
            self.import_failures[module_name] = f"{type(exc).__name__}: {exc}"
            return None
        self._modules[module_name] = module
        return module

    def verdict(
        self, module: ModuleType, class_name: str
    ) -> tuple[str, str | None, bool] | None:
        """Return ``(status, effective_extra, exempt)`` for a Pydantic model."""
        from pydantic import BaseModel, RootModel

        obj = getattr(module, class_name, None)
        if not isinstance(obj, type) or not issubclass(obj, BaseModel):
            return None
        if getattr(obj, "__module__", None) != getattr(module, "__name__", None):
            return None
        if obj is BaseModel or issubclass(obj, RootModel):
            return STATUS_EXPLICIT_FORBID, None, True

        extra = obj.model_config.get("extra")
        if extra is None:
            return STATUS_IMPLICIT_DEFAULT, None, False
        return _STATUS_BY_EXTRA.get(str(extra), STATUS_UNRESOLVED), str(extra), False
