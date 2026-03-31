# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""File-based implementation of ProtocolStateStore.

Persists node state as YAML files on disk. Each state snapshot is stored at
``{state_root}/{node_id}/{scope_id}/state.yaml``.

Atomic writes: state is written to a temporary file in the target directory,
then renamed to the final path. This prevents partial writes from corrupting
existing state. On rename failure the temporary file is preserved so callers
can recover.

Concurrency: last-write-wins. No file locking (Phase 1 local-only use).

.. versionadded:: 0.35.1
    Added as part of Local-First Node Runtime (OMN-7063)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from omnibase_core.errors.error_state_corruption import StateCorruptionError
from omnibase_core.models.state.model_state_envelope import ModelStateEnvelope


class ServiceStateDisk:
    """File-based state store backed by YAML files on disk."""

    def __init__(self, state_root: Path) -> None:
        self._state_root = state_root

    def _state_path(self, node_id: str, scope_id: str) -> Path:
        return self._state_root / node_id / scope_id / "state.yaml"

    async def get(
        self, node_id: str, scope_id: str = "default"
    ) -> ModelStateEnvelope | None:
        path = self._state_path(node_id, scope_id)
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)  # yaml-ok: deserialize file then model_validate
            return ModelStateEnvelope.model_validate(data)
        except Exception as exc:
            raise StateCorruptionError(f"Corrupt state file at {path}: {exc}") from exc

    async def put(self, envelope: ModelStateEnvelope) -> None:
        path = self._state_path(envelope.node_id, envelope.scope_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = yaml.safe_dump(
            envelope.model_dump(mode="json"), default_flow_style=False
        )
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=".state_", suffix=".tmp"
        )
        closed = False
        try:
            os.write(fd, serialized.encode("utf-8"))
            os.close(fd)
            closed = True
            Path(tmp_path).rename(path)
        except BaseException:
            if not closed:
                os.close(fd)
            raise

    async def delete(self, node_id: str, scope_id: str = "default") -> bool:
        path = self._state_path(node_id, scope_id)
        if not path.exists():
            return False
        path.unlink()
        # Clean up empty parent directories
        scope_dir = path.parent
        if scope_dir.exists() and not any(scope_dir.iterdir()):
            scope_dir.rmdir()
        node_dir = scope_dir.parent
        if node_dir.exists() and not any(node_dir.iterdir()):
            node_dir.rmdir()
        return True

    async def exists(self, node_id: str, scope_id: str = "default") -> bool:
        return self._state_path(node_id, scope_id).exists()

    async def list_keys(self, node_id: str | None = None) -> list[tuple[str, str]]:
        keys: list[tuple[str, str]] = []
        if node_id is not None:
            node_dir = self._state_root / node_id
            if not node_dir.is_dir():
                return []
            for scope_dir in sorted(node_dir.iterdir()):
                if scope_dir.is_dir() and (scope_dir / "state.yaml").exists():
                    keys.append((node_id, scope_dir.name))
        else:
            if not self._state_root.is_dir():
                return []
            for ndir in sorted(self._state_root.iterdir()):
                if not ndir.is_dir():
                    continue
                for scope_dir in sorted(ndir.iterdir()):
                    if scope_dir.is_dir() and (scope_dir / "state.yaml").exists():
                        keys.append((ndir.name, scope_dir.name))
        return keys
