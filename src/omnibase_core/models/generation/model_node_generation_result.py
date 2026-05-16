# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelNodeGenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    contract_yaml: str
    handler_source: str
    artifact_paths: list[str]
    generated_contract_hash: str
    generated_handler_hash: str
    stdout: str
    stderr: str
    returncode: int
