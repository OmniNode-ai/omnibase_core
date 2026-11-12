# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Release-consistency COMPUTE: typed release facts in, a report out (OMN-23845).

release.yml already refuses a tag that differs from the version the build
derives, before it builds. Nothing read the published files back afterwards.
This compares, after a successful release:

* each file the release built with the file PyPI serves under the same name:
  present, and the same sha256;
* the built wheel's METADATA ``Version`` with the tag;
* PyPI's reported version for the release with the tag.

PyPI unread is UNKNOWN, never AGREE or MISMATCH.
"""

from __future__ import annotations

from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_check_input import (
    ModelReleaseConsistencyCheckInput,
)
from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_report import (
    ModelReleaseConsistencyReport,
    ReleaseConsistencyVerdict,
)


class NodeReleaseConsistencyCheckCompute:
    """Pure comparison of what a release built with what PyPI serves."""

    def handle(
        self, request: ModelReleaseConsistencyCheckInput
    ) -> ModelReleaseConsistencyReport:
        """One line per check, in a fixed order, and the overall verdict."""
        tag = request.tag
        version = tag[1:] if tag.startswith("v") else tag
        lines: list[str] = [f"UNKNOWN {error}" for error in request.runtime_errors]

        if request.wheel_version_raw is None:
            lines.append("UNKNOWN wheel metadata: no built wheel Version to read")
        elif request.wheel_version_raw == version:
            lines.append(
                f"AGREE wheel metadata Version {request.wheel_version_raw} equals tag {tag}"
            )
        else:
            lines.append(
                f"MISMATCH wheel metadata Version {request.wheel_version_raw} "
                f"differs from tag {tag}"
            )

        built = {item.name: item.sha256 for item in request.built_files}
        if request.served_files is None:
            lines.append(f"UNKNOWN PyPI: could not read the JSON for {version}")
            lines.extend(f"UNKNOWN {name}: PyPI unread" for name in sorted(built))
            return self._report(tag, lines)

        if request.served_version_raw == version:
            lines.append(f"AGREE PyPI version {version} equals tag {tag}")
        else:
            lines.append(
                f"MISMATCH PyPI version {request.served_version_raw} differs from tag {tag}"
            )

        served = {item.name: item.sha256 for item in request.served_files}
        for name in sorted(built):
            if name not in served:
                lines.append(f"MISMATCH {name}: built but missing from PyPI")
            elif served[name] != built[name]:
                lines.append(
                    f"MISMATCH {name}: PyPI sha256 {served[name]} "
                    f"differs from built {built[name]}"
                )
            else:
                lines.append(f"AGREE {name} sha256 {built[name]}")
        lines.extend(
            f"MISMATCH {name}: served by PyPI but not built by this release"
            for name in sorted(set(served) - set(built))
        )
        return self._report(tag, lines)

    @staticmethod
    def _report(tag: str, lines: list[str]) -> ModelReleaseConsistencyReport:
        states = {line.split(" ", 1)[0] for line in lines}
        verdict: ReleaseConsistencyVerdict = (
            "MISMATCH"
            if "MISMATCH" in states
            else "UNKNOWN"
            if "UNKNOWN" in states
            else "AGREE"
        )
        return ModelReleaseConsistencyReport(
            tag=tag, verdict=verdict, lines=tuple(lines)
        )
