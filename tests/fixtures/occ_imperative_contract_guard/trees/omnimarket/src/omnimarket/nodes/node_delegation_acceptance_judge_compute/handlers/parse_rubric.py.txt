# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Parse the rubric YAML text a caller passes in; the node reads no file. Pure."""

from __future__ import annotations

import yaml

from omnimarket.nodes.node_delegation_acceptance_judge_compute.models.model_acceptance_rubric import (
    ModelAcceptanceRubric,
)


def parse_rubric(rubric_yaml: str) -> ModelAcceptanceRubric:
    raw = yaml.safe_load(rubric_yaml)
    if not isinstance(raw, dict):
        raise ValueError("the acceptance rubric must be a YAML mapping")
    return ModelAcceptanceRubric.model_validate(raw)
