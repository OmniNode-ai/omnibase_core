# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EFFECT boundary: read a release's dist files and a saved PyPI JSON response.

It reads local files only. The release job fetches the PyPI JSON itself, with
retries, and passes the saved file; a missing or unparsable file is PyPI
unread, which the COMPUTE node reports UNKNOWN.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_check_input import (
    ModelReleaseConsistencyCheckInput,
)
from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_gather_input import (
    ModelReleaseConsistencyGatherInput,
)
from omnibase_core.models.nodes.release_consistency_check.model_release_file_digest import (
    ModelReleaseFileDigest,
)

_SUMS_FILE = "SHA256SUMS.txt"
_METADATA_SUFFIX = ".dist-info/METADATA"
_VERSION_FIELD = "Version:"


class NodeReleaseConsistencyGatherEffect:
    """Collect the built files, the wheel version and PyPI's served files."""

    def handle(
        self, request: ModelReleaseConsistencyGatherInput
    ) -> ModelReleaseConsistencyCheckInput:
        """Read each source; one that cannot be read becomes an UNKNOWN fact."""
        dist = Path(request.dist_dir)
        errors: list[str] = []
        built: tuple[ModelReleaseFileDigest, ...] = ()
        try:
            built, unreadable = self._parse_sums(
                (dist / _SUMS_FILE).read_text(encoding="utf-8")
            )
            errors.extend(
                f"{_SUMS_FILE}: unreadable line {raw!r}" for raw in unreadable
            )
        except OSError as exc:
            errors.append(f"{_SUMS_FILE}: {exc}")
        served_version_raw, served = self._read_pypi(request.pypi_json_path)
        return ModelReleaseConsistencyCheckInput(
            tag=request.tag,
            built_files=built,
            wheel_version_raw=self._wheel_version(dist),
            served_version_raw=served_version_raw,
            served_files=served,
            runtime_errors=tuple(errors),
        )

    @staticmethod
    def _parse_sums(
        text: str,
    ) -> tuple[tuple[ModelReleaseFileDigest, ...], tuple[str, ...]]:
        """``sha256sum`` output (``<hex>  dist/<file>``): files, unreadable lines."""
        files: list[ModelReleaseFileDigest] = []
        unreadable: list[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            digest, _, path = line.partition(" ")
            name = Path(path.strip().lstrip("*")).name
            if not digest or not name:
                unreadable.append(raw)
                continue
            files.append(ModelReleaseFileDigest(name=name, sha256=digest.lower()))
        return tuple(files), tuple(unreadable)

    @staticmethod
    def _wheel_version(dist: Path) -> str | None:
        """The METADATA Version of the one built wheel, or None."""
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) != 1:
            return None
        try:
            with zipfile.ZipFile(wheels[0]) as wheel:
                for member in wheel.namelist():
                    if not member.endswith(_METADATA_SUFFIX):
                        continue
                    for line in wheel.read(member).decode("utf-8").splitlines():
                        if line.startswith(_VERSION_FIELD):
                            return line.split(":", 1)[1].strip()
        except (OSError, zipfile.BadZipFile, UnicodeDecodeError):
            return None
        return None

    @staticmethod
    def _read_pypi(
        path: str | None,
    ) -> tuple[str | None, tuple[ModelReleaseFileDigest, ...] | None]:
        """PyPI's version and served files; (None, None) when it is unread."""
        if path is None:
            return None, None
        try:
            loaded: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None, None
        if not isinstance(loaded, dict):
            return None, None
        info = loaded.get("info")
        version = info.get("version") if isinstance(info, dict) else None
        urls = loaded.get("urls")
        if not isinstance(urls, list):
            return None, None
        served: list[ModelReleaseFileDigest] = []
        for entry in urls:
            if not isinstance(entry, dict):
                continue
            name = entry.get("filename")
            digests = entry.get("digests")
            sha = digests.get("sha256") if isinstance(digests, dict) else None
            if isinstance(name, str) and isinstance(sha, str):
                served.append(ModelReleaseFileDigest(name=name, sha256=sha.lower()))
        return (version if isinstance(version, str) else None), tuple(served)
