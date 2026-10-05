# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inline configuration and discovered repository facts; no handler I/O."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_check_config import (
    ModelTestRootCollectionCheckConfig,
)
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_selector import (
    ModelTestRootCollectionSelector,
)


class ModelTestRootCollectionCheckInput(BaseModel):
    """Everything the old script discovered or read, as typed input."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)
    directories: tuple[str, ...] = ()
    test_files: tuple[str, ...] = ()
    standalone_pyprojects: tuple[str, ...] = ()
    selector: ModelTestRootCollectionSelector
    config: ModelTestRootCollectionCheckConfig = Field(
        default_factory=ModelTestRootCollectionCheckConfig
    )
    root_label: str = "."
