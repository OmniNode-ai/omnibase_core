# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Nominal string identifiers and non-SemVer generation markers.

These values cross external or human-readable boundaries where UUID coercion
would destroy meaning. ``NewType`` keeps their established string wire shape
while preventing accidental interchange in strictly typed code.
"""

from typing import NewType

AdrId = NewType("AdrId", str)
ArtifactWriterVersion = NewType("ArtifactWriterVersion", str)
DispatcherId = NewType("DispatcherId", str)
ExternalLearningId = NewType("ExternalLearningId", str)
ExternalSourceId = NewType("ExternalSourceId", str)
GoldenChainFixtureVersion = NewType("GoldenChainFixtureVersion", str)
LlmModelId = NewType("LlmModelId", str)
RoutingDecisionId = NewType("RoutingDecisionId", str)
SweepSessionId = NewType("SweepSessionId", str)
ThemeId = NewType("ThemeId", str)

__all__ = [
    "AdrId",
    "ArtifactWriterVersion",
    "DispatcherId",
    "ExternalLearningId",
    "ExternalSourceId",
    "GoldenChainFixtureVersion",
    "LlmModelId",
    "RoutingDecisionId",
    "SweepSessionId",
    "ThemeId",
]
